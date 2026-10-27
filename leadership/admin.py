from django.contrib import admin
from .models import Founder


@admin.register(Founder)
class FounderAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "position",
        "qualification",
        "is_active",
        "updated_at",
    )

    list_editable = ("is_active",)

    fieldsets = (
        ("Personal Information", {
            "fields": (
                "name",
                "position",
                "qualification",
                "photo",
            )
        }),

        ("Biography", {
            "fields": (
                "biography_1",
                "biography_2",
                "biography_3",
            )
        }),

        ("Leadership Values", {
            "fields": (
                "pillar_1",
                "pillar_2",
                "pillar_3",
            )
        }),

        ("Visibility", {
            "fields": ("is_active",)
        }),
    )