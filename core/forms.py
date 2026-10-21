
import re

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from core.models import SiteSettings


class SiteSettingsForm(forms.ModelForm):

    class Meta:

        model = SiteSettings

        fields = [
            # =====================================================
            # BUSINESS INFORMATION
            # =====================================================
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
            # BANK TRANSFER
            # =====================================================
            "bank_name",
            "account_name",
            "account_number",
            "branch_name",

            # =====================================================
            # PAYFAST
            # =====================================================
            "payfast_enabled",
            "payfast_merchant_id",
            "payfast_merchant_key",
            "payfast_passphrase",
            "payfast_sandbox",

            # =====================================================
            # PAYPAL
            # =====================================================
            "paypal_enabled",
            "paypal_email",
            "paypal_client_id",
            "paypal_secret",
            "paypal_sandbox",

            # =====================================================
            # PAYMENT INSTRUCTIONS
            # =====================================================
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
            # BANK TRANSFER
            # =====================================================

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

            # =====================================================
            # PAYFAST PAYMENT SETTINGS
            # =====================================================

            "payfast_enabled": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),

            "payfast_merchant_id": forms.TextInput(attrs={
                "placeholder": "Enter PayFast Merchant ID",
                "autocomplete": "off",
            }),

            "payfast_merchant_key": forms.TextInput(attrs={
                "placeholder": "Enter PayFast Merchant Key",
                "autocomplete": "off",
            }),

            "payfast_passphrase": forms.PasswordInput(
                render_value=False,
                attrs={
                    "placeholder": (
                        "Leave blank to keep existing passphrase"
                    ),
                    "autocomplete": "new-password",
                },
            ),

            "payfast_sandbox": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),

            # =====================================================
            # PAYPAL PAYMENT SETTINGS
            # =====================================================

            "paypal_enabled": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),

            "paypal_email": forms.EmailInput(attrs={
                "placeholder": "payments@example.com",
            }),

            "paypal_client_id": forms.TextInput(attrs={
                "placeholder": "Enter PayPal Client ID",
                "autocomplete": "off",
            }),

            "paypal_secret": forms.PasswordInput(
                render_value=False,
                attrs={
                    "placeholder": (
                        "Leave blank to keep existing API secret"
                    ),
                    "autocomplete": "new-password",
                },
            ),

            "paypal_sandbox": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),

            # =====================================================
            # PAYMENT INSTRUCTIONS
            # =====================================================

            "payment_instructions": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": (
                    "Additional payment instructions "
                    "shown to clients on quotations..."
                ),
            }),
        }

        labels = {
            "notification_emails": "Staff Notification Emails",

            "bank_name": "Bank Name",
            "account_name": "Account Holder Name",
            "account_number": "Account Number",
            "branch_name": "Branch Name",

            "payfast_enabled": "Enable PayFast Payments",
            "payfast_merchant_id": "PayFast Merchant ID",
            "payfast_merchant_key": "PayFast Merchant Key",
            "payfast_passphrase": "PayFast Passphrase",
            "payfast_sandbox": "PayFast Test Mode",

            "paypal_enabled": "Enable PayPal Payments",
            "paypal_email": "PayPal Business Email",
            "paypal_client_id": "PayPal Client ID",
            "paypal_secret": "PayPal API Secret",
            "paypal_sandbox": "PayPal Test Mode",

            "payment_instructions": "Payment Instructions",
        }

        help_texts = {

            "notification_emails": (
                "Enter one or more staff email addresses, "
                "separated by commas, semicolons, or new lines. "
                "All configured recipients will receive "
                "website activity notifications."
            ),

            "payfast_enabled": (
                "Allow PayFast payments when the payment "
                "gateway integration is configured."
            ),

            "payfast_merchant_id": (
                "Merchant ID provided by PayFast."
            ),

            "payfast_merchant_key": (
                "Merchant Key provided by PayFast."
            ),

            "payfast_passphrase": (
                "PayFast integration passphrase. "
                "Leave blank to retain the existing value."
            ),

            "payfast_sandbox": (
                "Enable for testing. Disable only when "
                "your live PayFast integration is ready."
            ),

            "paypal_enabled": (
                "Allow PayPal payments when the payment "
                "gateway integration is configured."
            ),

            "paypal_email": (
                "Email associated with your PayPal "
                "Business Account."
            ),

            "paypal_client_id": (
                "Client ID from your PayPal Developer Dashboard."
            ),

            "paypal_secret": (
                "PayPal REST API Secret. "
                "Leave blank to retain the existing value."
            ),

            "paypal_sandbox": (
                "Enable for testing. Disable only when "
                "your live PayPal integration is ready."
            ),
        }

    # =========================================================
    # INITIALIZE FORM
    # =========================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Do not expose previously saved secrets in HTML.
        for field_name in (
            "payfast_passphrase",
            "paypal_secret",
        ):
            self.fields[field_name].required = False

        # Provide helpful styling to regular fields.
        for name, field in self.fields.items():

            if isinstance(
                field.widget,
                forms.CheckboxInput,
            ):
                field.widget.attrs.setdefault(
                    "class",
                    "form-check-input",
                )

            elif not isinstance(
                field.widget,
                forms.FileInput,
            ):
                field.widget.attrs.setdefault(
                    "class",
                    "form-control",
                )

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

        # Split using commas, semicolons, or new lines.
        emails = [
            email.strip()
            for email in re.split(r"[,;\r\n]+", value)
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

        # Remove duplicate email addresses.
        unique_emails = []
        seen_emails = set()

        for email in emails:

            normalized_email = email.lower()

            if normalized_email not in seen_emails:

                seen_emails.add(normalized_email)
                unique_emails.append(email)

        # Store each address on its own line.
        return "\n".join(unique_emails)

    # =========================================================
    # VALIDATE PAYFAST SETTINGS
    # =========================================================

    def clean_payfast_passphrase(self):

        value = self.cleaned_data.get(
            "payfast_passphrase",
            "",
        )

        # Keep the existing passphrase if left blank.
        if not value and self.instance.pk:
            return self.instance.payfast_passphrase or ""

        return value

    # =========================================================
    # VALIDATE PAYPAL SETTINGS
    # =========================================================

    def clean_paypal_secret(self):

        value = self.cleaned_data.get(
            "paypal_secret",
            "",
        )

        # Keep the existing API secret if left blank.
        if not value and self.instance.pk:
            return self.instance.paypal_secret or ""

        return value

    # =========================================================
    # VALIDATE ENABLED PAYMENT GATEWAYS
    # =========================================================

    def clean(self):

        cleaned_data = super().clean()

        # =====================================================
        # PAYFAST VALIDATION
        # =====================================================

        if cleaned_data.get("payfast_enabled"):

            merchant_id = cleaned_data.get(
                "payfast_merchant_id",
                "",
            )

            merchant_key = cleaned_data.get(
                "payfast_merchant_key",
                "",
            )

            if not merchant_id:
                self.add_error(
                    "payfast_merchant_id",
                    "Merchant ID is required when PayFast is enabled.",
                )

            if not merchant_key:
                self.add_error(
                    "payfast_merchant_key",
                    "Merchant Key is required when PayFast is enabled.",
                )

        # =====================================================
        # PAYPAL VALIDATION
        # =====================================================

        if cleaned_data.get("paypal_enabled"):

            client_id = cleaned_data.get(
                "paypal_client_id",
                "",
            )

            secret = cleaned_data.get(
                "paypal_secret",
                "",
            )

            if not client_id:
                self.add_error(
                    "paypal_client_id",
                    "Client ID is required when PayPal is enabled.",
                )

            if not secret:
                self.add_error(
                    "paypal_secret",
                    "API Secret is required when PayPal is enabled.",
                )

        return cleaned_data
