import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from core.models import CustomUser


def validate_phone_number(value):
    """Accept common Bangladeshi and international phone formats."""
    if not value:
        return value
    compact = re.sub(r"[\s()-]", "", value)
    if not re.fullmatch(r"\+?\d{7,15}", compact):
        raise ValidationError(
            "Enter a valid phone number using 7 to 15 digits, optionally starting with +."
        )
    return compact


class CustomRegistrationForm(UserCreationForm):
    ROLE_CHOICES = [
        (CustomUser.RoleChoices.DONOR, "Donor"),
        (CustomUser.RoleChoices.NGO, "NGO"),
        (CustomUser.RoleChoices.VOLUNTEER, "Volunteer"),
    ]

    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Your full name"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"autocomplete": "email", "placeholder": "you@example.com"}
        )
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        validators=[validate_phone_number],
        widget=forms.TextInput(
            attrs={"autocomplete": "tel", "placeholder": "+8801XXXXXXXXX"}
        ),
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    profile_pic = forms.ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = (
            "full_name",
            "email",
            "phone_number",
            "role",
            "profile_pic",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_full_name(self):
        full_name = self.cleaned_data["full_name"].strip()
        if len(full_name) < 2:
            raise forms.ValidationError("Enter your full name.")
        return full_name

    def clean_phone_number(self):
        value = self.cleaned_data.get("phone_number", "")
        return validate_phone_number(value.strip()) if value else ""

    def save(self, commit=True):
        user = super().save(commit=False)
        user.full_name = self.cleaned_data["full_name"]
        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data.get("phone_number") or None
        user.role = self.cleaned_data["role"]
        user.profile_pic = self.cleaned_data.get("profile_pic")
        if commit:
            user.save()
        return user


class CustomLoginForm(forms.Form):
    identifier = forms.CharField(
        label="Email or Phone Number",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "placeholder": "you@example.com or +8801XXXXXXXXX",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "placeholder": "Enter your password"}
        )
    )


class ProfileUpdateForm(forms.ModelForm):
    remove_profile_pic = forms.BooleanField(required=False)

    class Meta:
        model = CustomUser
        fields = ("full_name", "phone_number", "profile_pic")
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "phone_number": forms.TextInput(
                attrs={"autocomplete": "tel", "placeholder": "+8801XXXXXXXXX"}
            ),
        }

    def clean_full_name(self):
        full_name = self.cleaned_data["full_name"].strip()
        if len(full_name) < 2:
            raise forms.ValidationError("Enter your full name.")
        return full_name

    def clean_phone_number(self):
        value = self.cleaned_data.get("phone_number", "")
        return validate_phone_number(value.strip()) if value else ""

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("remove_profile_pic"):
            user.profile_pic = None
        if commit:
            user.save()
        return user

