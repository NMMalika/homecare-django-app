

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from chatbot.models import (
    ChatbotConversationLog,
    UnansweredQuestion,
)

from .chatbot_views import ChatbotKnowledgeForm

# ============================================================
# ACCESS CONTROL
# ============================================================


def check_access(request):
    user = request.user

    if not (
        user.is_authenticated
        and (
            user.is_superuser
            or (user.is_staff and getattr(user, "role", None) == "ADMIN")
        )
    ):
        raise PermissionDenied("You do not have permission to manage chatbot training.")


# ============================================================
# QUESTION MATCHING
# ============================================================


def normalize_question(value):
    """
    Normalize question text for matching across dashboards.
    """
    return " ".join((value or "").casefold().split()).rstrip("?!., ")


def matching_unanswered_questions(question):
    """
    Return unanswered-question records matching this question.
    """
    key = normalize_question(question)

    return [
        item
        for item in UnansweredQuestion.objects.all()
        if normalize_question(item.question) == key
    ]


def matching_conversation_logs(question):
    """
    Return all conversation logs matching this question.
    """
    key = normalize_question(question)

    return [
        item
        for item in ChatbotConversationLog.objects.all()
        if normalize_question(item.question) == key
    ]


# ============================================================
# TRAINING DASHBOARD
# ============================================================


@login_required
def chatbot_training(request):
    check_access(request)

    status = request.GET.get("status", "all")
    search = request.GET.get("q", "").strip()

    logs = ChatbotConversationLog.objects.all()

    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    if status == "unanswered":
        logs = logs.filter(answer_source="fallback")

    elif status == "incorrect":
        logs = logs.filter(review_status="INCORRECT")

    elif status == "trained":
        logs = logs.filter(review_status="TRAINED")

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if search:
        logs = logs.filter(
            Q(question__icontains=search) | Q(chatbot_answer__icontains=search)
        )

    logs = list(logs.order_by("-created_at")[:100])

    # --------------------------------------------------------
    # SYNCHRONIZE QUESTION STATUS
    # --------------------------------------------------------
    # UnansweredQuestion.status is the shared source of truth.
    # This must remain INSIDE chatbot_training().
    # --------------------------------------------------------

    question_map = {
        normalize_question(item.question): item
        for item in UnansweredQuestion.objects.all()
    }

    for log in logs:
        linked_question = question_map.get(normalize_question(log.question))

        log.shared_question_status = linked_question.status if linked_question else None

        log.shared_question_id = linked_question.pk if linked_question else None

    # --------------------------------------------------------
    # DASHBOARD STATISTICS
    # --------------------------------------------------------

    total_questions = ChatbotConversationLog.objects.count()

    total_unanswered = UnansweredQuestion.objects.filter(status="NEW").count()

    total_incorrect = ChatbotConversationLog.objects.filter(
        review_status="INCORRECT"
    ).count()

    total_trained = ChatbotConversationLog.objects.filter(
        review_status="TRAINED"
    ).count()

    return render(
        request,
        "staff/chatbot/training.html",
        {
            "logs": logs,
            "status": status,
            "search": search,
            "total_questions": total_questions,
            "total_unanswered": total_unanswered,
            "total_incorrect": total_incorrect,
            "total_trained": total_trained,
        },
    )


# ============================================================
# MARK ANSWER INCORRECT
# ============================================================


@login_required
@require_POST
def chatbot_mark_incorrect(request, pk):
    check_access(request)

    with transaction.atomic():

        log = get_object_or_404(
            ChatbotConversationLog.objects.select_for_update(),
            pk=pk,
        )

        log.review_status = "INCORRECT"

        log.save(update_fields=["review_status"])

        # Reopen matching unanswered questions for review,
        # without undoing previously published resolutions.
        for question in matching_unanswered_questions(log.question):
            if question.status != "RESOLVED":
                question.status = "REVIEWED"
                question.save(update_fields=["status"])

    messages.success(
        request,
        "Question marked for correction in both dashboards.",
    )

    return redirect("staff:chatbot_training")


# ============================================================
# TRAIN / WRITE CORRECT ANSWER
# ============================================================


@login_required
def chatbot_train_answer(request, pk):
    check_access(request)

    log = get_object_or_404(
        ChatbotConversationLog,
        pk=pk,
    )

    # --------------------------------------------------------
    # FIND LINKED UNANSWERED QUESTION
    # --------------------------------------------------------

    unanswered_id = request.GET.get("unanswered_id", "") or request.POST.get(
        "unanswered_id", ""
    )

    unanswered = None

    if unanswered_id.isdecimal():

        candidate = UnansweredQuestion.objects.filter(pk=int(unanswered_id)).first()

        if candidate and normalize_question(candidate.question) == normalize_question(
            log.question
        ):
            unanswered = candidate

    # Find by question text when opened from Training Center.
    if unanswered is None:

        matching = matching_unanswered_questions(log.question)

        unanswered = matching[0] if matching else None

    # --------------------------------------------------------
    # SAVE AND PUBLISH ANSWER
    # --------------------------------------------------------

    if request.method == "POST":

        form = ChatbotKnowledgeForm(request.POST)

        if form.is_valid():

            with transaction.atomic():

                # Save the verified knowledge article.
                article = form.save(commit=False)

                article.is_published = True
                article.save()

                form.save_m2m()

                # Synchronize every matching conversation log.
                for matching_log in matching_conversation_logs(log.question):
                    matching_log.staff_answer = article.answer
                    matching_log.review_status = "TRAINED"

                    matching_log.save(
                        update_fields=[
                            "staff_answer",
                            "review_status",
                        ]
                    )

                # Resolve every matching unanswered question.
                for question in matching_unanswered_questions(log.question):
                    question.status = "RESOLVED"

                    question.save(update_fields=["status"])

            messages.success(
                request,
                "Correct answer published successfully. "
                "The question is now Resolved in Unanswered "
                "Questions and Trained in the Training Center.",
            )

            if unanswered is not None:
                return redirect(
                    reverse("staff:chatbot_unanswered") + "?status=RESOLVED"
                )

            return redirect("staff:chatbot_training")

    # --------------------------------------------------------
    # OPEN TRAINING FORM
    # --------------------------------------------------------

    else:

        # Mark matching unanswered questions as Reviewed
        # when staff opens the training form.
        for question in matching_unanswered_questions(log.question):
            if question.status != "RESOLVED":
                question.status = "REVIEWED"

                question.save(update_fields=["status"])

        form = ChatbotKnowledgeForm(
            initial={
                "title": log.question[:200],
                "answer": log.staff_answer,
                "is_published": True,
            }
        )

    # --------------------------------------------------------
    # RENDER FORM
    # --------------------------------------------------------

    return render(
        request,
        "staff/chatbot/train_answer.html",
        {
            "log": log,
            "form": form,
            "unanswered": unanswered,
            "unanswered_id": (unanswered.pk if unanswered else None),
        },
    )
