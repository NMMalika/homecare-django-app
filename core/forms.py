from django import forms

from core.models import SiteSettings


class SiteSettingsForm(forms.ModelForm):

    class Meta:

        model = SiteSettings

        fields = [
            "business_name",
            "tagline",
            "logo",
            "favicon",

            "email",
            "phone",
            "whatsapp",
            "emergency_phone",
            "address",
            "city",
            "country",
            "website",

            "facebook",
            "instagram",
            "linkedin",
            "tiktok",
            "youtube",

            "google_maps_url",
            "google_business_url",

            "bank_name",
            "account_name",
            "account_number",
            "branch_name",
            "mobile_money_name",
            "mobile_money_number",
            "payment_instructions",
        ]

        widgets = {

            "business_name": forms.TextInput(attrs={
                "placeholder": "Business name",
            }),

            "tagline": forms.TextInput(attrs={
                "placeholder": "Professional, compassionate, and reliable",
            }),

            "email": forms.EmailInput(attrs={
                "placeholder": "Email address",
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

            "google_maps_url": forms.URLInput(attrs={
                "placeholder": "Google Maps URL",
            }),

            "google_business_url": forms.URLInput(attrs={
                "placeholder": "Google Business URL",
            }),

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