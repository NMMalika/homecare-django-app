from django import forms
from django.forms.models import inlineformset_factory

from services.models import Service

from .models import (
    HomeCareRequest,
    Quotation,
    QuotationItem,
    Referral,
    Payment,
)


# ============================================================
# HOME CARE REQUEST FORM
# ============================================================

class HomeCareRequestForm(forms.ModelForm):

    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.filter(is_active=True),
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-select",
                "size": "5",
            }
        ),
        required=False,
        label="Services Required",
    )

    custom_services = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )

    class Meta:
        model = HomeCareRequest

        fields = [
            "full_name",
            "phone",
            "email",
            "location",
            "services",
            "preferred_date",
            "preferred_time",
            "description",
        ]

        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Full Name",
                }
            ),

            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Phone Number",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email Address",
                }
            ),

            "location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Physical Address / Location",
                }
            ),

            "preferred_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "preferred_time": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the care or support required...",
                }
            ),
        }


# ============================================================
# REFERRAL FORM
# ============================================================

class ReferralForm(forms.ModelForm):

    services_needed = forms.ModelMultipleChoiceField(
        queryset=Service.objects.filter(is_active=True),
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-select",
                "size": "5",
            }
        ),
        required=False,
        label="Services Needed",
    )

    custom_services = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )

    class Meta:
        model = Referral

        fields = [
            "referrer_name",
            "referrer_email",
            "referrer_phone",
            "referring_facility",
            "patient_name",
            "patient_email",
            "patient_phone",
            "services_needed",
            "additional_notes",
        ]

        widgets = {
            "referrer_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your Name",
                }
            ),

            "referrer_email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your Email",
                }
            ),

            "referrer_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your Phone",
                }
            ),

            "referring_facility": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Hospital / Clinic / Organization (Optional)"
                    ),
                }
            ),

            "patient_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Patient's Full Name",
                }
            ),

            "patient_email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Patient's Email",
                }
            ),

            "patient_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Patient's Phone",
                }
            ),

            "additional_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Provide any extra clinical notes "
                        "or medical background..."
                    ),
                }
            ),
        }


# ============================================================
# QUOTATION FORM
# ============================================================

class QuotationForm(forms.ModelForm):

    class Meta:
        model = Quotation

        fields = [
            "transportation_fee",
            "discount_code",
            "discount_amount",
            "description",
        ]

        labels = {
            "transportation_fee": "Transportation Fee (N$)",
            "discount_code": "Coupon / Promo Code",
            "discount_amount": "Discount Amount (N$)",
            "description": "Additional Notes / Payment Instructions",
        }

        widgets = {
            "transportation_fee": forms.NumberInput(
                attrs={
                    "class": "form-control quotation-extra",
                    "step": "0.01",
                    "min": "0",
                    "value": "0.00",
                }
            ),

            "discount_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. WELCOME10",
                }
            ),

            "discount_amount": forms.NumberInput(
                attrs={
                    "class": "form-control quotation-extra",
                    "step": "0.01",
                    "min": "0",
                    "value": "0.00",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Add any additional quotation notes, "
                        "payment instructions or terms..."
                    ),
                }
            ),
        }


# ============================================================
# QUOTATION ITEM FORM
# ============================================================

class QuotationItemForm(forms.ModelForm):

    class Meta:
        model = QuotationItem

        fields = [
            "service",
            "name",
            "description",
            "quantity",
            "unit_price",
        ]

        widgets = {
            "service": forms.Select(
                attrs={
                    "class": "form-select quotation-service",
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": "form-control quotation-name",
                    "placeholder": "Custom service name",
                }
            ),

            "description": forms.TextInput(
                attrs={
                    "class": "form-control quotation-description",
                    "placeholder": "Optional description",
                }
            ),

            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control quotation-quantity",
                    "step": "0.01",
                    "min": "0.01",
                    "value": "1",
                }
            ),

            "unit_price": forms.NumberInput(
                attrs={
                    "class": "form-control quotation-unit-price",
                    "step": "0.01",
                    "min": "0",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["service"].required = False
        self.fields["name"].required = False
        self.fields["description"].required = False
        self.fields["quantity"].required = True
        self.fields["unit_price"].required = True

        self.fields["service"].queryset = (
            Service.objects
            .filter(is_active=True)
            .order_by("order", "name")
        )

    def clean(self):
        cleaned_data = super().clean()

        service = cleaned_data.get("service")

        name = (
            cleaned_data.get("name") or ""
        ).strip()

        quantity = cleaned_data.get("quantity")
        unit_price = cleaned_data.get("unit_price")

        # Must either select an existing service
        # or enter a custom service name.
        if not service and not name:
            raise forms.ValidationError(
                "Select an existing service or enter a custom service name."
            )

        if quantity is not None and quantity <= 0:
            raise forms.ValidationError(
                "Quantity must be greater than zero."
            )

        if unit_price is not None and unit_price < 0:
            raise forms.ValidationError(
                "Unit price cannot be negative."
            )

        # If an existing service was selected but
        # no custom name was entered, use the service name.
        if service and not name:
            cleaned_data["name"] = service.name

        return cleaned_data


# ============================================================
# UNLIMITED QUOTATION ITEM FORMSET
# ============================================================

QuotationItemFormSet = inlineformset_factory(
    Quotation,
    QuotationItem,
    form=QuotationItemForm,
    extra=1,
    can_delete=True,
)


# ============================================================
# PAYMENT SUBMISSION FORM
# ============================================================

class PaymentSubmissionForm(forms.ModelForm):

    class Meta:
        model = Payment

        fields = [
            "payment_code",
            "payment_method",
        ]

        widgets = {
            "payment_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Enter your transaction/payment code"
                    ),
                    "autocomplete": "off",
                }
            ),

            "payment_method": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

        labels = {
            "payment_code": "Payment / Transaction Code",
            "payment_method": "Payment Method",
        }

        help_texts = {
            "payment_code": (
                "Enter the transaction reference you received "
                "after making payment."
            ),
        }