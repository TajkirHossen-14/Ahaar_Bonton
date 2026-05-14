from django import forms
from django.contrib.auth.forms import UserCreationForm

from core.models import CustomUser


class CustomRegistrationForm(UserCreationForm):
    ROLE_CHOICES = [
        (CustomUser.RoleChoices.DONOR, "Donor"),
        (CustomUser.RoleChoices.NGO, "NGO"),
        (CustomUser.RoleChoices.VOLUNTEER, "Volunteer"),
    ]

    full_name = forms.CharField(max_length=255)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=20, required=False)
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
    identifier = forms.CharField(label="Email or Phone Number")
    password = forms.CharField(widget=forms.PasswordInput)


class ProfileUpdateForm(forms.ModelForm):
    remove_profile_pic = forms.BooleanField(required=False)

    class Meta:
        model = CustomUser
        fields = ("full_name", "phone_number", "profile_pic")
        widgets = {
            "phone_number": forms.TextInput(attrs={"placeholder": "+8801XXXXXXXXX"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("remove_profile_pic"):
            user.profile_pic = None
        if commit:
            user.save()
        return user

