from django import forms
from .models import Founder


class FounderForm(forms.ModelForm):

    class Meta:
        model = Founder

        fields = [
            "name",
            "position",
            "qualification",
            "photo",
            "biography_1",
            "biography_2",
            "biography_3",
            "pillar_1",
            "pillar_2",
            "pillar_3",
            "is_active",
        ]

        widgets = {
            "biography_1": forms.Textarea(attrs={"rows": 4}),
            "biography_2": forms.Textarea(attrs={"rows": 4}),
            "biography_3": forms.Textarea(attrs={"rows": 4}),
        }