import re

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


BENGALI_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
PROTECTED_BLOCK = re.compile(
    r"<(script|style|textarea)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
HTML_TAG = re.compile(r"(<[^>]*>)")
VISIBLE_TEXT_ATTRIBUTE = re.compile(
    r"""(?P<prefix>\b(?:title|alt|placeholder|aria-label|aria-valuetext)\s*=\s*)(?P<quote>["'])(?P<value>.*?)(?P=quote)""",
    re.IGNORECASE | re.DOTALL,
)


def localize_html_numbers(html):
    """Localize visible HTML digits without changing scripts or form values."""

    def localize_fragment(fragment):
        parts = HTML_TAG.split(fragment)
        for index in range(0, len(parts), 2):
            parts[index] = parts[index].translate(BENGALI_DIGITS)
        for index in range(1, len(parts), 2):
            parts[index] = VISIBLE_TEXT_ATTRIBUTE.sub(
                lambda match: (
                    match.group("prefix")
                    + match.group("quote")
                    + match.group("value").translate(BENGALI_DIGITS)
                    + match.group("quote")
                ),
                parts[index],
            )
        return "".join(parts)

    localized = []
    position = 0
    for match in PROTECTED_BLOCK.finditer(html):
        localized.append(localize_fragment(html[position : match.start()]))
        localized.append(match.group(0))
        position = match.end()
    localized.append(localize_fragment(html[position:]))
    return "".join(localized)


class BengaliNumberMiddleware:
    """Render Bengali digits in visible Bangla-mode HTML."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        language = getattr(request, "LANGUAGE_CODE", "").split("-", 1)[0]
        if language != "bn" or getattr(response, "streaming", False):
            return response
        if not hasattr(response, "content"):
            return response
        content_type = response.get("Content-Type", "").split(";", 1)[0].lower()
        content_encoding = response.get("Content-Encoding", "").lower()
        if content_type != "text/html" or content_encoding not in {"", "identity"}:
            return response

        charset = response.charset or "utf-8"
        content = response.content.decode(charset)
        if not re.search(r"[0-9]", content):
            return response
        localized = localize_html_numbers(content)
        if localized == content:
            return response
        response.content = localized.encode(charset)
        if "Content-Length" in response:
            response["Content-Length"] = str(len(response.content))
        return response
