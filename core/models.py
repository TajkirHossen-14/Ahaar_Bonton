import secrets
from datetime import timedelta

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone


def generate_otp():
    return f"{secrets.randbelow(1_000_000):06d}"


def otp_matches(stored_otp, entered_otp):
    return secrets.compare_digest(str(stored_otp), str(entered_otp))


class CustomUserManager(BaseUserManager):
    # OOP: Encapsulation - create_user and create_superuser logic is encapsulated in manager methods.
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email must be provided.")
        if not password:
            raise ValueError("Password must be provided.")

        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", CustomUser.RoleChoices.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    # OOP: Inheritance - CustomUser inherits authentication and permissions behavior.
    class RoleChoices(models.TextChoices):
        DONOR = "donor", "Donor"
        NGO = "ngo", "NGO"
        VOLUNTEER = "volunteer", "Volunteer"
        ADMIN = "admin", "Admin"

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=RoleChoices.choices)
    profile_pic = models.ImageField(upload_to="profiles/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "role"]

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_user_email_case_insensitive"),
        ]

    def save(self, *args, **kwargs):
        self.email = CustomUser.objects.normalize_email(self.email).strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def get_dashboard_url(self):
        # OOP: Polymorphism - same interface, different role-based behavior.
        role_urls = {
            self.RoleChoices.DONOR: "/donor/dashboard/",
            self.RoleChoices.NGO: "/ngo/dashboard/",
            self.RoleChoices.VOLUNTEER: "/volunteer/dashboard/",
            self.RoleChoices.ADMIN: "/admin-panel/dashboard/",
        }
        return role_urls.get(self.role, "/dashboard/")

    def get_average_rating(self):
        from django.db.models import Avg

        avg = self.ratings_received.aggregate(
            Avg('score'))['score__avg']
        return round(avg, 1) if avg else None

    def get_rating_count(self):
        return self.ratings_received.count()

    def get_rating_label(self):
        avg = self.get_average_rating()
        if avg is None:
            return 'No ratings yet'
        elif avg >= 4.5:
            return 'Excellent'
        elif avg >= 3.5:
            return 'Good'
        elif avg >= 2.5:
            return 'Average'
        else:
            return 'Poor'


class DonorProfile(models.Model):
    # OOP: Encapsulation - donor score behavior and validation rules are encapsulated in methods.
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="donor_profile",
    )
    trust_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    def __str__(self):
        return f"DonorProfile<{self.user.email}>"

    def update_trust_score(self, delta):
        self.trust_score = max(0, min(100, self.trust_score + delta))
        self.save(update_fields=["trust_score"])

    def increase_score(self):
        self.update_trust_score(+5)

    def decrease_score(self):
        self.update_trust_score(-2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(trust_score__gte=0) & Q(trust_score__lte=100),
                name="donor_trust_score_between_0_and_100",
            ),
        ]

    def get_score_label(self):
        if self.trust_score >= 85:
            return "Excellent"
        if self.trust_score >= 70:
            return "Good"
        if self.trust_score >= 50:
            return "Average"
        return "Needs Improvement"


class VolunteerProfile(models.Model):
    # OOP: Encapsulation - volunteer trust score behavior is encapsulated in model methods.
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="volunteer_profile",
    )
    trust_score = models.IntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    def __str__(self):
        return f"{self.user.full_name} — Score: {self.trust_score}"

    def update_trust_score(self, delta):
        self.trust_score = max(0, min(100, self.trust_score + delta))
        self.save(update_fields=["trust_score"])

    def increase_score(self):
        """Called when the volunteer successfully completes a delivery."""
        self.update_trust_score(+5)

    def decrease_score(self):
        """Called when an assigned delivery expires before completion."""
        self.update_trust_score(-3)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(trust_score__gte=0) & Q(trust_score__lte=100),
                name="volunteer_trust_score_between_0_and_100",
            ),
        ]

    def get_score_label(self):
        if self.trust_score >= 90:
            return "Excellent"
        if self.trust_score >= 70:
            return "Good"
        if self.trust_score >= 50:
            return "Average"
        return "Needs Improvement"


