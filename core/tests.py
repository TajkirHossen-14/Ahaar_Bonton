from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from food.services.matching import FoodMatcher

from .models import (
    CustomUser,
    Delivery,
    DonorProfile,
    FoodPost,
    FoodRequest,
    VolunteerProfile,
)


class VolunteerTrustScoreTests(TestCase):
    def create_user(self, role, name, email):
        return CustomUser.objects.create_user(
            email=email,
            password="Testpass123!",
            full_name=name,
            role=role,
        )

    def create_food_post(self, donor, *, expired=False, status="available"):
        return FoodPost.objects.create(
            donor=donor,
            title="Prepared meals",
            description="Fresh meals ready for delivery.",
            quantity=10,
            category=FoodPost.CategoryChoices.COOKED,
            image="food_posts/test.jpg",
            location="Dhaka",
            expiry_time=timezone.now()
            + timedelta(hours=-1 if expired else 2),
            status=status,
        )

    def test_registering_a_volunteer_creates_a_profile_with_full_score(self):
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "New Volunteer",
                "email": "new-volunteer@example.com",
                "role": CustomUser.RoleChoices.VOLUNTEER,
                "password1": "Testpass123!",
                "password2": "Testpass123!",
            },
        )

        self.assertRedirects(response, reverse("volunteer_dashboard"))
        volunteer = CustomUser.objects.get(email="new-volunteer@example.com")
        self.assertEqual(volunteer.volunteer_profile.trust_score, 100)

    def test_successful_delivery_keeps_a_full_volunteer_score_capped_at_100(self):
        donor = self.create_user("donor", "Donor", "donor@example.com")
        DonorProfile.objects.create(user=donor, trust_score=50)
        volunteer = self.create_user("volunteer", "Volunteer", "volunteer@example.com")
        VolunteerProfile.objects.create(user=volunteer)
        ngo = self.create_user("ngo", "NGO", "ngo@example.com")
        post = self.create_food_post(donor, status=FoodPost.StatusChoices.CLAIMED)
        food_request = FoodRequest.objects.create(
            ngo=ngo,
            food_post=post,
            status=FoodRequest.StatusChoices.APPROVED,
        )
        delivery = Delivery.objects.create(
            food_request=food_request,
            volunteer=volunteer,
            pickup_confirmed=True,
            delivery_otp="123456",
        )

        self.client.force_login(volunteer)
        with patch("core.views.notify"):
            response = self.client.post(
                reverse("confirm_delivery", args=[delivery.pk]), {"otp": "123456"}
            )

        self.assertRedirects(response, reverse("volunteer_dashboard"))
        delivery.refresh_from_db()
        donor.donor_profile.refresh_from_db()
        volunteer.volunteer_profile.refresh_from_db()
        self.assertTrue(delivery.is_confirmed)
        self.assertEqual(donor.donor_profile.trust_score, 55)
        self.assertEqual(volunteer.volunteer_profile.trust_score, 100)

    def test_expired_assigned_delivery_penalizes_volunteer_by_three(self):
        donor = self.create_user("donor", "Donor", "expired-donor@example.com")
        DonorProfile.objects.create(user=donor, trust_score=50)
        volunteer = self.create_user(
            "volunteer", "Volunteer", "expired-volunteer@example.com"
        )
        VolunteerProfile.objects.create(user=volunteer)
        ngo = self.create_user("ngo", "NGO", "expired-ngo@example.com")
        post = self.create_food_post(
            donor,
            expired=True,
            status=FoodPost.StatusChoices.CLAIMED,
        )
        food_request = FoodRequest.objects.create(
            ngo=ngo,
            food_post=post,
            status=FoodRequest.StatusChoices.APPROVED,
        )
        Delivery.objects.create(food_request=food_request, volunteer=volunteer)

        expired_count = FoodMatcher().auto_expire_old_posts()

        post.refresh_from_db()
        donor.donor_profile.refresh_from_db()
        volunteer.volunteer_profile.refresh_from_db()
        self.assertEqual(expired_count, 1)
        self.assertEqual(post.status, FoodPost.StatusChoices.EXPIRED)
        self.assertEqual(donor.donor_profile.trust_score, 48)
        self.assertEqual(volunteer.volunteer_profile.trust_score, 97)

    def test_leaderboard_and_dashboard_render_trust_score_data(self):
        donor = self.create_user("donor", "Trust Donor", "trust-donor@example.com")
        DonorProfile.objects.create(user=donor, trust_score=90)
        volunteer = self.create_user(
            "volunteer", "Trust Volunteer", "trust-volunteer@example.com"
        )
        VolunteerProfile.objects.create(user=volunteer, trust_score=80)

        leaderboard = self.client.get(reverse("leaderboard"))
        self.assertContains(leaderboard, "By Trust Score")
        self.assertContains(
            leaderboard,
            'id="tab-activity" class="tab-content tab-panel active"',
        )
        self.assertContains(leaderboard, "Trust Donor")
        self.assertContains(leaderboard, "Trust Volunteer")

        self.client.force_login(volunteer)
        dashboard = self.client.get(reverse("volunteer_dashboard"))
        self.assertEqual(dashboard.context["volunteer_profile"], volunteer.volunteer_profile)
        self.assertContains(dashboard, "Trust Score")
