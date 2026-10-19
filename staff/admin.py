
from django.contrib import admin
from .models import FAQItem, QuestionFormSettings, CustomerQuestion


@admin.register(QuestionFormSettings)
class QuestionFormSettingsAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "updated_at")
    fields = (
        "badge_text",
        "title",
        "description",
        "submit_button_text",
        "topics",
        "is_active",
    )


@admin.register(CustomerQuestion)
class CustomerQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "topic",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at", "topic")
    search_fields = ("name", "email", "phone", "question")
    readonly_fields = ("created_at", "updated_at", "replied_at")
    
@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = (
        "question",
        "display_order",
        "is_active",
        "updated_at",
    )
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("question", "answer")
    ordering = ("display_order", "id")