class FoodPost(models.Model):
    # OOP: Encapsulation - post state transitions and checks are wrapped inside model methods.
    class CategoryChoices(models.TextChoices):
        COOKED = "cooked", "Cooked"
        RAW = "raw", "Raw"
        PACKAGED = "packaged", "Packaged"
        BAKERY = "bakery", "Bakery"

    class StatusChoices(models.TextChoices):
        AVAILABLE = "available", "Available"
        CLAIMED = "claimed", "Claimed"
        DELIVERED = "delivered", "Delivered"
        EXPIRED = "expired", "Expired"

    donor = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="food_posts",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    category = models.CharField(max_length=20, choices=CategoryChoices.choices)
    image = models.ImageField(upload_to="food_posts/", blank=True)
    location = models.CharField(max_length=255)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    expiry_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.AVAILABLE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["expiry_time"]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="food_quantity_must_be_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(latitude__isnull=True, longitude__isnull=True)
                    | Q(
                        latitude__isnull=False,
                        longitude__isnull=False,
                        latitude__gte=-90,
                        latitude__lte=90,
                        longitude__gte=-180,
                        longitude__lte=180,
                    )
                ),
                name="food_coordinates_are_valid_pair",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def is_expired(self):
        return timezone.now() >= self.expiry_time

    def mark_claimed(self):
        self.status = self.StatusChoices.CLAIMED
        self.save(update_fields=["status"])

    def mark_delivered(self):
        self.status = self.StatusChoices.DELIVERED
        self.save(update_fields=["status"])

    def time_remaining(self):
        remaining = self.expiry_time - timezone.now()
        if remaining.total_seconds() <= 0:
            return timedelta(seconds=0)
        return remaining

    @property
    def expires_within_six_hours(self):
        now = timezone.now()
        return now < self.expiry_time <= now + timedelta(hours=6)

    def has_map(self):
        return self.latitude is not None and self.longitude is not None


class FoodRequest(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        COMPLETED = "completed", "Completed"

    ngo = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="food_requests",
    )
    food_post = models.ForeignKey(
        FoodPost,
        on_delete=models.CASCADE,
        related_name="requests",
    )
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("ngo", "food_post")

    def __str__(self):
        return f"FoodRequest<{self.ngo.email} -> {self.food_post.title}>"

    def approve(self):
        """Approve one request and claim the post without race-condition leaks."""
        with transaction.atomic():
            food_request = (
                FoodRequest.objects.select_for_update()
                .select_related("food_post")
                .get(pk=self.pk)
            )
            food_post = FoodPost.objects.select_for_update().get(pk=food_request.food_post_id)

            if food_request.status != self.StatusChoices.PENDING:
                raise ValueError("Only pending requests can be approved.")
            if food_post.status != FoodPost.StatusChoices.AVAILABLE or food_post.is_expired():
                raise ValueError("This food post is no longer available.")

            food_request.status = self.StatusChoices.APPROVED
            food_request.save(update_fields=["status"])
            food_post.mark_claimed()
            FoodRequest.objects.filter(
                food_post=food_post,
                status=self.StatusChoices.PENDING,
            ).exclude(pk=food_request.pk).update(status=self.StatusChoices.REJECTED)

            delivery, _ = Delivery.objects.get_or_create(
                food_request=food_request,
                defaults={
                    "pickup_otp": generate_otp(),
                    "delivery_otp": generate_otp(),
                },
            )
            self.refresh_from_db()
            return delivery

    def reject(self):
        with transaction.atomic():
            food_request = FoodRequest.objects.select_for_update().get(pk=self.pk)
            if food_request.status != self.StatusChoices.PENDING:
                raise ValueError("Only pending requests can be rejected.")
            food_request.status = self.StatusChoices.REJECTED
            food_request.save(update_fields=["status"])
            self.refresh_from_db()


