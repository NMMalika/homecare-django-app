from django import forms

from services.models import Service

from homecare.models import (
    HomeCareRequest,
    CaregiverAssignment,
    CaregiverDailyReport,
    CaregiverPayment,
)


# ============================================================
# SERVICE FORM
# ============================================================

class ServiceForm(forms.ModelForm):

    class Meta:
        model = Service

        fields = [
            "name",
            "slug",
            "category",
            "short_description",
            "description",
            "price",
            "icon_class",
            "image",
            "is_active",
            "order",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Service name",
                }
            ),

            "slug": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "service-slug",
                }
            ),

            "category": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "short_description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Short description",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Full service description",
                }
            ),

            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                }
            ),

            "icon_class": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "fa-solid fa-heart-pulse",
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),

            "order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),
        }


# ============================================================
# HOME CARE REQUEST FORM
# ============================================================

class HomeCareRequestForm(forms.ModelForm):

    class Meta:
        model = HomeCareRequest

        fields = [
            "full_name",
            "phone",
            "email",
            "services",
            "preferred_date",
            "preferred_time",
            "description",
            "admin_notes",
            "status",
        ]

        widgets = {

            # ------------------------------------------------
            # PATIENT DETAILS
            # ------------------------------------------------

            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Patient full name",
                }
            ),

            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Phone number",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email address",
                }
            ),

            # ------------------------------------------------
            # SERVICES
            # ------------------------------------------------

            "services": forms.SelectMultiple(
                attrs={
                    "class": "form-select",
                    "size": "6",
                }
            ),

            # ------------------------------------------------
            # PREFERRED DATE
            # ------------------------------------------------

            "preferred_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            # ------------------------------------------------
            # PREFERRED TIME
            # ------------------------------------------------

            "preferred_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-control",
                }
            ),

            # ------------------------------------------------
            # DESCRIPTION
            # ------------------------------------------------

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Describe the patient's needs, "
                        "condition or requested home care..."
                    ),
                }
            ),

            # ------------------------------------------------
            # ADMIN NOTES
            # ------------------------------------------------

            "admin_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Internal notes for Hands-On Health staff..."
                    ),
                }
            ),

            # ------------------------------------------------
            # STATUS
            # ------------------------------------------------

            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Only display active services
        if "services" in self.fields:
            self.fields["services"].queryset = (
                Service.objects
                .filter(is_active=True)
                .order_by("order", "name")
            )

            self.fields["services"].required = False


# ============================================================
# CAREGIVER ASSIGNMENT FORM
# ============================================================

class CaregiverAssignmentForm(forms.ModelForm):

    class Meta:
        model = CaregiverAssignment

        fields = "__all__"

        widgets = {

            "service_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "service_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-control",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Assignment notes...",
                }
            ),
        }


# ============================================================
# CAREGIVER DAILY REPORT FORM
# ============================================================

class CaregiverDailyReportForm(forms.ModelForm):

    class Meta:
        model = CaregiverDailyReport

        fields = "__all__"

        widgets = {

            "report_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "visit_start": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-control",
                }
            ),

            "visit_end": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-control",
                }
            ),

            "observations": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Patient observations...",
                }
            ),

            "care_provided": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Care provided during the visit...",
                }
            ),

            "progress": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Patient progress...",
                }
            ),

            "concerns": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Any concerns or issues...",
                }
            ),

            "caregiver_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Additional caregiver notes...",
                }
            ),
        }


# ============================================================
# CAREGIVER PAYMENT FORM
# ============================================================

class CaregiverPaymentForm(forms.ModelForm):

    class Meta:
        model = CaregiverPayment

        fields = "__all__"

        widgets = {

            "payment_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "payment_period_start": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "payment_period_end": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "reference": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Payment reference",
                }
            ),

            "method": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Payment method",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Payment notes...",
                }
            ),
        }
    from django import forms

from homecare.models import Caregiver


class StaffCaregiverInviteForm(forms.ModelForm):

    class Meta:
        model = Caregiver

        fields = [
            "name",
            "professional_title",
            "specialization",
            "phone",
            "email",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Caregiver full name",
                }
            ),
            "professional_title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Registered Nurse",
                }
            ),
            "specialization": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. Elderly Care, Palliative Care"
                    ),
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Phone number",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "caregiver@example.com",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        return email