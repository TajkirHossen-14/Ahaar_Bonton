from django.core.management.base import BaseCommand

from food.services.matching import FoodMatcher


class Command(BaseCommand):
    help = "Mark expired food posts and decrease donor trust scores"

    def handle(self, *args, **kwargs):
        count = FoodMatcher().auto_expire_old_posts()
        if count > 0:
            self.stdout.write(self.style.SUCCESS(f"Expired {count} post(s)."))
        else:
            self.stdout.write(self.style.WARNING("No posts to expire."))
