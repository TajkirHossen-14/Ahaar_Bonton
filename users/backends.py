from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrPhoneBackend(ModelBackend):
    # OOP: Inheritance - inherits ModelBackend, overrides authenticate()
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        identifier = (
            username
            or kwargs.get("identifier")
            or kwargs.get(getattr(User, "USERNAME_FIELD", "email"))
            or ""
        )
        identifier = str(identifier).strip()

        if not identifier or not password:
            return None

        user = User.objects.filter(email__iexact=identifier).first()
        if user is None:
            user = User.objects.filter(phone_number=identifier).first()
        if user is None:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

