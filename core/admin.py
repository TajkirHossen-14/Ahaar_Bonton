from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    CustomUser,
    Delivery,
    DonorProfile,
    FoodPost,
    FoodRequest,
    Rating,
    VolunteerProfile,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "full_name", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("email", "full_name", "phone_number")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("full_name", "phone_number", "role", "profile_pic")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "phone_number",
                    "role",
                    "profile_pic",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

    filter_horizontal = ("groups", "user_permissions")


@admin.register(DonorProfile)
class DonorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "trust_score", "score_label")

    @admin.display(description="Score Label")
    def score_label(self, obj):
        return obj.get_score_label()


@admin.register(VolunteerProfile)
class VolunteerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "trust_score", "score_label")

    @admin.display(description="Score Label")
    def score_label(self, obj):
        return obj.get_score_label()


@admin.register(FoodPost)
class FoodPostAdmin(admin.ModelAdmin):
    list_display = ("title", "donor", "category", "status", "expiry_time", "created_at")
    list_filter = ("status", "category")


@admin.register(FoodRequest)
class FoodRequestAdmin(admin.ModelAdmin):
    list_display = ("ngo", "food_post", "status", "requested_at")


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "food_request",
        "volunteer",
        "pickup_otp",
        "delivery_otp",
        "status",
        "is_confirmed",
    )
    readonly_fields = (
        "pickup_otp",
        "delivery_otp",
        "created_at",
        "picked_up_at",
        "delivered_at",
    )


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("rater", "rated_user", "score")
