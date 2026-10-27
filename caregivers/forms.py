from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

from accounts.models import User
from homecare.models import Caregiver
from django.db.models import Case, When, Value, IntegerField

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB


class MultipleFileInput(forms.ClearableFileInput):
    """File input that supports selecting more than one file."""

    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Validate and return multiple uploaded files."""

    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []

        files = data if isinstance(data, (list, tuple)) else [data]
        cleaned_files = []

        for uploaded_file in files:
            cleaned = super().clean(uploaded_file, initial)

            if cleaned.size > MAX_UPLOAD_SIZE:
                raise ValidationError(f"{cleaned.name}: file must be 5 MB or smaller.")

            cleaned_files.append(cleaned)

        return cleaned_files


class CaregiverLoginForm(AuthenticationForm):
    """Login form specifically for caregivers."""

    username = forms.CharField(
        label="Username",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your username",
                "autocomplete": "username",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        ),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class CaregiverInvitationRegistrationForm(forms.Form):
    """
    Registration form for a caregiver completing a staff-issued invitation.
    The caregiver remains inactive until an administrator approves them.
    """

    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="First name",
        error_messages={"required": "Please enter your first name."},
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "given-name",
                "placeholder": "Your first name",
            }
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Last name",
        error_messages={"required": "Please enter your last name."},
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "family-name",
                "placeholder": "Your last name",
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        label="Email address",
        disabled=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "autocomplete": "email",
            }
        ),
    )

    phone = forms.CharField(
        max_length=50,
        required=True,
        label="Phone number",
        error_messages={"required": "Please enter your phone number."},
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "tel",
                "placeholder": "e.g. +254 7XX XXX XXX",
            }
        ),
    )

    professional_title = forms.CharField(
        max_length=200,
        required=True,
        label="Professional title",
        error_messages={
            "required": (
                "Please enter your professional title, "
                "such as Caregiver or Registered Nurse."
            )
        },
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. Caregiver, Registered Nurse",
            }
        ),
    )

    specialization = forms.CharField(
        max_length=255,
        required=False,
        label="Specialization",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. Elderly care, palliative care",
            }
        ),
    )

    preferred_working_locations = forms.CharField(
        max_length=1000,
        required=False,
        label="Preferred Working Locations in Namibia",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": (
                    "e.g. Windhoek, Swakopmund, Walvis Bay, "
                    "Oshakati, Rundu"
                ),
            }
        ),
        help_text=(
            "Enter the towns or regions in Namibia where you prefer to work. "
            "Separate multiple locations with commas."
        ),
    )

    licence_number = forms.CharField(
        max_length=150,
        required=False,
        label="Licence / registration number",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter licence number if applicable",
            }
        ),
    )

    licence_issuing_authority = forms.CharField(
        max_length=255,
        required=False,
        label="Licence issuing authority",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. Nursing Council",
            }
        ),
    )

    licence_expiry_date = forms.DateField(
        required=False,
        label="Licence expiry date",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
        error_messages={
            "invalid": ("Enter a valid licence expiry date, or leave it blank.")
        },
    )

    cv = forms.FileField(
        required=True,
        label="CV / Resume",
        error_messages={
            "required": ("Please upload your CV before submitting your application.")
        },
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".pdf,.doc,.docx",
            }
        ),
    )

    cover_letter = forms.FileField(
        required=False,
        label="Cover letter (optional)",
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".pdf,.doc,.docx",
            }
        ),
    )

    licence_document = forms.FileField(
        required=False,
        label="Licence document (optional)",
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png"])],
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".pdf,.jpg,.jpeg,.png",
            }
        ),
    )

    certificates = MultipleFileField(
        required=False,
        label="Professional certificates (optional)",
        widget=MultipleFileInput(
            attrs={
                "class": "form-control",
                "accept": ".pdf,.jpg,.jpeg,.png,.doc,.docx",
            }
        ),
    )

    password = forms.CharField(
        required=True,
        label="Create password",
        error_messages={"required": "Please create a password."},
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Create a strong password",
                "autocomplete": "new-password",
            }
        ),
    )

    password_confirm = forms.CharField(
        required=True,
        label="Confirm password",
        error_messages={"required": ("Please re-enter your password to confirm it.")},
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter the same password again",
                "autocomplete": "new-password",
            }
        ),
    )

    def __init__(self, *args, caregiver=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.caregiver = caregiver

        if caregiver is not None:
            user = getattr(caregiver, "user", None)

            if user:
                self.fields["first_name"].initial = user.first_name
                self.fields["last_name"].initial = user.last_name
                self.fields["email"].initial = user.email or caregiver.email

            self.fields["phone"].initial = caregiver.phone
            self.fields["professional_title"].initial = caregiver.professional_title
            self.fields["specialization"].initial = caregiver.specialization

            # NEW: Populate existing location preferences
            self.fields["preferred_working_locations"].initial = (
                caregiver.preferred_working_locations
            )

            self.fields["licence_number"].initial = caregiver.licence_number
            self.fields["licence_issuing_authority"].initial = (
                caregiver.licence_issuing_authority
            )
            self.fields["licence_expiry_date"].initial = caregiver.licence_expiry_date

    def clean_first_name(self):
        value = self.cleaned_data["first_name"].strip()

        if not value:
            raise forms.ValidationError("Please enter your first name.")

        return value

    def clean_last_name(self):
        value = self.cleaned_data["last_name"].strip()

        if not value:
            raise forms.ValidationError("Please enter your last name.")

        return value

    def clean_phone(self):
        value = self.cleaned_data["phone"].strip()

        if not value:
            raise forms.ValidationError("Please enter your phone number.")

        return value

    def clean_preferred_working_locations(self):
        value = self.cleaned_data.get("preferred_working_locations", "").strip()

        # Normalize comma-separated locations and remove duplicates.
        locations = []
        seen = set()

        for location in value.split(","):
            location = location.strip()

            if location and location.casefold() not in seen:
                locations.append(location)
                seen.add(location.casefold())

        return ", ".join(locations)

    def clean_password(self):
        password = self.cleaned_data.get("password")

        if password:
            user = None

            if self.caregiver is not None:
                user = getattr(self.caregiver, "user", None)

            try:
                validate_password(password, user=user)
            except ValidationError as exc:
                raise forms.ValidationError(list(exc.messages))

        return password

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("password_confirm")

        if password and confirmation and password != confirmation:
            self.add_error(
                "password_confirm",
                "Passwords do not match. Please enter the same password in both fields.",
            )

        for field_name in (
            "cv",
            "cover_letter",
            "licence_document",
        ):
            uploaded = cleaned_data.get(field_name)

            if uploaded and uploaded.size > MAX_UPLOAD_SIZE:
                self.add_error(
                    field_name,
                    "This file is too large. Please upload a file that is 5 MB or smaller.",
                )

        for uploaded in cleaned_data.get("certificates", []):
            if uploaded and uploaded.size > MAX_UPLOAD_SIZE:
                self.add_error(
                    "certificates",
                    f"{uploaded.name} is too large. Each file must be 5 MB or smaller.",
                )

        return cleaned_data


# ============================================================
# CAREGIVER PASSWORD RESET FORM
# ============================================================


class CaregiverPasswordResetForm(PasswordResetForm):

    def get_users(self, email):
        users = super().get_users(email)

        for user in users:
            if user.role != User.Role.CAREGIVER:
                continue

            if not Caregiver.objects.filter(
                user=user,
                verification_status=Caregiver.VerificationStatus.APPROVED,
                is_active=True,
            ).exists():
                continue

            yield user


# ============================================================
# PUBLIC CAREGIVER APPLICATION FORM
# ============================================================


class CaregiverPublicApplicationForm(CaregiverInvitationRegistrationForm):
    """
    Public caregiver application.
    Applicants do not need a staff invitation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(caregiver=None, *args, **kwargs)

        self.fields["email"].disabled = False
        self.fields["email"].required = True

        self.fields["email"].widget.attrs.update(
            {
                "placeholder": "you@example.com",
                "autocomplete": "email",
            }
        )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()

        if not email:
            raise forms.ValidationError("Please enter your email address.")

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account already uses this email address. "
                "Please contact Hands-On Health for assistance."
            )

        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError(
                "This email address is already registered. "
                "Please contact Hands-On Health for assistance."
            )

        return email
