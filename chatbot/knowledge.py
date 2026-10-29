"""Approved, live public content only. Never import patient/payment/caregiver records."""

import re
from django.utils.html import strip_tags
from core.models import SiteSettings
from hero.models import HeroSlide
from leadership.models import Founder
from services.models import Service, ServiceCategory
from staff.models import FAQItem


def clean(value):
    return re.sub(r"\s+", " ", strip_tags(str(value or ""))).strip()


def public_knowledge():
    """No cache: staff edits become visible on the next request."""
    records = []
    for faq in FAQItem.objects.filter(is_active=True).order_by("display_order", "id"):
        if clean(faq.answer):
            records.append(
                {"title": clean(faq.question), "body": clean(faq.answer), "kind": "faq"}
            )
    for service in (
        Service.objects.filter(is_active=True)
        .select_related("category")
        .order_by("order", "name")
    ):
        category = clean(service.category.name) if service.category_id else ""
        details = clean(service.description or service.short_description)
        price = (
            f"Published base price: {service.formatted_price}."
            if service.price and service.price > 0
            else "Please request a quotation for pricing."
        )
        body = " ".join(filter(None, [service.name, category, details, price]))
        records.append(
            {
                "title": clean(service.name),
                "body": body,
                "kind": "service",
                "category": category,
            }
        )
    for category in ServiceCategory.objects.filter(services__is_active=True).distinct():
        records.append(
            {
                "title": clean(category.name),
                "body": f"{category.name} is one of our service categories.",
                "kind": "category",
            }
        )
    for slide in HeroSlide.objects.filter(is_active=True).order_by("position"):
        records.append(
            {
                "title": clean(slide.heading),
                "body": " ".join(
                    filter(
                        None,
                        map(clean, [slide.tagline, slide.heading, slide.description]),
                    )
                ),
                "kind": "about",
            }
        )
    for founder in Founder.objects.filter(is_active=True):
        details = [
            founder.name,
            founder.position,
            founder.qualification,
            founder.biography_1,
            founder.biography_2,
            founder.biography_3,
        ]
        records.append(
            {
                "title": f"Founder {clean(founder.name)}",
                "body": " ".join(filter(None, map(clean, details))),
                "kind": "leadership",
            }
        )
    return records


def contact_answer():
    s = SiteSettings.load()
    fields = [
        ("Business", s.business_name),
        ("Phone", s.phone),
        ("Email", s.email),
        ("Address", s.address),
        ("City", s.city),
        ("Country", s.country),
    ]
    lines = [f"{label}: {clean(value)}" for label, value in fields if clean(value)]
    links = []
    number = re.sub(r"\D", "", s.whatsapp or "")
    if number:
        links.append({"label": "Chat on WhatsApp", "url": f"https://wa.me/{number}"})
    return "\n".join(lines), links


def payment_answer():
    s = SiteSettings.load()
    lines = []
    if s.bank_name:
        lines.append(f"Bank transfer: {clean(s.bank_name)}.")
    if s.payfast_enabled:
        lines.append("PayFast is available.")
        if s.payfast_instructions:
            lines.append(clean(s.payfast_instructions))
    if s.paypal_enabled:
        lines.append("PayPal is available.")
        if s.paypal_instructions:
            lines.append(clean(s.paypal_instructions))
    if s.payment_instructions:
        lines.append(clean(s.payment_instructions))
    if not lines:
        lines.append(
            "Please contact our team for current payment methods and instructions."
        )
    # Deliberately do not disclose bank account numbers or payment credentials.
    return "\n".join(lines)


def staff_knowledge():
    """Fresh staff-approved articles. No caching of publication state."""
    from .models import ChatbotKnowledge

    return [
        {
            "title": clean(article.title),
            "body": clean(article.answer),
            "kind": article.category,
            "keywords": clean(article.keywords),
            "priority": article.priority,
            "source": "staff_knowledge",
        }
        for article in ChatbotKnowledge.objects.filter(is_published=True)
        if clean(article.answer)
    ]
