
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm


class CaregiverLoginForm(AuthenticationForm):
    """
    Login form specifically for caregivers.

    Uses Django's standard AuthenticationForm behaviour while
    providing caregiver-friendly field labels and styling.
    """

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
        """
        Important:
        AuthenticationForm expects request as the first argument.

        The form data must remain inside *args / **kwargs and should
        NOT be passed twice.
        """
        super().__init__(request, *args, **kwargs)

        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control",
            }
        )

        self.fields["password"].widget.attrs.update(
            {
                "class": "form-control",
            }
        )

