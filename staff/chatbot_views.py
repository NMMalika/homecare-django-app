# staff/chatbot_views.py

from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from chatbot.models import ChatbotKnowledge
from chatbot.models import UnansweredQuestion

def chatbot_staff_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (
            request.user.is_superuser
            or (
                request.user.is_staff and getattr(request.user, "role", None) == "ADMIN"
            )
        ):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


class ChatbotKnowledgeForm(forms.ModelForm):
    class Meta:
        model = ChatbotKnowledge
        fields = "__all__"
        widgets = {
            "answer": forms.Textarea(attrs={"rows": 7}),
            "keywords": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"


@chatbot_staff_required
def chatbot_knowledge_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    articles = ChatbotKnowledge.objects.all().order_by("-id")

    if query:
        articles = articles.filter(
            Q(title__icontains=query)
            | Q(answer__icontains=query)
            | Q(keywords__icontains=query)
        )

    if status == "published":
        articles = articles.filter(is_published=True)
    elif status == "draft":
        articles = articles.filter(is_published=False)

    unanswered_count = UnansweredQuestion.objects.filter(
        status=UnansweredQuestion.Status.NEW
    ).count()

    return render(
        request,
        "staff/chatbot/knowledge_list.html",
        {
            "articles": articles,
            "query": query,
            "status": status,
            "unanswered_count": unanswered_count,
        },
    )


@chatbot_staff_required
def chatbot_knowledge_create(request):
    form = ChatbotKnowledgeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Knowledge article created.")
        return redirect("staff:chatbot_knowledge_list")

    return render(
        request,
        "staff/chatbot/knowledge_form.html",
        {
            "form": form,
            "page_title": "Add Knowledge Article",
        },
    )


@chatbot_staff_required
def chatbot_knowledge_edit(request, pk):
    article = get_object_or_404(ChatbotKnowledge, pk=pk)

    form = ChatbotKnowledgeForm(
        request.POST or None,
        instance=article,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Knowledge article updated.")
        return redirect("staff:chatbot_knowledge_list")

    return render(
        request,
        "staff/chatbot/knowledge_form.html",
        {
            "form": form,
            "page_title": "Edit Knowledge Article",
        },
    )


@chatbot_staff_required
@require_POST
def chatbot_knowledge_toggle(request, pk):
    article = get_object_or_404(ChatbotKnowledge, pk=pk)

    article.is_published = not article.is_published
    article.save(update_fields=["is_published"])

    messages.success(request, "Publication status updated.")
    return redirect("staff:chatbot_knowledge_list")


@chatbot_staff_required
@require_POST
def chatbot_knowledge_delete(request, pk):
    article = get_object_or_404(ChatbotKnowledge, pk=pk)
    article.delete()

    messages.success(request, "Knowledge article deleted.")
    return redirect("staff:chatbot_knowledge_list")
