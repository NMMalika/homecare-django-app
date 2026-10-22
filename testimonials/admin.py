from django.contrib import admin
from .models import Testimonial


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "rating",
        "status",
        "consent_to_publish",
        "is_anonymous",
        "created_at",
        "approved_at",
    )

    list_filter = (
        "status",
        "rating",
        "consent_to_publish",
        "is_anonymous",
        "created_at",
    )

    search_fields = ("name", "email", "message")
    readonly_fields = ("created_at", "updated_at", "approved_at")
    list_per_page = 25
    date_hierarchy = "created_at"

    actions = ("approve_testimonials", "reject_testimonials")

    @admin.action(description="Approve selected testimonials")
    def approve_testimonials(self, request, queryset):
        from django.utils import timezone

        queryset.update(
            status=Testimonial.Status.APPROVED,
            approved_at=timezone.now(),
        )

    @admin.action(description="Reject selected testimonials")
    def reject_testimonials(self, request, queryset):
        queryset.update(
            status=Testimonial.Status.REJECTED,
            approved_at=None,
        )

    fieldsets = (
        (
            "Reviewer",
            {
                "fields": (
                    "name",
                    "email",
                    "is_anonymous",
                    "photo",
                    "submitted_by",
                )
            },
        ),
        ("Testimonial", {"fields": ("rating", "message", "consent_to_publish")}),
        ("Moderation", {"fields": ("status", "staff_notes", "approved_at")}),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