class Delivery(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        PICKED_UP = "picked_up", "Picked Up"
        DELIVERED = "delivered", "Delivered"

    STATUS_CHOICES = StatusChoices.choices

    food_request = models.OneToOneField(
        FoodRequest,
        on_delete=models.CASCADE,
        related_name='delivery'
    )
    volunteer = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='deliveries'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=StatusChoices.PENDING,
    )

    # Donor gives this OTP to Volunteer at pickup
    pickup_otp       = models.CharField(max_length=6, default=generate_otp)
    pickup_confirmed = models.BooleanField(default=False)
    picked_up_at     = models.DateTimeField(
        null=True, blank=True)

    # NGO gives this OTP to Volunteer at delivery
    delivery_otp       = models.CharField(max_length=6, default=generate_otp)
    delivery_confirmed = models.BooleanField(default=False)
    delivered_at       = models.DateTimeField(
        null=True, blank=True)

    is_confirmed = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    # OOP: Encapsulation — pickup logic inside class
    def confirm_pickup(self, entered_otp):
        with transaction.atomic():
            delivery = (
                Delivery.objects.select_for_update()
                .select_related("food_request__food_post")
                .get(pk=self.pk)
            )
            if delivery.pickup_confirmed:
                return "already_confirmed"
            if delivery.volunteer_id is None:
                return "not_assigned"
            if (
                delivery.food_request.status != FoodRequest.StatusChoices.APPROVED
                or delivery.food_request.food_post.status != FoodPost.StatusChoices.CLAIMED
            ):
                return "not_available"
            if delivery.food_request.food_post.is_expired():
                return "expired"
            if not otp_matches(delivery.pickup_otp, entered_otp):
                return "wrong_otp"

            delivery.pickup_confirmed = True
            delivery.status = self.StatusChoices.PICKED_UP
            delivery.picked_up_at = timezone.now()
            delivery.save(update_fields=["pickup_confirmed", "status", "picked_up_at"])
            self.refresh_from_db()
            return "success"

    # OOP: Encapsulation — delivery logic inside class
    def confirm_delivery(self, entered_otp):
        with transaction.atomic():
            delivery = (
                Delivery.objects.select_for_update()
                .select_related("food_request__food_post", "food_request__ngo", "volunteer")
                .get(pk=self.pk)
            )
            if delivery.is_confirmed:
                return "already_confirmed"
            if delivery.volunteer_id is None:
                return "not_assigned"
            if not delivery.pickup_confirmed:
                return "pickup_first"
            if (
                delivery.food_request.status != FoodRequest.StatusChoices.APPROVED
                or delivery.food_request.food_post.status != FoodPost.StatusChoices.CLAIMED
            ):
                return "not_available"
            if delivery.food_request.food_post.is_expired():
                return "expired"
            if not otp_matches(delivery.delivery_otp, entered_otp):
                return "wrong_otp"

            delivery.delivery_confirmed = True
            delivery.is_confirmed = True
            delivery.status = self.StatusChoices.DELIVERED
            delivery.delivered_at = timezone.now()
            delivery.food_request.status = FoodRequest.StatusChoices.COMPLETED
            delivery.food_request.food_post.mark_delivered()
            delivery.food_request.save(update_fields=["status"])
            delivery.save(
                update_fields=[
                    "delivery_confirmed",
                    "is_confirmed",
                    "status",
                    "delivered_at",
                ]
            )

            volunteer_profile, _ = VolunteerProfile.objects.get_or_create(user=delivery.volunteer)
            volunteer_profile.increase_score()
            donor_profile, _ = DonorProfile.objects.get_or_create(
                user=delivery.food_request.food_post.donor
            )
            donor_profile.increase_score()
            self.refresh_from_db()
            return "success"

    def mark_picked_up(self):
        """Mark pickup without an OTP for trusted internal/admin use only."""
        if self.is_confirmed or self.pickup_confirmed:
            raise ValueError("Pickup has already been confirmed.")
        if self.volunteer_id is None:
            raise ValueError("Assign a volunteer before confirming pickup.")
        if self.food_request.food_post.is_expired():
            raise ValueError("Expired food cannot be picked up.")
        self.status = self.StatusChoices.PICKED_UP
        self.pickup_confirmed = True
        self.picked_up_at = timezone.now()
        self.save(update_fields=["status", "pickup_confirmed", "picked_up_at"])

    @property
    def otp(self):
        # Backward compatibility: legacy views/templates may still reference `delivery.otp`.
        return self.delivery_otp

    def __str__(self):
        return f"Delivery — {self.food_request.food_post.title} ({self.get_status_display()})"

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(pickup_confirmed=False) | Q(picked_up_at__isnull=False),
                name="delivery_pickup_requires_timestamp",
            ),
            models.CheckConstraint(
                condition=Q(delivery_confirmed=False) | Q(delivered_at__isnull=False),
                name="delivery_completion_requires_timestamp",
            ),
            models.CheckConstraint(
                condition=~Q(status="picked_up")
                | Q(pickup_confirmed=True, picked_up_at__isnull=False),
                name="delivery_picked_up_requires_confirmation",
            ),
            models.CheckConstraint(
                condition=~Q(status="delivered")
                | Q(
                    delivery_confirmed=True,
                    is_confirmed=True,
                    delivered_at__isnull=False,
                ),
                name="delivery_delivered_requires_completion",
            ),
            models.CheckConstraint(
                condition=Q(is_confirmed=False)
                | Q(
                    delivery_confirmed=True,
                    status="delivered",
                    delivered_at__isnull=False,
                ),
                name="delivery_confirmed_requires_completion",
            ),
        ]


