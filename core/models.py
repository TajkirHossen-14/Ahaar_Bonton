import random
from datetime import timedelta

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


def generate_otp():
    return str(random.randint(100000, 999999))


class CustomUserManager(BaseUserManager):
    # OOP: Encapsulation - create_user and create_superuser logic is encapsulated in manager methods.
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email must be provided.")
        if not password:
            raise ValueError("Password must be provided.")

        email = self.normalize_email(email)
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


class DonorProfile(models.Model):
    # OOP: Encapsulation - donor score behavior and validation rules are encapsulated in methods.
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="donor_profile",
    )
    trust_score = models.IntegerField(default=0)

    def __str__(self):
        return f"DonorProfile<{self.user.email}>"

    def update_trust_score(self, delta):
        self.trust_score = max(0, self.trust_score + delta)
        self.save(update_fields=["trust_score"])

    def increase_score(self):
        self.update_trust_score(+5)

    def decrease_score(self):
        self.update_trust_score(-2)

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
    trust_score = models.IntegerField(default=0)

    def __str__(self):
        return f"VolunteerProfile<{self.user.email}>"

    def update_trust_score(self, delta):
        self.trust_score = max(0, self.trust_score + delta)
        self.save(update_fields=["trust_score"])

    def increase_score(self):
        self.update_trust_score(+5)

    def decrease_score(self):
        self.update_trust_score(-2)

    def get_score_label(self):
        if self.trust_score >= 85:
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
    quantity = models.PositiveIntegerField()
    category = models.CharField(max_length=20, choices=CategoryChoices.choices)
    image = models.ImageField(upload_to="food_posts/")
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
        self.status = 'approved'
        self.food_post.mark_claimed()
        self.save()
        delivery, created = Delivery.objects.get_or_create(
            food_request=self,
            defaults={
                'pickup_otp':   generate_otp(),
                'delivery_otp': generate_otp(),
            }
        )
        return delivery

    def reject(self):
        self.status = self.StatusChoices.REJECTED
        self.save(update_fields=["status"])


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
        if self.pickup_otp == entered_otp:
            self.pickup_confirmed = True
            self.status           = 'picked_up'
            self.picked_up_at     = timezone.now()
            self.save()
            return True
        return False

    # OOP: Encapsulation — delivery logic inside class
    def confirm_delivery(self, entered_otp):
        if not self.pickup_confirmed:
            return 'pickup_first'
        if self.delivery_otp == entered_otp:
            self.delivery_confirmed          = True
            self.is_confirmed                = True
            self.status                      = 'delivered'
            self.delivered_at                = timezone.now()
            self.food_request.status         = 'completed'
            self.food_request.food_post.mark_delivered()
            self.food_request.save()
            self.save()
            return 'success'
        return 'wrong_otp'

    def mark_picked_up(self):
        self.status       = 'picked_up'
        self.picked_up_at = timezone.now()
        self.save()

    @property
    def otp(self):
        # Backward compatibility: legacy views/templates may still reference `delivery.otp`.
        return self.delivery_otp

    def __str__(self):
        return (f'Delivery — '
                f'{self.food_request.food_post.title} '
                f'| Pickup OTP: {self.pickup_otp}')

    class Meta:
        ordering = ['-created_at']


class Rating(models.Model):
    rater = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="ratings_given",
    )
    rated_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="ratings_received",
    )
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating<{self.score}/5>"


# OOP CONCEPTS: Encapsulation(CustomUserManager, DonorProfile, VolunteerProfile, FoodPost, Delivery), Inheritance(CustomUser<-AbstractBaseUser), Polymorphism(get_dashboard_url), Abstraction(notification.py)
