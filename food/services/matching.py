from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.models import FoodPost


class FoodMatcher:
    # OOP: Encapsulation - private __queryset, all food logic in one class
    def __init__(self):
        self.__queryset = FoodPost.objects.filter(status=FoodPost.StatusChoices.AVAILABLE)

    def get_priority_posts(self):
        return self.__queryset.order_by("expiry_time")

    def get_expiring_soon(self, hours=6):
        cutoff = timezone.now() + timedelta(hours=hours)
        return self.__queryset.filter(expiry_time__lte=cutoff)

    def get_by_category(self, category):
        return self.__queryset.filter(category=category)

    def get_stats(self):
        queryset = FoodPost.objects.all()
        return {
            "total": queryset.count(),
            "available": queryset.filter(status=FoodPost.StatusChoices.AVAILABLE).count(),
            "claimed": queryset.filter(status=FoodPost.StatusChoices.CLAIMED).count(),
            "delivered": queryset.filter(status=FoodPost.StatusChoices.DELIVERED).count(),
            "expired": queryset.filter(status=FoodPost.StatusChoices.EXPIRED).count(),
        }

    def auto_expire_old_posts(self):
        now = timezone.now()
        posts = self.__queryset.filter(expiry_time__lte=now).select_related("donor")
        expired_count = 0

        with transaction.atomic():
            for post in posts:
                post.status = FoodPost.StatusChoices.EXPIRED
                post.save(update_fields=["status"])

                donor_profile = getattr(post.donor, "donor_profile", None)
                if donor_profile is not None:
                    donor_profile.decrease_score()

                expired_count += 1

        return expired_count

