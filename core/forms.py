
import re

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from core.models import SiteSettings


class SiteSettingsForm(forms.ModelForm):

    class Meta:
        model = SiteSettings

        fields = [
            # BUSINESS INFORMATION
            "business_name",
            "tagline",
            "logo",
            "favicon",

            # CONTACT INFORMATION
            "email",
            "notification_emails",
            "phone",
            "whatsapp",
            "emergency_phone",
            "address",
            "city",
            "country",
            "website",

            # SOCIAL MEDIA
            "facebook",
            "instagram",
            "linkedin",
            "tiktok",
            "youtube",

            # GOOGLE LINKS
            "google_maps_url",
            "google_business_url",

            # BANK TRANSFER
            "bank_name",
            "account_name",
            "account_number",
            "branch_name",

            # MANUAL PAYFAST
            "payfast_enabled",
            "payfast_payment_url",
            "payfast_instructions",

            # MANUAL PAYPAL
            "paypal_enabled",
            "paypal_email",
            "paypal_payment_url",
            "paypal_instructions",

            # GENERAL PAYMENT INSTRUCTIONS
            "payment_instructions",
        ]

        widgets = {
            # BUSINESS INFORMATION
            "business_name": forms.TextInput(attrs={
                "placeholder": "Business name",
            }),
            "tagline": forms.TextInput(attrs={
                "placeholder": "Professional, compassionate, and reliable",
            }),

            # CONTACT INFORMATION
            "email": forms.EmailInput(attrs={
                "placeholder": "Email address",
            }),
            "notification_emails": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": (
                    "admin@example.com\n"
                    "reception@example.com\n"
                    "accounts@example.com"
                ),
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

            # SOCIAL MEDIA
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

            # GOOGLE LINKS
            "google_maps_url": forms.URLInput(attrs={
                "placeholder": "Google Maps URL",
            }),
            "google_business_url": forms.URLInput(attrs={
                "placeholder": "Google Business URL",
            }),

            # BANK TRANSFER
            "bank_name": forms.TextInput(attrs={
                "placeholder": "Bank name",
            }),
            "account_name": forms.TextInput(attrs={
                "placeholder": "Account holder name",
            }),
            "account_number": forms.TextInput(attrs={
                "placeholder": "Bank account number",
            }),
            "branch_name": forms.TextInput(attrs={
                "placeholder": "Bank branch name",
            }),

            # MANUAL PAYFAST
            "payfast_enabled": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
            "payfast_payment_url": forms.URLInput(attrs={
                "placeholder": "https://...",
            }),
            "payfast_instructions": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": (
                    "Explain how patients should pay using PayFast, "
                    "including how to identify their payment."
                ),
            }),

            # MANUAL PAYPAL
            "paypal_enabled": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
            "paypal_email": forms.EmailInput(attrs={
                "placeholder": "payments@example.com",
            }),
            "paypal_payment_url": forms.URLInput(attrs={
                "placeholder": "https://paypal.me/...",
            }),
            "paypal_instructions": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": (
                    "Explain how patients should pay using PayPal "
                    "and submit their transaction confirmation."
                ),
            }),

            # GENERAL PAYMENT INSTRUCTIONS
            "payment_instructions": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": (
                    "Additional payment instructions shown "
                    "to clients on quotations and payment pages..."
                ),
            }),
        }

        labels = {
            "notification_emails": "Staff Notification Emails",

            "bank_name": "Bank Name",
            "account_name": "Account Holder Name",
            "account_number": "Account Number",
            "branch_name": "Branch Name",

            "payfast_enabled": "Enable Manual PayFast Payments",
            "payfast_payment_url": "PayFast Payment Link",
            "payfast_instructions": "PayFast Payment Instructions",

            "paypal_enabled": "Enable Manual PayPal Payments",
            "paypal_email": "PayPal Business Email",
            "paypal_payment_url": "PayPal Payment Link",
            "paypal_instructions": "PayPal Payment Instructions",

            "payment_instructions": "General Payment Instructions",
        }

        help_texts = {
            "notification_emails": (
                "Enter staff email addresses separated by commas, "
                "semicolons, or new lines. Duplicate addresses "
                "will be removed."
            ),
            "payfast_enabled": (
                "Allow patients to select PayFast and submit "
                "payment proof for staff verification."
            ),
            "payfast_payment_url": (
                "Optional hosted payment link provided by "
                "your PayFast merchant account."
            ),
            "payfast_instructions": (
                "Instructions displayed to patients choosing "
                "PayFast as their payment method."
            ),
            "paypal_enabled": (
                "Allow patients to select PayPal and submit "
                "payment proof for staff verification."
            ),
            "paypal_email": (
                "Email associated with your PayPal Business Account."
            ),
            "paypal_payment_url": (
                "Optional PayPal payment link. "
                "Use a link supported by your account."
            ),
            "paypal_instructions": (
                "Instructions displayed to patients choosing "
                "PayPal as their payment method."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "form-check-input",
                )
            elif not isinstance(field.widget, forms.FileInput):
                field.widget.attrs.setdefault(
                    "class",
                    "form-control",
                )

    # =========================================================
    # VALIDATE STAFF NOTIFICATION EMAILS
    # =========================================================

    def clean_notification_emails(self):
        value = self.cleaned_data.get("notification_emails", "")

        if not value or not value.strip():
            return ""

        emails = [
            email.strip()
            for email in re.split(r"[,;\r\n]+", value)
            if email.strip()
        ]

        unique_emails = []
        seen_emails = set()

        for email in emails:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError(
                    f"'{email}' is not a valid email address. "
                    "Please check and try again."
                )

            normalized_email = email.lower()

            if normalized_email not in seen_emails:
                seen_emails.add(normalized_email)
                unique_emails.append(email)

        return "\n".join(unique_emails)

    # =========================================================
    # VALIDATE MANUAL PAYMENT SETTINGS
    # =========================================================

    def clean(self):
        cleaned_data = super().clean()

        payfast_url = cleaned_data.get("payfast_payment_url")
        payfast_instructions = (
            cleaned_data.get("payfast_instructions") or ""
        ).strip()

        paypal_email = cleaned_data.get("paypal_email")
        paypal_url = cleaned_data.get("paypal_payment_url")

        cleaned_data["payfast_enabled"] = bool(
            payfast_url or payfast_instructions
        )

        cleaned_data["paypal_enabled"] = bool(
            paypal_email or paypal_url
        )

        return cleaned_data