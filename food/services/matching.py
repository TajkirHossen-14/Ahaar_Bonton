from datetime import timedelta

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from core.models import Delivery, FoodPost, FoodRequest, VolunteerProfile


class FoodMatcher:
    # OOP: Encapsulation - private __queryset, all food logic in one class
    def __init__(self):
        now = timezone.now()
        self.__queryset = FoodPost.objects.filter(
            status=FoodPost.StatusChoices.AVAILABLE,
            expiry_time__gt=now,
        )

    def get_priority_posts(self):
        return self.__queryset.order_by("expiry_time")

    def get_expiring_soon(self, hours=6):
        cutoff = timezone.now() + timedelta(hours=hours)
        return self.__queryset.filter(expiry_time__lte=cutoff)

    def get_by_category(self, category):
        return self.__queryset.filter(category=category)

    def get_stats(self):
        """Return live counts, including posts whose expiry time has passed."""
        now = timezone.now()
        queryset = FoodPost.objects.all()
        expired_filter = Q(status=FoodPost.StatusChoices.EXPIRED) | Q(
            status__in=[
                FoodPost.StatusChoices.AVAILABLE,
                FoodPost.StatusChoices.CLAIMED,
            ],
            expiry_time__lte=now,
        )
        return {
            "total": queryset.count(),
            "available": queryset.filter(
                status=FoodPost.StatusChoices.AVAILABLE,
                expiry_time__gt=now,
            ).count(),
            "claimed": queryset.filter(
                status=FoodPost.StatusChoices.CLAIMED,
                expiry_time__gt=now,
            ).count(),
            "delivered": queryset.filter(
                status=FoodPost.StatusChoices.DELIVERED
            ).count(),
            "expired": queryset.filter(expired_filter).count(),
            "meals_delivered": queryset.filter(
                status=FoodPost.StatusChoices.DELIVERED
            ).aggregate(total=Sum("quantity"))["total"]
            or 0,
        }

    def auto_expire_old_posts(self):
        """Expire available or claimed posts and penalize an assigned volunteer once."""
        now = timezone.now()
        posts = (
            FoodPost.objects.filter(
                status__in=[
                    FoodPost.StatusChoices.AVAILABLE,
                    FoodPost.StatusChoices.CLAIMED,
                ],
                expiry_time__lte=now,
            )
            .select_related("donor")
            .order_by("pk")
        )
        expired_count = 0

        with transaction.atomic():
            for post in posts.select_for_update():
                was_claimed = post.status == FoodPost.StatusChoices.CLAIMED
                post.status = FoodPost.StatusChoices.EXPIRED
                post.save(update_fields=["status"])

                if was_claimed:
                    FoodRequest.objects.filter(
                        food_post=post,
                        status=FoodRequest.StatusChoices.APPROVED,
                    ).update(status=FoodRequest.StatusChoices.REJECTED)
                    deliveries = Delivery.objects.filter(
                        food_request__food_post=post,
                        volunteer__isnull=False,
                        is_confirmed=False,
                    ).select_related("volunteer")
                    for delivery in deliveries:
                        profile, _ = VolunteerProfile.objects.get_or_create(
                            user=delivery.volunteer
                        )
                        profile.decrease_score()

                donor_profile = getattr(post.donor, "donor_profile", None)
                if donor_profile is not None:
                    donor_profile.decrease_score()

                expired_count += 1

        return expired_count

