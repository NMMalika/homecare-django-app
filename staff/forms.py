import re
from datetime import timedelta

from django import forms
from django.db.models import Case, When, Value, IntegerField

from services.models import Service

from homecare.models import (
    HomeCareRequest,
    CaregiverAssignment,
    CaregiverDailyReport,
    CaregiverPayment,
    Caregiver,
)

# ============================================================
# SERVICE FORM
# ============================================================


class ServiceForm(forms.ModelForm):

    DEFAULT_ICON = "fa-solid fa-heart-pulse"

    icon_class = forms.CharField(
        required=False,
        label="Icon Class",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "fa-solid fa-heart-pulse",
                "autocomplete": "off",
            }
        ),
        help_text=("Optional. Leave blank to use the default heart icon."),
    )

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

    def clean_icon_class(self):

        icon = (self.cleaned_data.get("icon_class") or "").strip()

        return icon or self.DEFAULT_ICON


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
            "services": forms.SelectMultiple(
                attrs={
                    "class": "form-select",
                    "size": "6",
                }
            ),
            "preferred_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "preferred_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-control",
                }
            ),
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
            "admin_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Internal notes for Hands-On Health staff...",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if "services" in self.fields:

            self.fields["services"].queryset = Service.objects.filter(
                is_active=True
            ).order_by("order", "name")

            self.fields["services"].required = False


# ============================================================
# CAREGIVER ASSIGNMENT FORM — LOCATION-AWARE RANKING
# ============================================================


