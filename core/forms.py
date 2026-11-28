from django import forms
from django.utils.translation import gettext_lazy as _

from food.forms import FoodPostForm
from users.forms import CustomLoginForm, CustomRegistrationForm, ProfileUpdateForm

from .models import Report

__all__ = [
    "CustomRegistrationForm",
    "CustomLoginForm",
    "FoodPostForm",
    "ProfileUpdateForm",
    "ReportForm",
]


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ("reason", "description")
        labels = {
            "reason": _("Reason"),
            "description": _("Details"),
        }
        widgets = {
            "reason": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "maxlength": 1500,
                    "placeholder": _("Add details that will help our team review this report."),
                }
            ),
        }

    def __init__(self, *args, report_type="post", **kwargs):
        super().__init__(*args, **kwargs)
        if report_type == "post":
            self.fields["reason"].choices = [
                choice
                for choice in Report.REASON_CHOICES
                if choice[0] in {"fake_food", "expired", "fraud", "spam", "inappropriate", "other"}
            ]
        else:
            self.fields["reason"].choices = [
                choice
                for choice in Report.REASON_CHOICES
                if choice[0] in {"fraud", "spam", "inappropriate", "other"}
            ]

    def clean_description(self):
        return self.cleaned_data["description"].strip()