class Rating(models.Model):
    SCORE_CHOICES = [(i, str(i)) for i in range(1, 6)]

    RATER_TYPE_CHOICES = [
        ('ngo_to_donor',      'NGO rates Donor'),
        ('donor_to_volunteer','Donor rates Volunteer'),
        ('ngo_to_volunteer',  'NGO rates Volunteer'),
    ]

    rater       = models.ForeignKey(
                    CustomUser,
                    on_delete=models.CASCADE,
                    related_name='ratings_given'
                  )
    rated_user  = models.ForeignKey(
                    CustomUser,
                    on_delete=models.CASCADE,
                    related_name='ratings_received'
                  )
    delivery    = models.ForeignKey(
                    'Delivery',
                    on_delete=models.CASCADE,
                    related_name='ratings'
                  )
    rating_type = models.CharField(
                    max_length=30,
                    choices=RATER_TYPE_CHOICES
                  )
    score       = models.IntegerField(choices=SCORE_CHOICES)
    comment     = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['rater', 'delivery', 'rating_type']
        ordering        = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(score__gte=1) & Q(score__lte=5),
                name="rating_score_between_1_and_5",
            ),
            models.CheckConstraint(
                condition=~Q(rater=models.F("rated_user")),
                name="rating_cannot_target_self",
            ),
        ]

    def __str__(self):
        return (
            f'{self.rater.full_name} → '
            f'{self.rated_user.full_name}: '
            f'{self.score}/5'
        )


class Report(models.Model):
    REPORT_TYPE = [
        ('post',  'Inappropriate Food Post'),
        ('user',  'Fraudulent User'),
    ]
    REASON_CHOICES = [
        ('fake_food',    'Fake or misleading food info'),
        ('expired',      'Food is already expired'),
        ('fraud',        'Fraudulent activity'),
        ('spam',         'Spam or repeated posts'),
        ('inappropriate','Inappropriate content'),
        ('other',        'Other'),
    ]
    STATUS_CHOICES = [
        ('pending',   'Pending Review'),
        ('reviewed',  'Reviewed'),
        ('resolved',  'Resolved'),
        ('dismissed', 'Dismissed'),
    ]

    reporter = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reports_made'
    )
    report_type = models.CharField(
        max_length=10,
        choices=REPORT_TYPE
    )
    # For post reports
    reported_post = models.ForeignKey(
        FoodPost,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reports'
    )
    # For user reports
    reported_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reports_received'
    )
    reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES
    )
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    resolved_at = models.DateTimeField(
        null=True, blank=True
    )
    admin_note = models.TextField(blank=True)

    def __str__(self):
        return f"Report by {self.reporter.full_name} — {self.report_type}"

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=["reporter", "reported_post"],
                condition=Q(reported_post__isnull=False),
                name="unique_reporter_post_report",
            ),
            models.UniqueConstraint(
                fields=["reporter", "reported_user"],
                condition=Q(reported_user__isnull=False),
                name="unique_reporter_user_report",
            ),
            models.CheckConstraint(
                condition=(
                    Q(report_type="post", reported_post__isnull=False, reported_user__isnull=True)
                    | Q(report_type="user", reported_user__isnull=False, reported_post__isnull=True)
                ),
                name="report_requires_exactly_one_target",
            ),
        ]


# OOP CONCEPTS: Encapsulation(CustomUserManager, DonorProfile, VolunteerProfile, FoodPost, Delivery), Inheritance(CustomUser<-AbstractBaseUser), Polymorphism(get_dashboard_url), Abstraction(notification.py)
