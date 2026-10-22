from django import forms
from .models import Testimonial


class TestimonialForm(forms.ModelForm):
    # Form-only field (not stored directly in the Testimonial model)
    relationship = forms.ChoiceField(
        choices=[
            ("client", "Client / Patient"),
            ("family", "Family Member"),
            ("guardian", "Legal Guardian"),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-control custom-select"}),
    )

    # Publishing consent field with default True initial state
    consent_to_publish = forms.BooleanField(
        required=True,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        error_messages={
            "required": "You must give consent to publish your testimonial."
        },
    )

    class Meta:
        model = Testimonial
        fields = [
            "name",
            "is_anonymous",
            "photo",
            "rating",
            "message",
            "consent_to_publish",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control custom-input",
                    "placeholder": "e.g. S. M. or John Doe",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control custom-textarea",
                    "rows": 4,
                    "placeholder": "Share how Hands-on Health helped your family...",
                }
            ),
            "is_anonymous": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
