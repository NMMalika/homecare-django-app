from django.contrib import admin
from .models import ChatbotKnowledge


@admin.register(ChatbotKnowledge)
class ChatbotKnowledgeAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_published", "priority", "updated_at")
    list_filter = ("category", "is_published")
    search_fields = ("title", "answer", "keywords")
    list_editable = ("is_published", "priority")
    ordering = ("-priority", "-updated_at")
    fieldsets = (
        ("Public answer", {"fields": ("title", "answer", "category")}),
        (
            "Matching and publication",
            {"fields": ("keywords", "priority", "is_published")},
        ),
    )
