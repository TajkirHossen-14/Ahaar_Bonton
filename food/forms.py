from django import forms

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
            "expiry_time",
        ]
        widgets = {
            "expiry_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["expiry_time"].input_formats = ["%Y-%m-%dT%H:%M"]

