

import json
import logging
import re

from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .knowledge import (
    public_knowledge,
    staff_knowledge,
    contact_answer,
    payment_answer,
)
from .search import tokens, best_match
from .tracking import record_unanswered_question
from .models import ChatbotConversationLog

logger = logging.getLogger(__name__)

# ============================================================
# JSON RESPONSE
# ============================================================


def result(message, source="general", links=None, status=200):
    return JsonResponse(
        {
            "reply": message,
            "source": source,
            "links": links or [],
        },
        status=status,
    )


# ============================================================
# ACTION BUTTON
# ============================================================


def action(request, name, label):
    return {
        "label": label,
        "url": request.build_absolute_uri(reverse(name)),
    }


# ============================================================
# CHATBOT MESSAGE ENDPOINT
# ============================================================


def _chatbot_message(request):

    # --------------------------------------------------------
    # GET VISITOR QUESTION
    # --------------------------------------------------------

    question = request.POST.get("message", "").strip()

    if not question:
        return result(
            "Please enter your question.",
            status=400,
        )

    if len(question) > 500:
        return result(
            "Please shorten your question to 500 characters.",
            status=400,
        )

    q = question.lower()
    w = tokens(q)

    # --------------------------------------------------------
    # GREETINGS
    # --------------------------------------------------------

    if q in {
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
    }:
        return result(
            "Hello! Welcome to Hands-On Health. "
            "Ask about our services, prices, payments, "
            "referrals or appointments."
        )

    # --------------------------------------------------------
    # GEOGRAPHIC COVERAGE / INTERNATIONAL AVAILABILITY
    # --------------------------------------------------------
    # Handle location questions BEFORE generic booking/referral
    # rules. A booking form does not prove a location is served.

    coverage_words = {
        "kenya",
        "namibia",
        "uganda",
        "tanzania",
        "zambia",
        "botswana",
        "south africa",
        "zimbabwe",
        "rwanda",
        "nigeria",
        "ghana",
        "abroad",
        "overseas",
        "international",
    }
    asks_coverage = (
        any(place in q for place in coverage_words)
        and (
            bool(
                w
                & {
                    "care",
                    "service",
                    "services",
                    "available",
                    "serve",
                    "operate",
                    "coverage",
                    "nursing",
                    "visit",
                }
            )
            or "home based" in q
            or "home-based" in q
        )
    ) or (
        bool(w & {"available", "serve", "operate", "coverage"})
        and bool(w & {"where", "country", "countries", "locations", "areas", "regions"})
    )

    if asks_coverage:
        # Staff-approved coverage answers take priority, but only
        # when the match is strong enough to be reliable.
        coverage_articles = [
            article
            for article in staff_knowledge()
            if any(
                term
                in (
                    str(article.get("title", ""))
                    + " "
                    + str(article.get("body", ""))
                    + " "
                    + str(article.get("kind", ""))
                ).lower()
                for term in (
                    "coverage",
                    "service area",
                    "locations served",
                    "kenya",
                    "namibia",
                    "international",
                    "countries served",
                )
            )
        ]
        matched, confidence = best_match(question, coverage_articles)
        if matched and confidence >= 0.75:
            return result(
                matched["body"],
                "coverage",
                [action(request, "pages:contact", "Contact Us")],
            )

        return result(
            "I cannot confirm from our published information whether "
            "Hands-On Health currently provides home-based care in "
            "your location. Please contact our team to verify service "
            "availability before making a booking.",
            "coverage_unconfirmed",
            [action(request, "pages:contact", "Confirm Service Availability")],
        )

    # --------------------------------------------------------
    # REFERRALS
    # --------------------------------------------------------

    if w & {"refer", "referrer", "referral"} or "send a patient" in q:
        return result(
            "Yes, you can submit a patient referral using "
            "our referral form. Our team will review "
            "the request.",
            "referral",
            [
                action(
                    request,
                    "homecare:referral",
                    "Refer a Patient",
                )
            ],
        )

    # --------------------------------------------------------
    # APPOINTMENTS / CONSULTATIONS
    # --------------------------------------------------------

    if ("appointment" in w or "consultation" in w) and not (
        "price" in w or "payment" in w
    ):
        return result(
            "You can request an appointment using " "our online booking form.",
            "appointment",
            [
                action(
                    request,
                    "homecare:book_appointment",
                    "Book Appointment",
                )
            ],
        )

    # --------------------------------------------------------
    # HOME CARE REQUEST
    # --------------------------------------------------------

    if (
        "home" in w
        and "care" in w
        and w
        & {
            "request",
            "arrange",
            "apply",
            "get",
        }
    ) or "request home care" in q:
        return result(
            "You can submit a home-care request " "through our website.",
            "homecare",
            [
                action(
                    request,
                    "homecare:request",
                    "Request Home Care",
                )
            ],
        )

    # --------------------------------------------------------
    # STAFF-MANAGED KNOWLEDGE BASE
    # --------------------------------------------------------

    articles = staff_knowledge()

    item, score = best_match(question, articles)

    if item and score >= 0.66:

        links = []

        if item["kind"] == "careers":
            links.append(
                action(
                    request,
                    "pages:professionals",
                    "For Healthcare Professionals",
                )
            )

        elif item["kind"] == "about":
            links.append(
                action(
                    request,
                    "pages:about",
                    "About Us",
                )
            )

        elif item["kind"] == "referral":
            links.append(
                action(
                    request,
                    "homecare:referral",
                    "Refer a Patient",
                )
            )

        elif item["kind"] in {
            "services",
            "service",
            "category",
        }:
            links.append(
                action(
                    request,
                    "pages:services",
                    "View Services",
                )
            )

        return result(
            item["body"],
            item["kind"],
            links,
        )

    # --------------------------------------------------------
    # PAYMENT INFORMATION
    # --------------------------------------------------------

    if (
        w
        & {
            "payment",
            "payments",
            "payfast",
            "paypal",
            "bank",
            "transfer",
            "billing",
        }
        or "payment mode" in q
        or "pay for" in q
    ):
        return result(
            payment_answer(),
            "payment",
        )

    # --------------------------------------------------------
    # CONTACT INFORMATION
    # --------------------------------------------------------

    if w & {
        "contact",
        "phone",
        "email",
        "whatsapp",
        "address",
        "location",
    }:

        text, links = contact_answer()

        return result(
            text or "Please use our contact page.",
            "contact",
            links
            + [
                action(
                    request,
                    "pages:contact",
                    "Contact Us",
                )
            ],
        )

    # --------------------------------------------------------
    # CAREERS / JOINING HANDS-ON HEALTH
    # --------------------------------------------------------

    if (
        w
        & {
            "join",
            "career",
            "careers",
            "job",
            "jobs",
            "work",
            "employment",
            "caregiver",
            "recruitment",
        }
    ) and "price" not in w:

        return result(
            "For information about working with "
            "Hands-On Health or collaborating as a "
            "healthcare professional, please visit "
            "our healthcare professionals page "
            "or contact our team. "
            "Application requirements are not currently "
            "available in the chatbot knowledge base.",
            "careers",
            [
                action(
                    request,
                    "pages:professionals",
                    "For Healthcare Professionals",
                ),
                action(
                    request,
                    "pages:contact",
                    "Contact Us",
                ),
            ],
        )

    # --------------------------------------------------------
    # ABOUT HANDS-ON HEALTH
    # --------------------------------------------------------

    if (
        "about us" in q
        or "about hands" in q
        or w
        & {
            "company",
            "organization",
            "organisation",
        }
    ):

        about = [
            record["body"]
            for record in public_knowledge()
            if (record["kind"] == "about" and record["body"])
        ]

        text = (
            "\n\n".join(about[:3])
            if about
            else ("Learn more about Hands-On Health " "on our About Us page.")
        )

        return result(
            text,
            "about",
            [
                action(
                    request,
                    "pages:about",
                    "About Us",
                )
            ],
        )

    # --------------------------------------------------------
    # LEADERSHIP / FOUNDER
    # --------------------------------------------------------

    if w & {
        "founder",
        "ceo",
        "director",
        "leadership",
    }:

        founders = [
            record["body"]
            for record in public_knowledge()
            if record["kind"] == "leadership"
        ]

        return result(
            (
                "\n\n".join(founders[:2])
                if founders
                else ("Please visit our About Us page " "for leadership information.")
            ),
            "leadership",
            [
                action(
                    request,
                    "pages:about",
                    "About Us",
                )
            ],
        )

    # --------------------------------------------------------
    # LIST SERVICES
    # --------------------------------------------------------

    if w & {"service", "services"} and len(w) == 1:

        services = [
            record["title"]
            for record in public_knowledge()
            if record["kind"] == "service"
        ]

        return result(
            (
                "Our active services include: " + ", ".join(services[:20])
                if services
                else "Please view our current services."
            ),
            "services",
            [
                action(
                    request,
                    "pages:services",
                    "View Services",
                )
            ],
        )

    # --------------------------------------------------------
    # SEARCH PUBLIC WEBSITE KNOWLEDGE
    # --------------------------------------------------------

    records = public_knowledge() + articles

    item, score = best_match(
        question,
        records,
    )

    # --------------------------------------------------------
    # OPTIONAL SEMANTIC SEARCH
    # --------------------------------------------------------

    if (not item or score < 0.62) and getattr(
        settings,
        "CHATBOT_SEMANTIC_ENABLED",
        False,
    ):

        try:
            from .semantic import semantic_match

            candidate, semantic_score = semantic_match(
                question,
                records,
            )

            if candidate and semantic_score >= 0.55:
                item = candidate
                score = 1.0

        except (ImportError, ModuleNotFoundError):
            pass

    # --------------------------------------------------------
    # RETURN MATCHED ANSWER
    # --------------------------------------------------------

    if item and score >= 0.62:

        links = []

        if item["kind"] in {
            "service",
            "category",
        }:

            links.append(
                action(
                    request,
                    "pages:services",
                    "View Services",
                )
            )

            links.append(
                action(
                    request,
                    "homecare:request",
                    "Request Home Care",
                )
            )

        elif item["kind"] in {
            "about",
            "leadership",
        }:

            links.append(
                action(
                    request,
                    "pages:about",
                    "About Us",
                )
            )

        elif item["kind"] == "careers":

            links.append(
                action(
                    request,
                    "pages:professionals",
                    "For Healthcare Professionals",
                )
            )

        elif item["kind"] == "referral":

            links.append(
                action(
                    request,
                    "homecare:referral",
                    "Refer a Patient",
                )
            )

        return result(
            item["body"],
            item["kind"],
            links,
        )

    # ========================================================
    # UNANSWERED QUESTION TRACKING
    # ========================================================

    # No reliable match was found.
    # Save the actual visitor question, NOT the Django
    # email message module.

    record_unanswered_question(question)

    # --------------------------------------------------------
    # FALLBACK RESPONSE
    # --------------------------------------------------------

    text, contact_links = contact_answer()

    return result(
        (
            "I could not find a reliable answer "
            "in our published information. "
            "Please contact our team for help." + ("\n\n" + text if text else "")
        ),
        "fallback",
        contact_links
        + [
            action(
                request,
                "pages:contact",
                "Contact Us",
            )
        ],
    )


