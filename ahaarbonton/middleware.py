from django.conf import settings


class DefaultLanguageMiddleware:
    """Use Bengali for first-time visitors instead of browser preferences."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME, "")
        primary_language = language.split("-", 1)[0]
        if primary_language not in dict(settings.LANGUAGES):
            request.META["HTTP_ACCEPT_LANGUAGE"] = settings.LANGUAGE_CODE
        return self.get_response(request)