def _normalise_location(value):
    """Normalise location text for a forgiving, case-insensitive comparison."""
    value = (value or "").strip().lower()
    value = re.sub(r"\bnamibia\b", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _location_parts(value):
    """Split a comma/semicolon-separated location list into clean values."""
    return [
        _normalise_location(part)
        for part in re.split(r"[,;\n]+", value or "")
        if _normalise_location(part)
    ]


def _caregiver_matches_location(caregiver, request_location):
    preferred = _location_parts(getattr(caregiver, "preferred_working_locations", ""))
    requested = _location_parts(request_location)

    if not preferred or not requested:
        return False

    # Match complete location entries first, while also allowing entries such
    # as "Windhoek, Khomas Region" to match a request in "Windhoek".
    for pref in preferred:
        for req in requested:
            if pref == req or pref in req or req in pref:
                return True
    return False


class LocationRankedCaregiverField(forms.ModelChoiceField):
    """Show matching caregivers first and mark their names in the dropdown."""

    def __init__(self, *args, request_location="", **kwargs):
        self.request_location = request_location or ""
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        name = str(obj)
        if _caregiver_matches_location(obj, self.request_location):
            return f"✓ LOCATION MATCH — {name}"
        return name


# ============================================================
# CAREGIVER ASSIGNMENT FORM
# ============================================================


class CaregiverAssignmentForm(forms.ModelForm):

    class Meta:
        model = CaregiverAssignment

        fields = [
            "homecare_request",
            "caregiver",
            "duration",
            "start_date",
            "end_date",
            "service_date",
            "service_time",
            "report_frequency",
            "notes",
        ]

        widgets = {
            "homecare_request": forms.Select(attrs={"class": "form-select"}),
            "duration": forms.Select(
                attrs={
                    "class": "form-select",
                    "id": "id_duration",
                }
            ),
            "start_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                    "id": "id_start_date",
                },
                format="%Y-%m-%d",
            ),
            "end_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                    "id": "id_end_date",
                    "readonly": "readonly",
                },
                format="%Y-%m-%d",
            ),
            "service_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                },
                format="%Y-%m-%d",
            ),
            "service_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-control",
                },
                format="%H:%M",
            ),
            "report_frequency": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Assignment notes...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        homecare_request = kwargs.pop(
            "homecare_request",
            None,
        )

        super().__init__(*args, **kwargs)

        # ----------------------------------------------------
        # RESOLVE HOME CARE REQUEST
        # ----------------------------------------------------

        if homecare_request is None and self.instance.pk:
            homecare_request = self.instance.homecare_request

        if homecare_request is None:

            request_id = (
                self.data.get("homecare_request")
                if self.is_bound
                else self.initial.get("homecare_request")
            )

            if request_id:

                try:
                    homecare_request = HomeCareRequest.objects.get(
                        pk=getattr(request_id, "pk", request_id)
                    )

                except (
                    HomeCareRequest.DoesNotExist,
                    TypeError,
                    ValueError,
                ):
                    homecare_request = None

        # ----------------------------------------------------
        # INITIAL ASSIGNMENT DATE
        # ----------------------------------------------------

        if not self.is_bound and not self.instance.pk:

            if homecare_request:

                self.initial.setdefault(
                    "start_date",
                    homecare_request.preferred_date,
                )

                self.initial.setdefault(
                    "service_time",
                    homecare_request.preferred_time,
                )

            start_date = self.initial.get("start_date")

            duration = self.initial.get(
                "duration",
                CaregiverAssignment.Duration.ONE_DAY,
            )

            if start_date:

                if duration == CaregiverAssignment.Duration.ONE_WEEK:
                    self.initial["end_date"] = start_date + timedelta(days=6)

                else:
                    self.initial["end_date"] = start_date

        # ----------------------------------------------------
        # LOCATION-AWARE CAREGIVER RANKING
        # ----------------------------------------------------

        request_location = (
            getattr(homecare_request, "location", "") if homecare_request else ""
        )

        caregiver_field = self.fields["caregiver"]

        base_queryset = Caregiver.objects.all()

        matching_ids = [
            caregiver.pk
            for caregiver in base_queryset
            if _caregiver_matches_location(
                caregiver,
                request_location,
            )
        ]

        approved_active_ids = list(
            base_queryset.filter(
                verification_status=(Caregiver.VerificationStatus.APPROVED),
                is_active=True,
            ).values_list("pk", flat=True)
        )

        priority = Case(
            When(
                pk__in=[pk for pk in matching_ids if pk in approved_active_ids],
                then=Value(0),
            ),
            When(
                pk__in=approved_active_ids,
                then=Value(1),
            ),
            When(
                pk__in=matching_ids,
                then=Value(2),
            ),
            default=Value(3),
            output_field=IntegerField(),
        )

        ranked_queryset = base_queryset.annotate(
            _assignment_priority=priority
        ).order_by(
            "_assignment_priority",
            "name",
        )

        self.fields["caregiver"] = LocationRankedCaregiverField(
            queryset=ranked_queryset,
            required=caregiver_field.required,
            label=caregiver_field.label,
            help_text=caregiver_field.help_text,
            initial=caregiver_field.initial,
            widget=caregiver_field.widget,
            empty_label=getattr(
                caregiver_field,
                "empty_label",
                "---------",
            ),
            request_location=request_location,
        )

        self.fields["caregiver"].widget.attrs.update({"class": "form-select"})

        # ----------------------------------------------------
        # DATE FIELDS
        # ----------------------------------------------------

        self.fields["start_date"].required = True

        # Calculated server-side rather than trusted from POST.
        self.fields["end_date"].required = False

        self.fields["duration"].required = True

        self.fields["report_frequency"].required = True

        # Legacy field is maintained automatically.
        self.fields["service_date"].required = False

    # ========================================================
    # VALIDATE AND CALCULATE ASSIGNMENT DATES
    # ========================================================

    def clean(self):

        cleaned_data = super().clean()

        duration = cleaned_data.get("duration")

        start_date = cleaned_data.get("start_date")

        if not start_date or not duration:
            return cleaned_data

        if duration == CaregiverAssignment.Duration.ONE_DAY:

            end_date = start_date

        elif duration == CaregiverAssignment.Duration.ONE_WEEK:

            end_date = start_date + timedelta(days=6)

        else:

            self.add_error(
                "duration",
                "Please select a valid assignment duration.",
            )

            return cleaned_data

        # Always calculate dates on the server.
        cleaned_data["end_date"] = end_date

        # Keep legacy service_date synchronized.
        cleaned_data["service_date"] = start_date

        return cleaned_data


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


# ============================================================
# STAFF CAREGIVER INVITATION FORM
# ============================================================


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
                    "placeholder": ("e.g. Elderly Care, Palliative Care"),
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

        return self.cleaned_data["email"].strip().lower()
