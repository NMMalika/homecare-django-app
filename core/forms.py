
import re

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from core.models import SiteSettings


class SiteSettingsForm(forms.ModelForm):

    class Meta:

        model = SiteSettings

        fields = [
            "business_name",
            "tagline",
            "logo",
            "favicon",

            # =====================================================
            # CONTACT INFORMATION
            # =====================================================
            "email",
            "notification_emails",
            "phone",
            "whatsapp",
            "emergency_phone",
            "address",
            "city",
            "country",
            "website",

            # =====================================================
            # SOCIAL MEDIA
            # =====================================================
            "facebook",
            "instagram",
            "linkedin",
            "tiktok",
            "youtube",

            # =====================================================
            # GOOGLE LINKS
            # =====================================================
            "google_maps_url",
            "google_business_url",

            # =====================================================
            # PAYMENT INFORMATION
            # =====================================================
            "bank_name",
            "account_name",
            "account_number",
            "branch_name",
            "mobile_money_name",
            "mobile_money_number",
            "payment_instructions",
        ]

        widgets = {

            # =====================================================
            # BUSINESS INFORMATION
            # =====================================================

            "business_name": forms.TextInput(attrs={
                "placeholder": "Business name",
            }),

            "tagline": forms.TextInput(attrs={
                "placeholder": "Professional, compassionate, and reliable",
            }),

            # =====================================================
            # CONTACT INFORMATION
            # =====================================================

            "email": forms.EmailInput(attrs={
                "placeholder": "Email address",
            }),

            # =====================================================
            # MULTIPLE STAFF NOTIFICATION EMAILS
            # =====================================================

            "notification_emails": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": (
                    "admin@example.com\n"
                    "reception@example.com\n"
                    "accounts@example.com"
                ),
                "class": "form-control",
                "autocomplete": "off",
            }),

            "phone": forms.TextInput(attrs={
                "placeholder": "+264 000 000 000",
            }),

            "whatsapp": forms.TextInput(attrs={
                "placeholder": "+264 000 000 000",
            }),

            "emergency_phone": forms.TextInput(attrs={
                "placeholder": "Emergency phone number",
            }),

            "address": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Physical address",
            }),

            "city": forms.TextInput(attrs={
                "placeholder": "City",
            }),

            "country": forms.TextInput(attrs={
                "placeholder": "Country",
            }),

            "website": forms.URLInput(attrs={
                "placeholder": "https://example.com",
            }),

            # =====================================================
            # SOCIAL MEDIA
            # =====================================================

            "facebook": forms.URLInput(attrs={
                "placeholder": "https://facebook.com/...",
            }),

            "instagram": forms.URLInput(attrs={
                "placeholder": "https://instagram.com/...",
            }),

            "linkedin": forms.URLInput(attrs={
                "placeholder": "https://linkedin.com/...",
            }),

            "tiktok": forms.URLInput(attrs={
                "placeholder": "https://tiktok.com/@...",
            }),

            "youtube": forms.URLInput(attrs={
                "placeholder": "https://youtube.com/...",
            }),

            # =====================================================
            # GOOGLE LINKS
            # =====================================================

            "google_maps_url": forms.URLInput(attrs={
                "placeholder": "Google Maps URL",
            }),

            "google_business_url": forms.URLInput(attrs={
                "placeholder": "Google Business URL",
            }),

            # =====================================================
            # PAYMENT INFORMATION
            # =====================================================

            "bank_name": forms.TextInput(attrs={
                "placeholder": "Bank name",
            }),

            "account_name": forms.TextInput(attrs={
                "placeholder": "Account name",
            }),

            "account_number": forms.TextInput(attrs={
                "placeholder": "Account number",
            }),

            "branch_name": forms.TextInput(attrs={
                "placeholder": "Branch name",
            }),

            "mobile_money_name": forms.TextInput(attrs={
                "placeholder": "e.g. M-Pesa",
            }),

            "mobile_money_number": forms.TextInput(attrs={
                "placeholder": "Mobile money number",
            }),

            "payment_instructions": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Payment instructions shown to clients...",
            }),
        }

        labels = {
            "notification_emails": "Staff Notification Emails",
        }

        help_texts = {
            "notification_emails": (
                "Enter one or more staff email addresses, "
                "separated by commas, semicolons, or new lines. "
                "All configured recipients will receive "
                "website activity notifications."
            ),
        }

    # =========================================================
    # VALIDATE MULTIPLE STAFF NOTIFICATION EMAILS
    # =========================================================

    def clean_notification_emails(self):

        value = self.cleaned_data.get(
            "notification_emails",
            "",
        )

        if not value or not value.strip():
            return ""

        # Split addresses using commas, semicolons, or new lines.
        emails = [
            email.strip()
            for email in re.split(r"[,;\n]+", value)
            if email.strip()
        ]

        # Validate every email address.
        for email in emails:

            try:
                validate_email(email)

            except ValidationError:
                raise ValidationError(
                    f"'{email}' is not a valid email address. "
                    "Please check and try again."
                )

        # Remove duplicate email addresses,
        # ignoring uppercase/lowercase differences.
        unique_emails = []
        seen_emails = set()

        for email in emails:

            normalized_email = email.lower()

            if normalized_email not in seen_emails:

                seen_emails.add(normalized_email)

                unique_emails.append(email)

        # Store each address on its own line.
        return "\n".join(unique_emails)
