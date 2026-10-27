
from django import forms
from .models import HeroSlide


class HeroSlideForm(forms.ModelForm):
    class Meta:
        model = HeroSlide
        fields = [
            "tagline",
            "heading",
            "description",
            "image",
            "is_active",
        ]
        widgets = {
            "tagline": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Compassionate • Reliable • Dignified",
            }),
            "heading": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Hero heading",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Describe your service...",
            }),
            "image": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/*",
            }),
        }
