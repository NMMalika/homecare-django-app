from django.contrib import admin

from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):

    fieldsets = (
        (
            "Business Information",
            {
                "fields": (
                    "business_name",
                    "tagline",
                    "logo",
                    "favicon",
                )
            },
        ),

        (
            "Contact Information",
            {
                "fields": (
                    "email",
                    "phone",
                    "whatsapp",
                    "emergency_phone",
                    "address",
                    "city",
                    "country",
                    "website",
                )
            },
        ),

        (
            "Social Media",
            {
                "fields": (
                    "facebook",
                    "instagram",
                    "linkedin",
                    "tiktok",
                    "youtube",
                )
            },
        ),

        (
            "Maps & Google Business",
            {
                "fields": (
                    "google_maps_url",
                    "google_business_url",
                )
            },
        ),

        (
            "Payment Information",
            {
                "description": (
                    "These details are displayed to clients "
                    "when they receive a home care quotation."
                ),
                "fields": (
                    "bank_name",
                    "account_name",
                    "account_number",
                    "branch_name",
                    "mobile_money_name",
                    "mobile_money_number",
                    "payment_instructions",
                ),
            },
        ),

        (
            "System",
            {
                "fields": (
                    "updated_at",
                )
            },
        ),
    )

    readonly_fields = (
        "updated_at",
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False