# ============================================================
# PUBLIC ENDPOINT + CONVERSATION LOGGING
# ============================================================


@require_POST
@csrf_protect
def chatbot_message(request):
    """Keep the existing rules, and log the actual response for review."""
    response = _chatbot_message(request)

    if response.status_code != 200:
        return response

    question = request.POST.get("message", "").strip()
    if not question:
        return response

    try:
        payload = json.loads(response.content.decode("utf-8"))
        reply = payload.get("reply", "")
        source = payload.get("source", "general")

        # Avoid retaining obvious contact details or likely clinical
        # disclosures in the staff review log. This is a conservative
        # safeguard, not a complete medical-data privacy solution.
        sensitive = (
            re.search(r"[\w.+-]+@[\w.-]+\.[\w.-]+", question)
            or re.search(r"\+?\d[\d\s()-]{8,}\d", question)
            or re.search(
                r"\b(?:diagnosed|diagnosis|symptoms|medication|"
                r"pregnant|pregnancy|hiv|cancer|blood pressure|"
                r"my patient|patient name)\b",
                question,
                re.IGNORECASE,
            )
        )

        if reply and not sensitive:
            ChatbotConversationLog.objects.create(
                question=question,
                chatbot_answer=reply,
                answer_source=source,
            )
    except Exception:
        logger.exception("Could not save chatbot conversation log")

    return response
