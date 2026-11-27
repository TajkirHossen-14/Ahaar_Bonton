import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.models import CustomUser


def validate_phone_number(value):
    """Accept common Bangladeshi and international phone formats."""
    if not value:
        return value
    compact = re.sub(r"[\s()-]", "", value)
    if not re.fullmatch(r"\+?\d{7,15}", compact):
        raise ValidationError(
            _("Enter a valid phone number using 7 to 15 digits, optionally starting with +.")
        )
    return compact


class CustomRegistrationForm(UserCreationForm):
    ROLE_CHOICES = [
        (CustomUser.RoleChoices.DONOR, _("Donor")),
        (CustomUser.RoleChoices.NGO, _("NGO")),
        (CustomUser.RoleChoices.VOLUNTEER, _("Volunteer")),
    ]

    full_name = forms.CharField(
        max_length=255,
        label=_("Full name"),
        widget=forms.TextInput(attrs={"autocomplete": "name", "placeholder": _("Your full name")}),
    )
    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(
            attrs={"autocomplete": "email", "placeholder": "you@example.com"}
        )
    )
    phone_number = forms.CharField(
        max_length=20,
        label=_("Phone number"),
        required=False,
        validators=[validate_phone_number],
        widget=forms.TextInput(
            attrs={"autocomplete": "tel", "placeholder": "+8801XXXXXXXXX"}
        ),
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES, label=_("I want to join as"))
    profile_pic = forms.ImageField(required=False, label=_("Profile photo"))

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
            raise forms.ValidationError(_("An account with this email already exists."))
        return email

    def clean_full_name(self):
        full_name = self.cleaned_data["full_name"].strip()
        if len(full_name) < 2:
            raise forms.ValidationError(_("Enter your full name."))
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
        label=_("Email or phone number"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "placeholder": "you@example.com or +8801XXXXXXXXX",
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "placeholder": _("Enter your password")}
        )
    )


class ProfileUpdateForm(forms.ModelForm):
    remove_profile_pic = forms.BooleanField(required=False, label=_("Remove profile photo"))

    class Meta:
        model = CustomUser
        fields = ("full_name", "phone_number", "profile_pic")
        labels = {
            "full_name": _("Full name"),
            "phone_number": _("Phone number"),
            "profile_pic": _("Profile photo"),
        }
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "phone_number": forms.TextInput(
                attrs={"autocomplete": "tel", "placeholder": "+8801XXXXXXXXX"}
            ),
        }

    def clean_full_name(self):
        full_name = self.cleaned_data["full_name"].strip()
        if len(full_name) < 2:
            raise forms.ValidationError(_("Enter your full name."))
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

