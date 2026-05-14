from abc import ABC, abstractmethod

from django.conf import settings
from django.core.mail import send_mail


class BaseNotification(ABC):
    # OOP: ABSTRACTION - BaseNotification cannot be instantiated directly
    def __init__(self, recipient, subject, message):
        self.recipient = recipient
        self.subject = subject
        self.message = message

    @abstractmethod
    def send(self):
        """Subclasses MUST implement send()."""

    def log(self):
        print(f"[Notification] recipient={self.recipient} subject={self.subject}")

    def get_preview(self):
        return f"{self.subject}: {self.message[:50]}"


class EmailNotification(BaseNotification):
    # OOP: Inheritance + Polymorphism
    def send(self):
        recipient_list = (
            list(self.recipient)
            if isinstance(self.recipient, (list, tuple, set))
            else [self.recipient]
        )
        send_mail(
            subject=self.subject,
            message=self.message,
            from_email=getattr(
                settings, "DEFAULT_FROM_EMAIL", "no-reply@ahaarbonton.local"
            ),
            recipient_list=recipient_list,
            fail_silently=False,
        )
        self.log()


class SMSNotification(BaseNotification):
    def send(self):
        print(f"[SMS] To: {self.recipient} | {self.subject} | {self.message}")
        self.log()


class SystemNotification(BaseNotification):
    def send(self):
        print(f"[SYSTEM] To: {self.recipient} | {self.subject} | {self.message}")
        self.log()


def notify(recipient, subject, message, method="email"):
    method_map = {
        "email": EmailNotification,
        "sms": SMSNotification,
        "system": SystemNotification,
    }
    notification_class = method_map.get(method.lower(), EmailNotification)
    notifier = notification_class(recipient, subject, message)
    notifier.send()
    return notifier


# OOP CONCEPTS IN THIS FILE:
# 1. ABSTRACTION  - BaseNotification(ABC) with @abstractmethod send()
# 2. INHERITANCE  - All 3 subclasses inherit BaseNotification
# 3. POLYMORPHISM - All have send() but behave differently
# 4. ENCAPSULATION - notify() hides which class is used

