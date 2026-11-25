import re
from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from food.services.matching import FoodMatcher

from .models import (
    CustomUser,
    Delivery,
    DonorProfile,
    FoodPost,
    FoodRequest,
    Rating,
    Report,
    VolunteerProfile,
)


class AhaarBontonTests(TestCase):
    password = "Testpass123!"

    def setUp(self):
        cache.clear()
        self.donor = self.create_user("donor", "Donor", "donor@example.com")
        self.volunteer = self.create_user(
            "volunteer", "Volunteer", "volunteer@example.com"
        )
        self.ngo = self.create_user("ngo", "NGO", "ngo@example.com")
        DonorProfile.objects.create(user=self.donor, trust_score=50)
        VolunteerProfile.objects.create(user=self.volunteer)

    def tearDown(self):
        cache.clear()

    def create_user(self, role, name, email):
        return CustomUser.objects.create_user(
            email=email,
            password=self.password,
            full_name=name,
            role=role,
        )

    def create_food_post(self, donor=None, *, expired=False, status="available"):
        return FoodPost.objects.create(
            donor=donor or self.donor,
            title="Prepared meals",
            description="Fresh meals ready for delivery.",
            quantity=10,
            category=FoodPost.CategoryChoices.COOKED,
            location="Dhaka",
            expiry_time=timezone.now()
            + timedelta(hours=-1 if expired else 2),
            status=status,
        )

    def create_approved_delivery(self, *, expired=False, volunteer=True):
        post = self.create_food_post(
            expired=expired,
            status=FoodPost.StatusChoices.CLAIMED,
        )
        food_request = FoodRequest.objects.create(
            ngo=self.ngo,
            food_post=post,
            status=FoodRequest.StatusChoices.APPROVED,
        )
        return Delivery.objects.create(
            food_request=food_request,
            volunteer=self.volunteer if volunteer else None,
            pickup_otp="111111",
            delivery_otp="222222",
        )

    def complete_delivery(self, delivery):
        now = timezone.now()
        delivery.pickup_confirmed = True
        delivery.picked_up_at = now
        delivery.delivery_confirmed = True
        delivery.delivered_at = now
        delivery.is_confirmed = True
        delivery.status = Delivery.StatusChoices.DELIVERED
        delivery.food_request.status = FoodRequest.StatusChoices.COMPLETED
        delivery.food_request.food_post.status = FoodPost.StatusChoices.DELIVERED
        delivery.food_request.save(update_fields=["status"])
        delivery.food_request.food_post.save(update_fields=["status"])
        delivery.save(
            update_fields=[
                "pickup_confirmed",
                "picked_up_at",
                "delivery_confirmed",
                "delivered_at",
                "is_confirmed",
                "status",
            ]
        )
        return delivery

    def test_registering_a_volunteer_creates_a_profile_with_full_score(self):
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "New Volunteer",
                "email": "new-volunteer@example.com",
                "role": CustomUser.RoleChoices.VOLUNTEER,
                "password1": self.password,
                "password2": self.password,
            },
        )

        self.assertRedirects(response, reverse("volunteer_dashboard"))
        volunteer = CustomUser.objects.get(email="new-volunteer@example.com")
        self.assertEqual(volunteer.volunteer_profile.trust_score, 100)

    def test_registration_rejects_case_insensitive_duplicate_email(self):
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Duplicate User",
                "email": "DONOR@EXAMPLE.COM",
                "role": CustomUser.RoleChoices.DONOR,
                "password1": self.password,
                "password2": self.password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "email", "An account with this email already exists."
        )
        self.assertEqual(CustomUser.objects.count(), 3)

    def test_registration_rejects_invalid_phone_number(self):
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Invalid Phone",
                "email": "invalid-phone@example.com",
                "phone_number": "123abc",
                "role": CustomUser.RoleChoices.DONOR,
                "password1": self.password,
                "password2": self.password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].has_error("phone_number"))

    def test_successful_delivery_increases_scores_once_and_caps_at_100(self):
        delivery = self.create_approved_delivery()
        delivery.pickup_confirmed = True
        delivery.status = Delivery.StatusChoices.PICKED_UP
        delivery.picked_up_at = timezone.now()
        delivery.save(update_fields=["pickup_confirmed", "status", "picked_up_at"])
        self.client.force_login(self.volunteer)

        with patch("core.views.notify"):
            response = self.client.post(
                reverse("confirm_delivery", args=[delivery.pk]), {"otp": "222222"}
            )
            repeated = self.client.post(
                reverse("confirm_delivery", args=[delivery.pk]), {"otp": "222222"}
            )

        self.assertRedirects(response, reverse("volunteer_dashboard"))
        self.assertRedirects(repeated, reverse("volunteer_dashboard"))
        delivery.refresh_from_db()
        self.donor.donor_profile.refresh_from_db()
        self.volunteer.volunteer_profile.refresh_from_db()
        self.assertTrue(delivery.is_confirmed)
        self.assertEqual(delivery.food_request.status, FoodRequest.StatusChoices.COMPLETED)
        self.assertEqual(delivery.food_request.food_post.status, FoodPost.StatusChoices.DELIVERED)
        self.assertEqual(self.donor.donor_profile.trust_score, 55)
        self.assertEqual(self.volunteer.volunteer_profile.trust_score, 100)

    def test_delivery_cannot_be_confirmed_before_pickup(self):
        delivery = self.create_approved_delivery()
        self.client.force_login(self.volunteer)

        response = self.client.post(
            reverse("confirm_delivery", args=[delivery.pk]), {"otp": "222222"}
        )

        self.assertRedirects(response, reverse("volunteer_dashboard"))
        delivery.refresh_from_db()
        self.volunteer.volunteer_profile.refresh_from_db()
        self.assertFalse(delivery.is_confirmed)
        self.assertEqual(self.volunteer.volunteer_profile.trust_score, 100)

    def test_wrong_otp_does_not_penalize_and_locks_after_five_attempts(self):
        delivery = self.create_approved_delivery()
        self.client.force_login(self.volunteer)

        for _ in range(5):
            self.client.post(
                reverse("confirm_pickup", args=[delivery.pk]), {"otp": "000000"}
            )
        locked_response = self.client.post(
            reverse("confirm_pickup", args=[delivery.pk]), {"otp": "111111"}
        )

        self.assertRedirects(locked_response, reverse("volunteer_dashboard"))
        delivery.refresh_from_db()
        self.volunteer.volunteer_profile.refresh_from_db()
        self.assertFalse(delivery.pickup_confirmed)
        self.assertEqual(self.volunteer.volunteer_profile.trust_score, 100)
        self.assertIn(
            "Too many incorrect attempts",
            list(locked_response.wsgi_request._messages)[-1].message,
        )

    def test_expired_assigned_delivery_is_processed_once(self):
        delivery = self.create_approved_delivery(expired=True)

        expired_count = FoodMatcher().auto_expire_old_posts()
        repeated_count = FoodMatcher().auto_expire_old_posts()

        delivery.refresh_from_db()
        self.donor.donor_profile.refresh_from_db()
        self.volunteer.volunteer_profile.refresh_from_db()
        self.assertEqual(expired_count, 1)
        self.assertEqual(repeated_count, 0)
        self.assertEqual(delivery.food_request.food_post.status, FoodPost.StatusChoices.EXPIRED)
        self.assertEqual(delivery.food_request.status, FoodRequest.StatusChoices.REJECTED)
        self.assertEqual(self.donor.donor_profile.trust_score, 48)
        self.assertEqual(self.volunteer.volunteer_profile.trust_score, 97)

    def test_live_stats_count_time_expired_posts_as_expired(self):
        self.create_food_post(expired=True)

        stats = FoodMatcher().get_stats()

        self.assertEqual(stats["available"], 0)
        self.assertEqual(stats["expired"], 1)
        self.assertEqual(stats["total"], 1)

    def test_request_approval_rejects_competing_requests_and_cannot_repeat(self):
        post = self.create_food_post()
        other_ngo = self.create_user("ngo", "Other NGO", "other-ngo@example.com")
        first = FoodRequest.objects.create(ngo=self.ngo, food_post=post)
        second = FoodRequest.objects.create(ngo=other_ngo, food_post=post)
        self.client.force_login(self.donor)

        with patch("core.views.notify"):
            response = self.client.post(
                reverse("handle_request", args=[first.pk]), {"action": "approve"}
            )
            repeated = self.client.post(
                reverse("handle_request", args=[first.pk]), {"action": "approve"}
            )

        self.assertRedirects(response, reverse("donor_requests"))
        self.assertRedirects(repeated, reverse("donor_requests"))
        first.refresh_from_db()
        second.refresh_from_db()
        post.refresh_from_db()
        self.assertEqual(first.status, FoodRequest.StatusChoices.APPROVED)
        self.assertEqual(second.status, FoodRequest.StatusChoices.REJECTED)
        self.assertEqual(post.status, FoodPost.StatusChoices.CLAIMED)
        self.assertTrue(hasattr(first, "delivery"))

    def test_expired_delivery_cannot_be_accepted(self):
        delivery = self.create_approved_delivery(expired=True, volunteer=False)
        self.client.force_login(self.volunteer)

        response = self.client.post(reverse("accept_delivery", args=[delivery.pk]))

        self.assertRedirects(response, reverse("volunteer_dashboard"))
        delivery.refresh_from_db()
        self.assertIsNone(delivery.volunteer)

    def test_only_delivery_participants_can_rate(self):
        delivery = self.create_approved_delivery()
        delivery.pickup_confirmed = True
        delivery.status = Delivery.StatusChoices.PICKED_UP
        delivery.picked_up_at = timezone.now()
        delivery.delivery_confirmed = True
        delivery.is_confirmed = True
        delivery.status = Delivery.StatusChoices.DELIVERED
        delivery.delivered_at = timezone.now()
        delivery.food_request.status = FoodRequest.StatusChoices.COMPLETED
        delivery.food_request.food_post.status = FoodPost.StatusChoices.DELIVERED
        delivery.food_request.save(update_fields=["status"])
        delivery.food_request.food_post.save(update_fields=["status"])
        delivery.save(
            update_fields=[
                "pickup_confirmed", "status", "picked_up_at",
                "delivery_confirmed", "is_confirmed", "delivered_at",
            ]
        )
        outsider = self.create_user("ngo", "Outsider", "outsider@example.com")
        self.client.force_login(outsider)

        response = self.client.post(
            reverse("submit_rating", args=[delivery.pk]),
            {"rating_type": "ngo_to_donor", "score": "5", "comment": "Great"},
        )

        self.assertRedirects(response, outsider.get_dashboard_url())
        self.assertFalse(Rating.objects.exists())

    def test_participant_rating_is_unique(self):
        delivery = self.create_approved_delivery()
        delivery.pickup_confirmed = True
        delivery.status = Delivery.StatusChoices.PICKED_UP
        delivery.picked_up_at = timezone.now()
        delivery.delivery_confirmed = True
        delivery.is_confirmed = True
        delivery.status = Delivery.StatusChoices.DELIVERED
        delivery.delivered_at = timezone.now()
        delivery.food_request.status = FoodRequest.StatusChoices.COMPLETED
        delivery.food_request.food_post.status = FoodPost.StatusChoices.DELIVERED
        delivery.food_request.save(update_fields=["status"])
        delivery.food_request.food_post.save(update_fields=["status"])
        delivery.save(
            update_fields=[
                "pickup_confirmed", "status", "picked_up_at",
                "delivery_confirmed", "is_confirmed", "delivered_at",
            ]
        )
        self.client.force_login(self.ngo)
        payload = {"rating_type": "ngo_to_donor", "score": "5", "comment": "Great"}

        self.client.post(reverse("submit_rating", args=[delivery.pk]), payload)
        self.client.post(reverse("submit_rating", args=[delivery.pk]), payload)

        self.assertEqual(Rating.objects.count(), 1)
        self.assertEqual(Rating.objects.get().rated_user, self.donor)

    def test_self_report_is_rejected_and_duplicate_report_is_handled(self):
        post = self.create_food_post()
        self.client.force_login(self.donor)
        own_response = self.client.get(reverse("report_post", args=[post.pk]))
        self.assertRedirects(own_response, self.donor.get_dashboard_url())

        self.client.force_login(self.ngo)
        payload = {"reason": "fake_food", "description": "The details are misleading."}
        self.client.post(reverse("report_post", args=[post.pk]), payload)
        duplicate = self.client.post(reverse("report_post", args=[post.pk]), payload)

        self.assertEqual(Report.objects.count(), 1)
        self.assertRedirects(duplicate, self.ngo.get_dashboard_url())
        self.assertIn(
            "already reported",
            list(duplicate.wsgi_request._messages)[-1].message,
        )

    def test_sensitive_actions_reject_get_requests(self):
        post = self.create_food_post()
        self.client.force_login(self.donor)

        self.assertEqual(self.client.get(reverse("delete_food", args=[post.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("admin_expire_food")).status_code, 405)
        self.client.force_login(self.volunteer)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        delivery = self.create_approved_delivery(volunteer=False)
        self.assertEqual(self.client.get(reverse("accept_delivery", args=[delivery.pk])).status_code, 405)

    def test_logout_post_ends_session(self):
        self.client.force_login(self.donor)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_rejects_external_next_url(self):
        response = self.client.post(
            reverse("login") + "?next=https://evil.example/",
            {"identifier": self.donor.email, "password": self.password},
        )

        self.assertRedirects(response, self.donor.get_dashboard_url())

    def test_notification_failure_does_not_break_delivery_acceptance(self):
        delivery = self.create_approved_delivery(volunteer=False)
        self.client.force_login(self.volunteer)

        with patch("delivery.services.notification.send_mail", return_value=0):
            response = self.client.post(reverse("accept_delivery", args=[delivery.pk]))

        self.assertRedirects(response, reverse("volunteer_dashboard"))
        delivery.refresh_from_db()
        self.assertEqual(delivery.volunteer, self.volunteer)

    def test_public_pages_render_for_anonymous_visitors(self):
        post = self.create_food_post()
        post.latitude = 23.8103
        post.longitude = 90.4125
        post.save(update_fields=["latitude", "longitude"])

        for url_name in ("home", "transparency", "leaderboard", "food_map", "heatmap"):
            with self.subTest(page=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(reverse("user_profile", args=[self.donor.pk])).status_code, 200)

        home = self.client.get(reverse("home"))
        self.assertContains(home, 'class="mobile-theme-controls"')
        self.assertContains(home, 'class="mobile-account-actions"')

    def test_map_json_escapes_user_generated_script_content(self):
        post = self.create_food_post()
        malicious_title = '</script><script>alert("xss")</script>'
        post.title = malicious_title
        post.latitude = 23.8103
        post.longitude = 90.4125
        post.save(update_fields=["title", "latitude", "longitude"])

        response = self.client.get(reverse("food_map"))

        self.assertContains(response, "\\u003C/script\\u003E")
        self.assertNotContains(response, malicious_title)

    def test_leaderboard_exposes_trust_score_rankings(self):
        self.donor.donor_profile.trust_score = 90
        self.donor.donor_profile.save(update_fields=["trust_score"])
        self.volunteer.volunteer_profile.trust_score = 80
        self.volunteer.volunteer_profile.save(update_fields=["trust_score"])

        response = self.client.get(reverse("leaderboard"))

        self.assertContains(response, "By trust score")
        self.assertContains(response, "Donor")
        self.assertContains(response, "Volunteer")
        self.assertIn("trust_donors", response.context)
        self.assertIn("trust_volunteers", response.context)

    def test_ngo_dashboard_identifies_food_expiring_within_six_hours(self):
        urgent_post = self.create_food_post()
        later_post = self.create_food_post()
        later_post.expiry_time = timezone.now() + timedelta(hours=10)
        later_post.save(update_fields=["expiry_time"])
        self.client.force_login(self.ngo)

        response = self.client.get(reverse("ngo_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-expiring="yes"')
        self.assertContains(response, 'data-expiring="no"')
        self.assertTrue(urgent_post.expires_within_six_hours)
        self.assertFalse(later_post.expires_within_six_hours)

    def test_heatmap_counts_time_expired_mapped_posts_as_expired(self):
        post = self.create_food_post(expired=True)
        post.latitude = 23.8103
        post.longitude = 90.4125
        post.save(update_fields=["latitude", "longitude"])

        response = self.client.get(reverse("heatmap"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["available"], 0)
        self.assertEqual(response.context["stats"]["expired"], 1)
        self.assertContains(response, 'id="heatmap-data"')

    def test_authenticated_pages_render_for_each_role(self):
        post = self.create_food_post()
        admin = self.create_user("admin", "Admin", "admin@example.com")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=["is_staff", "is_superuser"])

        role_pages = {
            "donor": ["donor_dashboard", "donor_requests", "add_food", "profile"],
            "ngo": ["ngo_dashboard", "ngo_my_requests", "profile"],
            "volunteer": ["volunteer_dashboard", "profile"],
            "admin": ["admin_dashboard", "admin:index"],
        }
        users = {
            "donor": self.donor,
            "ngo": self.ngo,
            "volunteer": self.volunteer,
            "admin": admin,
        }

        for role, page_names in role_pages.items():
            self.client.force_login(users[role])
            for page_name in page_names:
                with self.subTest(role=role, page=page_name):
                    self.assertEqual(self.client.get(reverse(page_name)).status_code, 200)
            if role == "donor":
                self.assertEqual(self.client.get(reverse("edit_food", args=[post.pk])).status_code, 200)
            if role == "ngo":
                self.assertEqual(self.client.get(reverse("request_food", args=[post.pk])).status_code, 200)
                self.assertEqual(self.client.get(reverse("report_post", args=[post.pk])).status_code, 200)
                self.assertEqual(self.client.get(reverse("report_user", args=[self.donor.pk])).status_code, 200)

    def test_food_forms_include_leaflet_assets(self):
        post = self.create_food_post()
        self.client.force_login(self.donor)

        responses = (
            self.client.get(reverse("add_food")),
            self.client.get(reverse("edit_food", args=[post.pk])),
        )
        for response in responses:
            self.assertContains(response, "leaflet@1.9.4/dist/leaflet.css")
            self.assertContains(response, "leaflet@1.9.4/dist/leaflet.js")

    def test_offline_page_never_contains_personalized_navigation(self):
        self.client.force_login(self.donor)
        response = self.client.get(reverse("offline"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.donor.full_name)
        self.assertNotContains(response, "Log out")
    def test_service_worker_is_served_with_root_scope(self):
        response = self.client.get(reverse("service_worker"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("application/javascript"))
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        self.assertIn("no-cache", response["Cache-Control"])
        script = b"".join(response.streaming_content)
        self.assertIn(b"const CACHE_NAME = 'ahaarbonton-v", script)
        self.assertIn(b"const OFFLINE_PATH = '/offline/'", script)
        response.close()
        home = self.client.get(reverse("home"))
        self.assertContains(
            home,
            "navigator.serviceWorker.register('/service-worker.js')",
        )
        self.assertNotContains(home, "/static/js/service-worker.js")
    def test_login_and_register_use_focused_split_layout(self):
        for page_name, eye_count in (("login", 1), ("register", 2)):
            with self.subTest(page=page_name):
                response = self.client.get(reverse(page_name))
                self.assertContains(response, '<body class="auth-page">')
                self.assertNotContains(response, '<header class="site-header">')
                self.assertNotContains(response, '<footer class="site-footer">')
                self.assertContains(response, 'class="auth-story"')
                self.assertContains(response, 'class="auth-network"')
                self.assertNotContains(response, 'class="auth-story-art"')
                self.assertContains(response, 'class="auth-shell')
                self.assertEqual(response.content.count(b'href="#i-eye-off"'), eye_count)
                self.assertNotContains(response, b'href="#i-eye"')
    def test_error_flash_uses_standard_alert_styling(self):
        delivery = self.create_approved_delivery()
        self.client.force_login(self.volunteer)

        response = self.client.post(
            reverse("confirm_pickup", args=[delivery.pk]), {"otp": "000000"}, follow=True
        )

        self.assertContains(response, 'class="alert alert-error"')

    def test_food_form_validates_future_expiry_and_coordinate_pair(self):
        from food.forms import FoodPostForm

        payload = {
            "title": "Fresh meals",
            "description": "Fresh meals for twenty people.",
            "quantity": 20,
            "category": FoodPost.CategoryChoices.COOKED,
            "location": "Dhaka",
            "latitude": "23.8103",
            "longitude": "",
            "expiry_time": (timezone.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
        }
        form = FoodPostForm(payload)

        self.assertFalse(form.is_valid())
        self.assertIn("expiry_time", form.errors)
        self.assertIn("__all__", form.errors)

    def test_registration_role_preselection_only_accepts_public_roles(self):
        for role in ("donor", "ngo", "volunteer"):
            with self.subTest(role=role):
                response = self.client.get(reverse("register"), {"role": role})
                self.assertEqual(response.context["form"]["role"].value(), role)

        for role in ("admin", "staff", ""):
            with self.subTest(invalid_role=role):
                response = self.client.get(reverse("register"), {"role": role})
                self.assertIsNone(response.context["form"]["role"].value())

    def test_login_preserves_safe_local_next_url(self):
        next_url = reverse("donor_requests")
        login_page = self.client.get(reverse("login"), {"next": next_url})
        self.assertContains(
            login_page,
            f'<input type="hidden" name="next" value="{next_url}">',
        )

        response = self.client.post(
            reverse("login"),
            {
                "identifier": self.donor.email,
                "password": self.password,
                "next": next_url,
            },
        )

        self.assertRedirects(response, next_url)

    def test_home_calls_to_action_match_authentication_state(self):
        anonymous_home = self.client.get(reverse("home"))
        self.assertContains(anonymous_home, f'href="{reverse("register")}"')
        self.assertContains(anonymous_home, "Get Started")
        self.assertContains(anonymous_home, "Every Meal")
        self.assertContains(anonymous_home, "Matters.")
        self.assertContains(anonymous_home, "Bangladesh’s Surplus Food Redistribution Platform")
        self.assertContains(anonymous_home, "Create your account")
        self.assertNotContains(anonymous_home, "Bangladesh’s community food network")
        self.assertNotContains(anonymous_home, "Create your free account")
        self.assertNotContains(anonymous_home, "Good food. Shared forward.")
        self.assertNotContains(anonymous_home, "When food has a deadline, every detail matters.")
        self.assertNotContains(anonymous_home, "Choose the role that fits your day-to-day life.")
        self.assertContains(anonymous_home, 'class="container home-impact-section"')
        self.assertNotContains(anonymous_home, "Join the movement")
        self.assertNotContains(anonymous_home, 'class="hero-live"')
        self.assertNotContains(anonymous_home, 'class="hero-art-frame"')
        self.assertNotContains(anonymous_home, 'class="hero-route"')
        self.assertContains(anonymous_home, 'class="hero-note"')
        self.assertContains(anonymous_home, "Successful deliveries")
        self.assertNotContains(anonymous_home, "Servings delivered")
        self.assertEqual(anonymous_home.content.count(b'class="impact-stat"'), 3)
        self.assertContains(anonymous_home, "One platform. Three ways to help.")

        self.client.force_login(self.donor)
        member_home = self.client.get(reverse("home"))
        self.assertContains(member_home, 'href="/dashboard/"')
        self.assertContains(member_home, "Go to your dashboard")
        self.assertNotContains(member_home, "One platform. Three ways to help.")

    def test_public_maps_expose_designed_empty_states(self):
        food_map = self.client.get(reverse("food_map"))
        heatmap = self.client.get(reverse("heatmap"))

        self.assertContains(food_map, "The map is ready for its first donation.")
        self.assertContains(food_map, "No mapped donations yet")
        self.assertContains(heatmap, "No location data yet")
        self.assertContains(heatmap, 'id="heatmapMessageTitle"')

    def test_transparency_chart_data_is_paired_and_accessible(self):
        self.create_food_post()
        self.create_food_post()

        response = self.client.get(reverse("transparency"))

        for prefix in ("category", "status", "monthly"):
            labels = response.context[f"{prefix}_chart_labels"]
            values = response.context[f"{prefix}_chart_values"]
            self.assertEqual(len(labels), len(values))
            self.assertContains(response, f'id="{prefix}ChartLabels"')
            self.assertContains(response, f'id="{prefix}ChartValues"')
            self.assertContains(response, f'id="{prefix}ChartSummary"')
        self.assertEqual(sum(response.context["category_chart_values"]), 2)
        self.assertEqual(sum(response.context["status_chart_values"]), 2)
        self.assertEqual(len(response.context["monthly_chart_labels"]), 12)
        self.assertContains(response, "data-chart-fallback")

    def test_profile_avatar_endpoint_returns_a_small_webp_image(self):
        buffer = BytesIO()
        Image.new("RGB", (400, 300), (20, 120, 80)).save(buffer, format="PNG")

        with TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                self.donor.profile_pic.save(
                    "qa-avatar.png",
                    SimpleUploadedFile("qa-avatar.png", buffer.getvalue()),
                    save=True,
                )
                response = self.client.get(
                    reverse("profile_avatar", args=[self.donor.pk])
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/webp")
        with Image.open(BytesIO(response.content)) as avatar:
            self.assertEqual(avatar.format, "WEBP")
            self.assertLessEqual(max(avatar.size), 96)

    def test_public_profile_uses_verified_rating_and_role_activity(self):
        delivery = self.complete_delivery(self.create_approved_delivery())
        Rating.objects.create(
            rater=self.ngo,
            rated_user=self.donor,
            delivery=delivery,
            rating_type="ngo_to_donor",
            score=4,
        )

        response = self.client.get(reverse("user_profile", args=[self.donor.pk]))

        self.assertEqual(response.context["rating_percentage"], 80.0)
        self.assertEqual(response.context["rating_count"], 1)
        self.assertEqual(response.context["activity_count"], 1)
        self.assertEqual(response.context["activity_label"], "Donations delivered")
        self.assertContains(response, "4.0 out of 5 stars")

    def test_volunteer_active_count_excludes_completed_deliveries(self):
        self.complete_delivery(self.create_approved_delivery())
        self.client.force_login(self.volunteer)

        response = self.client.get(reverse("volunteer_dashboard"))

        self.assertEqual(response.context["active_count"], 0)
        self.assertEqual(response.context["completed_count"], 1)
        self.assertContains(response, "<strong>0</strong><small>Active</small>")

    def test_rating_forms_have_unique_ids_across_deliveries(self):
        first = self.complete_delivery(self.create_approved_delivery())
        second = self.complete_delivery(self.create_approved_delivery())
        self.client.force_login(self.ngo)

        response = self.client.get(reverse("ngo_my_requests"))
        html = response.content.decode()
        input_ids = re.findall(r'<input[^>]+id="(score-[^"]+)"', html)
        label_targets = re.findall(r'<label[^>]+for="(score-[^"]+)"', html)

        self.assertEqual(len(input_ids), 20)
        self.assertEqual(len(set(input_ids)), 20)
        self.assertEqual(set(input_ids), set(label_targets))
        self.assertIn(f"score-ngo_to_donor-{first.pk}-1", input_ids)
        self.assertIn(f"score-ngo_to_volunteer-{second.pk}-5", input_ids)

    def test_food_map_keeps_coordinates_rounded_for_authenticated_users(self):
        post = self.create_food_post()
        post.latitude = 23.8103456
        post.longitude = 90.4123456
        post.save(update_fields=["latitude", "longitude"])
        self.client.force_login(self.donor)

        response = self.client.get(reverse("food_map"))
        map_post = response.context["posts_data"][0]

        self.assertEqual(map_post["lat"], 23.81)
        self.assertEqual(map_post["lng"], 90.412)

    def test_ngo_dashboard_uses_annotated_donor_rating(self):
        delivery = self.complete_delivery(self.create_approved_delivery())
        Rating.objects.create(
            rater=self.ngo,
            rated_user=self.donor,
            delivery=delivery,
            rating_type="ngo_to_donor",
            score=4,
        )
        self.create_food_post()
        self.client.force_login(self.ngo)

        response = self.client.get(reverse("ngo_dashboard"))

        self.assertEqual(response.context["posts"][0].donor_avg_rating, 4.0)
        self.assertContains(response, 'aria-label="Rated 4.0 out of 5"')

    @override_settings(DEBUG=False)
    def test_custom_404_page_is_used_outside_debug(self):
        response = self.client.get("/__qa_nonexistent__/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(
            response,
            "This page has moved on.",
            status_code=404,
        )

    def test_food_countdown_display_is_human_readable(self):
        post = self.create_food_post()
        post.expiry_time = timezone.now() + timedelta(hours=2, minutes=30)

        self.assertRegex(post.time_remaining_display, r"^\d+h \d+m$")
        self.assertNotIn("microsecond", post.time_remaining_display)

        post.expiry_time = timezone.now() - timedelta(seconds=1)
        self.assertEqual(post.time_remaining_display, "0m")

    def test_admin_dashboard_hides_unavailable_django_admin_links(self):
        admin = self.create_user("admin", "Limited Admin", "limited-admin@example.com")
        admin.is_staff = True
        admin.save(update_fields=["is_staff"])
        self.client.force_login(admin)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertFalse(response.context["can_access_django_admin"])
        self.assertNotContains(response, reverse("admin:index"))
        self.assertContains(response, 'href="#reports-title"')
        self.assertContains(response, 'href="#recent-posts-title"')
        self.assertContains(response, "Django admin shortcuts require a staff account")

    def test_admin_dashboard_preserves_accessible_tables_and_expiry_action(self):
        admin = self.create_user("admin", "Admin", "admin@example.com")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(admin)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertContains(response, 'class="sr-only admin-table-caption"')
        self.assertContains(response, 'scope="col"')
        self.assertContains(
            response,
            f'action="{reverse("admin_expire_food")}"',
        )
        self.assertContains(response, "Run expiry check")
        self.assertTrue(response.context["can_access_django_admin"])
        self.assertContains(response, reverse("admin:index"))
