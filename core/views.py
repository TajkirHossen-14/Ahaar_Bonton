from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from food.forms import FoodPostForm
from .models import (
    CustomUser,
    Delivery,
    DonorProfile,
    FoodPost,
    FoodRequest,
    VolunteerProfile,
)
from food.services.matching import FoodMatcher
from users.forms import CustomLoginForm, CustomRegistrationForm, ProfileUpdateForm
from delivery.services.notification import notify


def _require_role(request, allowed_roles):
    if request.user.role not in allowed_roles:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("dashboard")
    return None


# PUBLIC
def home_view(request):
    stats = FoodMatcher().get_stats()
    return render(request, "home.html", {"stats": stats})


def transparency_view(request):
    stats = FoodMatcher().get_stats()
    total_users = CustomUser.objects.count()
    volunteer_count = CustomUser.objects.filter(
        role=CustomUser.RoleChoices.VOLUNTEER
    ).count()
    ngo_count = CustomUser.objects.filter(role=CustomUser.RoleChoices.NGO).count()
    completed_deliveries = Delivery.objects.filter(is_confirmed=True).count()
    recent_deliveries = Delivery.objects.filter(is_confirmed=True).order_by(
        "-delivered_at"
    )[:8]

    context = {
        "stats": stats,
        "total_users": total_users,
        "volunteer_count": volunteer_count,
        "ngo_count": ngo_count,
        "completed_deliveries": completed_deliveries,
        "recent_deliveries": recent_deliveries,
    }
    return render(request, "transparency.html", context)


