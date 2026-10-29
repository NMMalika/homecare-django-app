from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from chatbot.models import (
    UnansweredQuestion,
    ChatbotConversationLog,
)


def can_manage_chatbot(user):
    return user.is_authenticated and (
        user.is_superuser or (user.is_staff and getattr(user, "role", None) == "ADMIN")
    )


def normalize_question(value):
    return " ".join((value or "").casefold().split()).rstrip("?!., ")


def matching_logs(question):
    """
    Match all conversation logs with the same question,
    including differences in capitalization and spacing.
    """
    normalized = normalize_question(question)

    ids = [
        log.pk
        for log in ChatbotConversationLog.objects.only("pk", "question").iterator()
        if normalize_question(log.question) == normalized
    ]

    return ChatbotConversationLog.objects.filter(pk__in=ids)


@user_passes_test(can_manage_chatbot)
@require_GET
def unanswered_questions(request):
    status = request.GET.get("status", "NEW").upper()

    valid_statuses = {choice[0] for choice in UnansweredQuestion.Status.choices}

    if status not in valid_statuses | {"ALL"}:
        status = "NEW"

    questions = UnansweredQuestion.objects.all()

    if status != "ALL":
        questions = questions.filter(status=status)

    questions = questions.order_by(
        "-last_asked_at",
        "-created_at",
        "-pk",
    )

    return render(
        request,
        "staff/chatbot/unanswered_questions.html",
        {
            "questions": questions,
            "current_status": status,
            "total_unanswered": (
                UnansweredQuestion.objects.filter(status="NEW").count()
            ),
            "total_new": UnansweredQuestion.objects.filter(status="NEW").count(),
            "total_reviewed": UnansweredQuestion.objects.filter(
                status="REVIEWED"
            ).count(),
            "total_resolved": UnansweredQuestion.objects.filter(
                status="RESOLVED"
            ).count(),
            "total_ignored": UnansweredQuestion.objects.filter(
                status="IGNORED"
            ).count(),
            "total_questions": UnansweredQuestion.objects.count(),
        },
    )


@user_passes_test(can_manage_chatbot)
@require_GET
def chatbot_unanswered_train(request, pk):
    """
    Clicking Train marks the question REVIEWED
    and opens the existing training form.
    """

    with transaction.atomic():
        unanswered = get_object_or_404(
            UnansweredQuestion.objects.select_for_update(),
            pk=pk,
        )

        if unanswered.status != "RESOLVED":
            unanswered.status = "REVIEWED"
            unanswered.save(update_fields=["status"])

        log = matching_logs(unanswered.question).order_by("-created_at").first()

        if log is None:
            log = ChatbotConversationLog.objects.create(
                question=unanswered.question,
                chatbot_answer=(
                    "The chatbot could not find a reliable " "answer to this question."
                ),
                answer_source="fallback",
            )

    url = reverse(
        "staff:chatbot_train_answer",
        kwargs={"pk": log.pk},
    )

    return redirect(f"{url}?unanswered_id={unanswered.pk}")


@user_passes_test(can_manage_chatbot)
@require_POST
def chatbot_unanswered_ignore(request, pk):
    """
    Ignore the question without deleting its history.
    """

    with transaction.atomic():
        unanswered = get_object_or_404(
            UnansweredQuestion.objects.select_for_update(),
            pk=pk,
        )

        if unanswered.status == "RESOLVED":
            messages.warning(request, "This question is already resolved.")
        else:
            unanswered.status = "IGNORED"
            unanswered.save(update_fields=["status"])

            messages.success(request, "Question ignored in both dashboards.")

    return redirect(reverse("staff:chatbot_unanswered") + "?status=IGNORED")


@user_passes_test(can_manage_chatbot)
@require_POST
def update_unanswered_status(request, pk):
    """
    Keep the old URL working for compatibility.
    Only Ignore is permitted through this endpoint.
    """

    status = request.POST.get("status", "").upper()

    if status != "IGNORED":
        messages.error(
            request,
            "Use Train / Write Correct Answer to review " "and resolve questions.",
        )
        return redirect("staff:chatbot_unanswered")

    return chatbot_unanswered_ignore(request, pk)
