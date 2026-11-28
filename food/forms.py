from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import FoodPost


class FoodPostForm(forms.ModelForm):
    class Meta:
        model = FoodPost
        fields = [
            "title",
            "description",
            "quantity",
            "category",
            "image",
            "location",
            "latitude",
            "longitude",
            "expiry_time",
        ]
        widgets = {
            "expiry_time": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["expiry_time"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["quantity"].min_value = 1
        self.fields["quantity"].widget.attrs["min"] = 1
        self.fields["title"].widget.attrs["placeholder"] = _("e.g. Fresh meals for 20 people")
        self.fields["description"].widget.attrs["rows"] = 4
        self.fields["location"].widget.attrs["placeholder"] = _("Area, street, or landmark")
        field_labels = {
            "title": _("Food title"),
            "description": _("Description"),
            "quantity": _("Quantity"),
            "category": _("Category"),
            "image": _("Food photo"),
            "location": _("Pickup location"),
            "latitude": _("Latitude"),
            "longitude": _("Longitude"),
            "expiry_time": _("Expiry time"),
        }
        for field_name, label in field_labels.items():
            self.fields[field_name].label = label
        self.fields["latitude"].required = False
        self.fields["latitude"].validators = [
            MinValueValidator(-90),
            MaxValueValidator(90),
        ]
        self.fields["longitude"].required = False
        self.fields["longitude"].validators = [
            MinValueValidator(-180),
            MaxValueValidator(180),
        ]

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if len(title) < 3:
            raise forms.ValidationError(_("Enter a descriptive food title."))
        return title

    def clean_description(self):
        description = self.cleaned_data["description"].strip()
        if len(description) < 10:
            raise forms.ValidationError(_("Add a short description of the food and its condition."))
        return description

    def clean_location(self):
        location = self.cleaned_data["location"].strip()
        if len(location) < 2:
            raise forms.ValidationError(_("Enter a pickup location."))
        return location

    def clean_expiry_time(self):
        expiry_time = self.cleaned_data["expiry_time"]
        if expiry_time <= timezone.now():
            raise forms.ValidationError(_("Expiry time must be in the future."))
        return expiry_time

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")
        if (latitude is None) != (longitude is None):
            raise forms.ValidationError(
                _("Provide both latitude and longitude, or leave both blank.")
            )
        return cleaned_data