# AUTH
def register_view(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    if request.method == "POST":
        form = CustomRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            if user.role == CustomUser.RoleChoices.DONOR:
                DonorProfile.objects.get_or_create(user=user)
            elif user.role == CustomUser.RoleChoices.VOLUNTEER:
                VolunteerProfile.objects.get_or_create(user=user)
            login(request, user, backend="users.backends.EmailOrPhoneBackend")
            messages.success(request, "Registration successful.")
            return redirect(user.get_dashboard_url())
    else:
        form = CustomRegistrationForm()

    return render(request, "auth/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    form = CustomLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        identifier = form.cleaned_data["identifier"]
        password = form.cleaned_data["password"]
        user = authenticate(request, username=identifier, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Login successful.")
            return redirect(user.get_dashboard_url())
        messages.error(request, "Invalid email/phone or password.")

    return render(request, "auth/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect("/login/")


@login_required
def dashboard_redirect(request):
    return redirect(request.user.get_dashboard_url())


@login_required
def profile_view(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "auth/profile.html", {"form": form})


# DONOR
@login_required
def donor_dashboard(request):
    denied = _require_role(request, [CustomUser.RoleChoices.DONOR])
    if denied:
        return denied

    posts = FoodPost.objects.filter(donor=request.user).order_by("-created_at")
    pending_count = FoodRequest.objects.filter(
        food_post__donor=request.user,
        status=FoodRequest.StatusChoices.PENDING,
    ).count()

    total_posts = posts.count()
    active_posts = posts.filter(status=FoodPost.StatusChoices.AVAILABLE).count()
    delivered_posts = posts.filter(status=FoodPost.StatusChoices.DELIVERED).count()
    expired_posts = posts.filter(status=FoodPost.StatusChoices.EXPIRED).count()

    context = {
        "posts": posts,
        "total_posts": total_posts,
        "active_posts": active_posts,
        "delivered_posts": delivered_posts,
        "expired_posts": expired_posts,
        "stats": {
            "total": total_posts,
            "active": active_posts,
            "delivered": delivered_posts,
            "expired": expired_posts,
        },
        "pending_count": pending_count,
        "donor_profile": DonorProfile.objects.filter(user=request.user).first(),
    }
    return render(request, "donor/dashboard.html", context)


@login_required
def add_food_post(request):
    denied = _require_role(request, [CustomUser.RoleChoices.DONOR])
    if denied:
        return denied

    if request.method == "POST":
        form = FoodPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.donor = request.user
            post.latitude = request.POST.get("latitude") or None
            post.longitude = request.POST.get("longitude") or None
            post.save()
            messages.success(request, "Food post created.")
            return redirect("donor_dashboard")
    else:
        form = FoodPostForm()

    return render(request, "donor/add_food.html", {"form": form})


@login_required
def edit_food_post(request, pk):
    denied = _require_role(request, [CustomUser.RoleChoices.DONOR])
    if denied:
        return denied

    post = get_object_or_404(FoodPost, pk=pk, donor=request.user)
    blocked_statuses = [FoodPost.StatusChoices.CLAIMED, FoodPost.StatusChoices.DELIVERED]
    if post.status in blocked_statuses:
        messages.warning(request, "Claimed or delivered posts cannot be edited.")
        return redirect("donor_dashboard")

    if request.method == "POST":
        form = FoodPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.latitude = request.POST.get("latitude") or None
            post.longitude = request.POST.get("longitude") or None
            post.save()
            messages.success(request, "Food post updated.")
            return redirect("donor_dashboard")
    else:
        form = FoodPostForm(instance=post)

    return render(request, "donor/edit_food.html", {"form": form, "post": post})


@login_required
def delete_food_post(request, pk):
    denied = _require_role(request, [CustomUser.RoleChoices.DONOR])
    if denied:
        return denied

    post = get_object_or_404(FoodPost, pk=pk, donor=request.user)
    blocked_statuses = [FoodPost.StatusChoices.CLAIMED, FoodPost.StatusChoices.DELIVERED]
    if post.status in blocked_statuses:
        messages.warning(request, "Claimed or delivered posts cannot be deleted.")
    else:
        post.delete()
        messages.success(request, "Food post deleted.")
    return redirect("donor_dashboard")


@login_required
def donor_requests(request):
    denied = _require_role(request, [CustomUser.RoleChoices.DONOR])
    if denied:
        return denied

    all_requests = FoodRequest.objects.filter(food_post__donor=request.user).select_related(
        "ngo",
        "food_post",
    )
    pending_requests = all_requests.filter(status=FoodRequest.StatusChoices.PENDING)
    approved_requests = all_requests.filter(status=FoodRequest.StatusChoices.APPROVED)
    rejected_requests = all_requests.filter(status=FoodRequest.StatusChoices.REJECTED)
    completed_requests = all_requests.filter(status=FoodRequest.StatusChoices.COMPLETED)

    return render(
        request,
        "donor/requests.html",
        {
            "all_requests": all_requests,
            "pending_requests": pending_requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "completed_requests": completed_requests,
            "pending_count": pending_requests.count(),
        },
    )


@login_required
def handle_request(request, pk):
    denied = _require_role(request, [CustomUser.RoleChoices.DONOR])
    if denied:
        return denied

    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("donor_requests")

    food_request = get_object_or_404(
        FoodRequest,
        pk=pk,
        food_post__donor=request.user,
    )
    action = request.POST.get("action")

    if action == "approve":
        delivery = food_request.approve()
        notify(
            recipient=food_request.ngo.email,
            subject="Food Request Approved",
            message=(
                f"Your request for '{food_request.food_post.title}' was approved. "
                f"Delivery OTP: {delivery.delivery_otp}"
            ),
            method="email",
        )
        messages.success(request, "Request approved.")
    elif action == "reject":
        food_request.reject()
        notify(
            recipient=food_request.ngo.email,
            subject="Food Request Rejected",
            message=f"Your request for '{food_request.food_post.title}' was rejected.",
            method="email",
        )
        messages.warning(request, "Request rejected.")
    else:
        messages.error(request, "Unknown action.")

    return redirect("donor_requests")


# NGO
@login_required
def ngo_dashboard(request):
    denied = _require_role(request, [CustomUser.RoleChoices.NGO])
    if denied:
        return denied

    matcher = FoodMatcher()
    posts = matcher.get_priority_posts()
    expiring = matcher.get_expiring_soon(6)
    requested_post_ids = set(
        FoodRequest.objects.filter(ngo=request.user).values_list("food_post_id", flat=True)
    )
    context = {
        "posts": posts,
        "expiring": expiring,
        "expiring_count": expiring.count(),
        "requested_post_ids": requested_post_ids,
        # Backward compatibility keys
        "priority_posts": posts,
        "expiring_soon": expiring,
    }
    return render(request, "ngo/dashboard.html", context)


@login_required
def request_food(request, pk):
    denied = _require_role(request, [CustomUser.RoleChoices.NGO])
    if denied:
        return denied

    food_post = get_object_or_404(FoodPost, pk=pk)
    if food_post.is_expired():
        messages.error(request, "This food post is already expired.")
        return redirect("ngo_dashboard")

    if food_post.status != FoodPost.StatusChoices.AVAILABLE:
        messages.error(request, "This food post is not available for requests.")
        return redirect("ngo_dashboard")

    already_requested = FoodRequest.objects.filter(
        ngo=request.user,
        food_post=food_post,
    ).exists()
    if already_requested:
        messages.warning(request, "You already requested this food post.")
        return redirect("ngo_dashboard")

    if request.method == "POST":
        message = request.POST.get("message", "")
        FoodRequest.objects.create(ngo=request.user, food_post=food_post, message=message)
        notify(
            recipient=food_post.donor.email,
            subject="New Food Request Received",
            message=f"{request.user.full_name} requested your post '{food_post.title}'.",
            method="email",
        )
        messages.success(request, "Food request submitted.")
        return redirect("ngo_my_requests")

    return render(
        request,
        "ngo/request_confirm.html",
        {"post": food_post, "food_post": food_post},
    )


@login_required
def ngo_my_requests(request):
    denied = _require_role(request, [CustomUser.RoleChoices.NGO])
    if denied:
        return denied

    requests_qs = FoodRequest.objects.filter(ngo=request.user).select_related(
        "food_post",
        "food_post__donor",
    )
    return render(
        request,
        "ngo/my_requests.html",
        {"my_requests": requests_qs, "requests": requests_qs},
    )


# VOLUNTEER
@login_required
def volunteer_dashboard(request):
    denied = _require_role(request, [CustomUser.RoleChoices.VOLUNTEER])
    if denied:
        return denied

    available_deliveries = Delivery.objects.filter(
        volunteer__isnull=True,
        is_confirmed=False,
    ).select_related("food_request", "food_request__food_post", "food_request__ngo")
    my_deliveries = Delivery.objects.filter(volunteer=request.user).select_related(
        "food_request",
        "food_request__food_post",
        "food_request__ngo",
    )
    volunteer_profile, _ = VolunteerProfile.objects.get_or_create(user=request.user)

    available_count = available_deliveries.count()
    my_count = my_deliveries.count()
    return render(
        request,
        "volunteer/dashboard.html",
        {
            "available_deliveries": available_deliveries,
            "my_deliveries": my_deliveries,
            "available_count": available_count,
            "my_count": my_count,
            "volunteer_trust_score": volunteer_profile.trust_score,
        },
    )


@login_required
def accept_delivery(request, pk):
    if request.user.role != 'volunteer':
        messages.error(request, 'Access denied.')
        return redirect('/')
    if request.method != 'POST':
        return redirect('volunteer_dashboard')

    delivery = get_object_or_404(
        Delivery,
        pk=pk,
        volunteer__isnull=True,
        is_confirmed=False
    )
    delivery.volunteer = request.user
    delivery.save()

    notify(
        recipient=(
            delivery.food_request.food_post.donor.email
        ),
        subject='Volunteer assigned for your delivery',
        message=(
            f'Hello '
            f'{delivery.food_request.food_post.donor.full_name}'
            f',\n\n'
            f'{request.user.full_name} has accepted the '
            f'delivery for '
            f'"{delivery.food_request.food_post.title}".\n\n'
            f'They will pick up the food from your '
            f'location soon.\n\n'
            f'Your Pickup OTP: {delivery.pickup_otp}\n'
            f'Give this OTP to the volunteer when '
            f'they arrive for pickup.\n\n'
            f'- AhaarBonton'
        ),
        method='email'
    )

    messages.success(
        request,
        f'Delivery accepted! '
        f'Pickup from: '
        f'{delivery.food_request.food_post.location}'
    )
    return redirect('volunteer_dashboard')


@login_required
def confirm_pickup(request, pk):
    """
    Step 1 of 2.
    Volunteer enters Donor's pickup_otp to confirm
    that food has been picked up from the donor.
    """
    if request.user.role != 'volunteer':
        messages.error(request, 'Access denied.')
        return redirect('/')
    if request.method != 'POST':
        return redirect('volunteer_dashboard')

    delivery = get_object_or_404(
        Delivery,
        pk=pk,
        volunteer=request.user,
        pickup_confirmed=False
    )

    entered_otp = request.POST.get('otp', '').strip()
    if not entered_otp:
        messages.error(request, 'Please enter the OTP.')
        return redirect('volunteer_dashboard')

    success = delivery.confirm_pickup(entered_otp)

    if success:
        # Notify NGO that food is on the way
        # Also send them the delivery OTP
        notify(
            recipient=delivery.food_request.ngo.email,
            subject='Food is on the way!',
            message=(
                f'Hello '
                f'{delivery.food_request.ngo.full_name}'
                f',\n\n'
                f'{request.user.full_name} has picked up '
                f'"{delivery.food_request.food_post.title}"'
                f' and is on the way to you.\n\n'
                f'Your Delivery OTP: '
                f'{delivery.delivery_otp}\n\n'
                f'When the volunteer arrives, '
                f'give them this OTP to confirm '
                f'the delivery.\n\n'
                f'- AhaarBonton'
            ),
            method='email'
        )
        messages.success(
            request,
            'Pickup confirmed! '
            'The NGO has been notified that '
            'food is on the way.'
        )
    else:
        messages.error(
            request,
            'Incorrect Pickup OTP. '
            'Please get the correct OTP from the donor.'
        )

    return redirect('volunteer_dashboard')


@login_required
def confirm_delivery(request, pk):
    """
    Step 2 of 2.
    Volunteer enters NGO's delivery_otp to confirm
    that food has been delivered to the NGO.
    Pickup must be confirmed first.
    """
    if request.user.role != 'volunteer':
        messages.error(request, 'Access denied.')
        return redirect('/')
    if request.method != 'POST':
        return redirect('volunteer_dashboard')

    delivery = get_object_or_404(
        Delivery,
        pk=pk,
        volunteer=request.user,
        delivery_confirmed=False
    )

    entered_otp = request.POST.get('otp', '').strip()
    if not entered_otp:
        messages.error(request, 'Please enter the OTP.')
        return redirect('volunteer_dashboard')

    result = delivery.confirm_delivery(entered_otp)
    volunteer_profile, _ = VolunteerProfile.objects.get_or_create(user=request.user)

    if result == 'pickup_first':
        volunteer_profile.decrease_score()
        messages.error(
            request,
            'You must confirm pickup first '
            'before confirming delivery.'
        )

    elif result == 'success':
        volunteer_profile.increase_score()
        # Update donor trust score
        try:
            profile = DonorProfile.objects.get(
                user=delivery.food_request.food_post.donor
            )
            profile.increase_score()
        except DonorProfile.DoesNotExist:
            pass

        # Notify donor
        notify(
            recipient=(
                delivery.food_request.food_post.donor.email
            ),
            subject='Delivery completed!',
            message=(
                f'Hello '
                f'{delivery.food_request.food_post.donor.full_name}'
                f',\n\n'
                f'"{delivery.food_request.food_post.title}"'
                f' has been successfully delivered to '
                f'{delivery.food_request.ngo.full_name}.'
                f'\n\nYour trust score has been '
                f'increased by 5 points. Thank you!\n\n'
                f'- AhaarBonton'
            ),
            method='email'
        )

        messages.success(
            request,
            'Delivery fully confirmed! '
            'Food has reached the NGO.'
        )

    else:
        volunteer_profile.decrease_score()
        messages.error(
            request,
            'Incorrect Delivery OTP. '
            'Please get the correct OTP from the NGO.'
        )

    return redirect('volunteer_dashboard')


# ADMIN
@login_required
def admin_dashboard(request):
    denied = _require_role(request, [CustomUser.RoleChoices.ADMIN])
    if denied:
        return denied

    matcher = FoodMatcher()
    stats = matcher.get_stats()

    total_users = CustomUser.objects.count()
    donor_count = CustomUser.objects.filter(role=CustomUser.RoleChoices.DONOR).count()
    ngo_count = CustomUser.objects.filter(role=CustomUser.RoleChoices.NGO).count()
    volunteer_count = CustomUser.objects.filter(
        role=CustomUser.RoleChoices.VOLUNTEER
    ).count()
    admin_count = CustomUser.objects.filter(role=CustomUser.RoleChoices.ADMIN).count()

    def _percentage(value):
        return round((value / total_users) * 100, 2) if total_users else 0

    user_counts = {
        "total": total_users,
        "donor": {"count": donor_count, "percentage": _percentage(donor_count)},
        "ngo": {"count": ngo_count, "percentage": _percentage(ngo_count)},
        "volunteer": {
            "count": volunteer_count,
            "percentage": _percentage(volunteer_count),
        },
        "admin": {"count": admin_count, "percentage": _percentage(admin_count)},
    }

    recent_posts = FoodPost.objects.select_related("donor").order_by("-created_at")[:10]
    expiring_posts = FoodPost.objects.filter(
        status=FoodPost.StatusChoices.AVAILABLE,
        expiry_time__lte=timezone.now() + timedelta(hours=6),
    ).order_by("expiry_time")
    recent_requests = FoodRequest.objects.select_related("ngo", "food_post").order_by(
        "-requested_at"
    )[:8]
    delivery_stats = {
        "total": Delivery.objects.count(),
        "pending": Delivery.objects.filter(status=Delivery.StatusChoices.PENDING).count(),
        "picked_up": Delivery.objects.filter(
            status=Delivery.StatusChoices.PICKED_UP
        ).count(),
        "delivered": Delivery.objects.filter(
            status=Delivery.StatusChoices.DELIVERED
        ).count(),
        "confirmed": Delivery.objects.filter(is_confirmed=True).count(),
    }

    context = {
        "stats": stats,
        "user_counts": user_counts,
        "recent_posts": recent_posts,
        "expiring_posts": expiring_posts,
        "recent_requests": recent_requests,
        "delivery_stats": delivery_stats,
        # Phase 9 explicit context
        "total_users": total_users,
        "donor_count": donor_count,
        "ngo_count": ngo_count,
        "volunteer_count": volunteer_count,
        "donor_percent": user_counts["donor"]["percentage"],
        "ngo_percent": user_counts["ngo"]["percentage"],
        "volunteer_percent": user_counts["volunteer"]["percentage"],
        "completed_deliveries": delivery_stats["confirmed"],
        "total_deliveries": delivery_stats["total"],
    }
    return render(request, "admin_panel/dashboard.html", context)


@login_required
def admin_expire_food(request):
    denied = _require_role(request, [CustomUser.RoleChoices.ADMIN])
    if denied:
        return denied

    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("admin_dashboard")

    expired_count = FoodMatcher().auto_expire_old_posts()
    messages.info(request, f"{expired_count} posts marked as expired.")
    return redirect("admin_dashboard")


# ERROR PAGES
def custom_404(request, exception):
    return render(request, "404.html", status=404)


def custom_403(request, exception):
    return render(request, "403.html", status=403)
