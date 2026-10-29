# chatbot/tracking.py

import re

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import UnansweredQuestion

# ============================================================
# NORMALIZE QUESTION
# ============================================================


def normalize_question(question):
    """
    Normalize questions so repeated questions
    are recognized as the same question.

    Example:
        "  WHAT is Home Care?  "
        "what is home care?"

    Both produce the same normalized question.
    """

    question = (question or "").strip().casefold()

    # Remove repeated whitespace.
    question = re.sub(r"\s+", " ", question)

    # Remove trailing punctuation.
    question = question.rstrip("?!., ")

    return question[:500]


# ============================================================
# BASIC PERSONAL INFORMATION CHECK
# ============================================================


def contains_personal_information(question):
    """
    Avoid storing obvious email addresses and phone numbers.

    This is a basic filter, not a complete
    personal-data detection system.
    """

    # Email address.
    if re.search(
        r"[\w.+-]+@[\w.-]+\.\w+",
        question,
    ):
        return True

    # Phone number.
    if re.search(
        r"\+?\d[\d\s().-]{8,}\d",
        question,
    ):
        return True

    return False


# ============================================================
# RECORD UNANSWERED QUESTION
# ============================================================


def record_unanswered_question(question):
    """
    Save unanswered chatbot questions.

    Rules:
        1. Ignore empty questions.
        2. Ignore obvious personal contact information.
        3. Prevent duplicate question records.
        4. Increase occurrences for repeated questions.
        5. Preserve staff review status.
        6. Update last_asked_at.
        7. New questions start with NEW status.
    """

    question = (question or "").strip()

    # --------------------------------------------------------
    # VALIDATE QUESTION
    # --------------------------------------------------------

    if not question:
        return None

    if len(question) > 2000:
        return None

    if contains_personal_information(question):
        return None

    normalized = normalize_question(question)

    if not normalized:
        return None

    # --------------------------------------------------------
    # RECORD QUESTION
    # --------------------------------------------------------

    try:
        with transaction.atomic():

            existing = (
                UnansweredQuestion.objects.select_for_update()
                .filter(normalized_question=normalized)
                .order_by("pk")
                .first()
            )

            if existing:

                # IMPORTANT:
                # Do not change the question's status.
                # Staff may have already reviewed,
                # resolved or ignored it.

                UnansweredQuestion.objects.filter(pk=existing.pk).update(
                    occurrences=F("occurrences") + 1,
                    last_asked_at=timezone.now(),
                )

                return existing

            # ------------------------------------------------
            # CREATE NEW UNANSWERED QUESTION
            # ------------------------------------------------

            return UnansweredQuestion.objects.create(
                question=question,
                normalized_question=normalized,
                status=UnansweredQuestion.Status.NEW,
                occurrences=1,
                last_asked_at=timezone.now(),
            )

    except IntegrityError:
        # Another request may have created the same
        # question at the same time.

        with transaction.atomic():

            existing = (
                UnansweredQuestion.objects.select_for_update()
                .filter(normalized_question=normalized)
                .order_by("pk")
                .first()
            )

            if existing:

                UnansweredQuestion.objects.filter(pk=existing.pk).update(
                    occurrences=F("occurrences") + 1,
                    last_asked_at=timezone.now(),
                )

                return existing

        return None
