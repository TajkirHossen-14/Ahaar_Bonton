import calendar
import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Avg, Case, Count, IntegerField, Q, When
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from food.forms import FoodPostForm
from .models import (
    CustomUser,
    Delivery,
    DonorProfile,
    FoodPost,
    FoodRequest,
    Report,
    Rating,
    VolunteerProfile,
)
from food.services.matching import FoodMatcher
from users.forms import CustomLoginForm, CustomRegistrationForm, ProfileUpdateForm
from delivery.services.notification import notify
from .forms import ReportForm


OTP_MAX_ATTEMPTS = 5
OTP_LOCK_SECONDS = 300


def _require_role(request, allowed_roles):
    if request.user.role not in allowed_roles:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("dashboard")
    return None


def _safe_next_url(request, fallback):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback


def _otp_cache_key(request, delivery, stage):
    return f"otp-attempts:{request.user.pk}:{stage}:{delivery.pk}"


def _otp_state(request, delivery, stage):
    key = _otp_cache_key(request, delivery, stage)
    state = cache.get(key, {"count": 0, "locked_until": 0})
    return state.get("locked_until", 0) > timezone.now().timestamp(), state, key


def _record_failed_otp(request, delivery, stage):
    locked, state, key = _otp_state(request, delivery, stage)
    if locked:
        return
    state["count"] = state.get("count", 0) + 1
    if state["count"] >= OTP_MAX_ATTEMPTS:
        state = {
            "count": 0,
            "locked_until": timezone.now().timestamp() + OTP_LOCK_SECONDS,
        }
    cache.set(key, state, timeout=OTP_LOCK_SECONDS)


def _clear_otp_attempts(request, delivery, stage):
    cache.delete(_otp_cache_key(request, delivery, stage))


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
    recent_deliveries = (
        Delivery.objects.filter(is_confirmed=True)
        .select_related("food_request__ngo", "food_request__food_post__donor", "volunteer")
        .order_by("-delivered_at")[:8]
    )

    category_counts_qs = FoodPost.objects.values("category").annotate(total=Count("id"))
    category_count_map = {row["category"]: row["total"] for row in category_counts_qs}
    category_order = [
        (FoodPost.CategoryChoices.COOKED, "Cooked"),
        (FoodPost.CategoryChoices.RAW, "Raw"),
        (FoodPost.CategoryChoices.PACKAGED, "Packaged"),
        (FoodPost.CategoryChoices.BAKERY, "Bakery"),
    ]
    category_chart_labels = [label for _, label in category_order]
    category_chart_values = [category_count_map.get(code, 0) for code, _ in category_order]

    status_order = [
        (FoodPost.StatusChoices.AVAILABLE, "Available"),
        (FoodPost.StatusChoices.CLAIMED, "Claimed"),
        (FoodPost.StatusChoices.DELIVERED, "Delivered"),
        (FoodPost.StatusChoices.EXPIRED, "Expired"),
    ]
    status_chart_labels = [label for _, label in status_order]
    status_chart_values = [
        stats["available"],
        stats["claimed"],
        stats["delivered"],
        stats["expired"],
    ]

    monthly_deliveries_qs = (
        Delivery.objects.filter(is_confirmed=True, delivered_at__isnull=False)
        .annotate(month=TruncMonth("delivered_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    monthly_deliveries_map = {}
    for row in monthly_deliveries_qs:
        month = row.get("month")
        if month:
            monthly_deliveries_map[(month.year, month.month)] = row["total"]

    now_local = timezone.localtime()
    month_points = []
    for offset in range(11, -1, -1):
        year = now_local.year
        month = now_local.month - offset
        while month <= 0:
            month += 12
            year -= 1
        month_points.append((year, month))

    monthly_chart_labels = [f"{calendar.month_abbr[m]} {str(y)[-2:]}" for y, m in month_points]
    monthly_chart_values = [monthly_deliveries_map.get((y, m), 0) for y, m in month_points]

    context = {
        "stats": stats,
        "total_users": total_users,
        "volunteer_count": volunteer_count,
        "ngo_count": ngo_count,
        "completed_deliveries": completed_deliveries,
        "recent_deliveries": recent_deliveries,
        "category_chart_labels": category_chart_labels,
        "category_chart_values": category_chart_values,
        "status_chart_labels": status_chart_labels,
        "status_chart_values": status_chart_values,
        "monthly_chart_labels": monthly_chart_labels,
        "monthly_chart_values": monthly_chart_values,
    }
    return render(request, "transparency.html", context)


# AUTH
def register_view(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    if request.method == "POST":
        form = CustomRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    if user.role == CustomUser.RoleChoices.DONOR:
                        DonorProfile.objects.get_or_create(user=user)
                    elif user.role == CustomUser.RoleChoices.VOLUNTEER:
                        VolunteerProfile.objects.get_or_create(user=user)
            except IntegrityError:
                messages.error(request, "An account with these details already exists.")
            else:
                login(request, user, backend="users.backends.EmailOrPhoneBackend")
                messages.success(request, "Your account is ready. Welcome to AhaarBonton.")
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
            messages.success(request, "Welcome back. You are now signed in.")
            return redirect(_safe_next_url(request, user.get_dashboard_url()))
        messages.error(request, "Invalid email/phone or password.")

    return render(request, "auth/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("login")


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
    active_posts = posts.filter(
        status=FoodPost.StatusChoices.AVAILABLE,
        expiry_time__gt=timezone.now(),
    ).count()
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
            form.save()
            messages.success(request, "Food post updated.")
            return redirect("donor_dashboard")
    else:
        form = FoodPostForm(instance=post)

    return render(request, "donor/edit_food.html", {"form": form, "post": post})


@login_required
@require_POST
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

    donor_rated_delivery_ids = set(
        Rating.objects.filter(
            rater=request.user,
            rating_type=Rating.RATER_TYPE_CHOICES[1][0],
        ).values_list("delivery_id", flat=True)
    )
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
            "donor_rated_delivery_ids": donor_rated_delivery_ids,
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

    try:
        if action == "approve":
            delivery = food_request.approve()
        elif action == "reject":
            food_request.reject()
            delivery = None
        else:
            messages.error(request, "Unknown action.")
            return redirect("donor_requests")
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("donor_requests")

    if action == "approve":
        notify(
            recipient=food_request.ngo.email,
            subject="Food Request Approved",
            message=(
                f"Your request for '{food_request.food_post.title}' was approved. "
                f"Delivery OTP: {delivery.delivery_otp}"
            ),
            method="email",
        )
        messages.success(request, "Request approved. A delivery is now open for volunteers.")
    else:
        notify(
            recipient=food_request.ngo.email,
            subject="Food Request Rejected",
            message=f"Your request for '{food_request.food_post.title}' was rejected.",
            method="email",
        )
        messages.warning(request, "Request rejected.")

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
        FoodRequest.objects.filter(ngo=request.user)
        .exclude(status=FoodRequest.StatusChoices.REJECTED)
        .values_list("food_post_id", flat=True)
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

    existing_request = FoodRequest.objects.filter(
        ngo=request.user,
        food_post=food_post,
    ).first()
    if existing_request and existing_request.status != FoodRequest.StatusChoices.REJECTED:
        messages.warning(request, "You already have an active request for this food post.")
        return redirect("ngo_dashboard")

    if request.method == "POST":
        message = request.POST.get("message", "").strip()[:1000]
        try:
            with transaction.atomic():
                locked_post = FoodPost.objects.select_for_update().get(pk=food_post.pk)
                if locked_post.is_expired() or locked_post.status != FoodPost.StatusChoices.AVAILABLE:
                    raise ValueError("This food post is no longer available.")
                if existing_request:
                    existing_request.status = FoodRequest.StatusChoices.PENDING
                    existing_request.message = message
                    existing_request.requested_at = timezone.now()
                    existing_request.save(
                        update_fields=["status", "message", "requested_at"]
                    )
                else:
                    FoodRequest.objects.create(
                        ngo=request.user,
                        food_post=locked_post,
                        message=message,
                    )
        except (ValueError, IntegrityError) as exc:
            messages.error(
                request,
                str(exc) if isinstance(exc, ValueError) else "This request already exists.",
            )
            return redirect("ngo_dashboard")

        notify(
            recipient=food_post.donor.email,
            subject="New Food Request Received",
            message=f"{request.user.full_name} requested your post '{food_post.title}'.",
            method="email",
        )
        messages.success(request, "Food request submitted. You can track it in My Requests.")
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

    requests_qs = (
        FoodRequest.objects.filter(ngo=request.user)
        .select_related(
            "food_post",
            "food_post__donor",
        )
        .annotate(
            status_priority=Case(
                When(status=FoodRequest.StatusChoices.PENDING, then=0),
                default=1,
                output_field=IntegerField(),
            )
        )
        .order_by("status_priority", "-requested_at")
    )
    ngo_ratings = Rating.objects.filter(
        rater=request.user,
        rating_type__in=["ngo_to_donor", "ngo_to_volunteer"],
    ).values_list("rating_type", "delivery_id")
    ngo_donor_rated_delivery_ids = {
        delivery_id for rating_type, delivery_id in ngo_ratings if rating_type == "ngo_to_donor"
    }
    ngo_volunteer_rated_delivery_ids = {
        delivery_id for rating_type, delivery_id in ngo_ratings if rating_type == "ngo_to_volunteer"
    }
    return render(
        request,
        "ngo/my_requests.html",
        {
            "my_requests": requests_qs,
            "requests": requests_qs,
            "ngo_donor_rated_delivery_ids": ngo_donor_rated_delivery_ids,
            "ngo_volunteer_rated_delivery_ids": ngo_volunteer_rated_delivery_ids,
        },
    )


# VOLUNTEER
@login_required
def volunteer_dashboard(request):
    denied = _require_role(request, [CustomUser.RoleChoices.VOLUNTEER])
    if denied:
        return denied

    available_deliveries = (
        Delivery.objects.filter(
            volunteer__isnull=True,
            is_confirmed=False,
            status=Delivery.StatusChoices.PENDING,
            food_request__status=FoodRequest.StatusChoices.APPROVED,
            food_request__food_post__status=FoodPost.StatusChoices.CLAIMED,
            food_request__food_post__expiry_time__gt=timezone.now(),
        )
        .select_related(
            "food_request",
            "food_request__food_post",
            "food_request__food_post__donor",
            "food_request__ngo",
        )
        .order_by("food_request__food_post__expiry_time")
    )
    my_deliveries = Delivery.objects.filter(volunteer=request.user).select_related(
        "food_request",
        "food_request__food_post",
        "food_request__food_post__donor",
        "food_request__ngo",
    )
    volunteer_profile, _ = VolunteerProfile.objects.get_or_create(user=request.user)

    available_count = available_deliveries.count()
    my_count = my_deliveries.count()
    completed_count = my_deliveries.filter(is_confirmed=True).count()
    active_count = my_deliveries.filter(is_confirmed=False).count()
    return render(
        request,
        "volunteer/dashboard.html",
        {
            "available_deliveries": available_deliveries,
            "my_deliveries": my_deliveries,
            "available_count": available_count,
            "my_count": my_count,
            "completed_count": completed_count,
            "active_count": active_count,
            "volunteer_trust_score": volunteer_profile.trust_score,
            "volunteer_profile": volunteer_profile,
        },
    )


@login_required
@require_POST
def accept_delivery(request, pk):
    if request.user.role != 'volunteer':
        messages.error(request, 'Access denied.')
        return redirect('/')
    try:
        with transaction.atomic():
            delivery = (
                Delivery.objects.select_for_update()
                .select_related("food_request__food_post")
                .get(
                    pk=pk,
                    volunteer__isnull=True,
                    is_confirmed=False,
                    status=Delivery.StatusChoices.PENDING,
                )
            )
            food_post = delivery.food_request.food_post
            if (
                delivery.food_request.status != FoodRequest.StatusChoices.APPROVED
                or food_post.status != FoodPost.StatusChoices.CLAIMED
                or food_post.is_expired()
            ):
                raise ValueError("This delivery is no longer available.")
            delivery.volunteer = request.user
            delivery.save(update_fields=["volunteer"])
    except (Delivery.DoesNotExist, ValueError):
        messages.error(request, "This delivery is no longer available or was already accepted.")
        return redirect("volunteer_dashboard")

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
@require_POST
def confirm_pickup(request, pk):
    """
    Step 1 of 2.
    Volunteer enters Donor's pickup_otp to confirm
    that food has been picked up from the donor.
    """
    if request.user.role != 'volunteer':
        messages.error(request, 'Access denied.')
        return redirect('/')
    delivery = get_object_or_404(
        Delivery,
        pk=pk,
        volunteer=request.user,
    )

    entered_otp = request.POST.get('otp', '').strip()
    if not entered_otp:
        messages.error(request, 'Please enter the 6-digit OTP.')
        return redirect('volunteer_dashboard')

    locked, _, _ = _otp_state(request, delivery, 'pickup')
    if locked:
        messages.error(request, 'Too many incorrect attempts. Try again in 5 minutes.')
        return redirect('volunteer_dashboard')

    result = delivery.confirm_pickup(entered_otp)

    if result == 'success':
        _clear_otp_attempts(request, delivery, 'pickup')
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
    elif result == 'already_confirmed':
        messages.info(request, 'Pickup was already confirmed.')
    elif result == 'expired':
        messages.error(request, 'This food post has expired and cannot be picked up.')
    elif result == 'not_assigned':
        messages.error(request, 'This delivery is not assigned to you.')
    elif result == 'not_available':
        messages.error(request, 'This delivery is no longer active.')
    else:
        _record_failed_otp(request, delivery, 'pickup')
        messages.error(
            request,
            'Incorrect Pickup OTP. Please get the correct OTP from the donor.'
        )

    return redirect('volunteer_dashboard')


@login_required
@require_POST
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
    delivery = get_object_or_404(
        Delivery,
        pk=pk,
        volunteer=request.user,
    )

    entered_otp = request.POST.get('otp', '').strip()
    if not entered_otp:
        messages.error(request, 'Please enter the 6-digit OTP.')
        return redirect('volunteer_dashboard')

    locked, _, _ = _otp_state(request, delivery, 'delivery')
    if locked:
        messages.error(request, 'Too many incorrect attempts. Try again in 5 minutes.')
        return redirect('volunteer_dashboard')

    result = delivery.confirm_delivery(entered_otp)

    if result == 'pickup_first':
        messages.error(
            request,
            'You must confirm pickup first before confirming delivery.'
        )

    elif result == 'success':
        _clear_otp_attempts(request, delivery, 'delivery')
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

    elif result == 'already_confirmed':
        messages.info(request, 'This delivery was already completed.')
    elif result == 'expired':
        messages.error(request, 'This food post has expired and cannot be delivered.')
    elif result == 'not_assigned':
        messages.error(request, 'This delivery is not assigned to you.')
    elif result == 'not_available':
        messages.error(request, 'This delivery is no longer active.')
    else:
        _record_failed_otp(request, delivery, 'delivery')
        messages.error(
            request,
            'Incorrect Delivery OTP. Please get the correct OTP from the NGO.'
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
        expiry_time__gt=timezone.now(),
        expiry_time__lte=timezone.now() + timedelta(hours=6),
    ).order_by("expiry_time")
    recent_requests = FoodRequest.objects.select_related("ngo", "food_post").order_by(
        "-requested_at"
    )[:8]
    recent_reports = Report.objects.filter(status="pending").select_related(
        "reporter", "reported_post", "reported_user"
    )[:8]
    pending_report_count = Report.objects.filter(status="pending").count()
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
        "recent_reports": recent_reports,
        "pending_report_count": pending_report_count,
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
@require_POST
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


@login_required
def report_post(request, post_pk):
    post = get_object_or_404(FoodPost, pk=post_pk)
    if post.donor_id == request.user.pk:
        messages.error(request, "You cannot report your own food post.")
        return redirect(request.user.get_dashboard_url())

    form = ReportForm(request.POST or None, report_type="post")
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                Report.objects.create(
                    reporter=request.user,
                    report_type="post",
                    reported_post=post,
                    reason=form.cleaned_data["reason"],
                    description=form.cleaned_data["description"],
                )
        except IntegrityError:
            messages.warning(request, "You have already reported this post.")
        else:
            messages.success(request, "Report submitted. Our team will review it.")
        return redirect(request.user.get_dashboard_url())

    return render(
        request,
        "reports/report_post.html",
        {"post": post, "form": form},
    )


@login_required
def report_user(request, user_pk):
    reported = get_object_or_404(CustomUser, pk=user_pk)
    if reported.pk == request.user.pk:
        messages.error(request, "You cannot report your own account.")
        return redirect("user_profile", user_pk=reported.pk)

    form = ReportForm(request.POST or None, report_type="user")
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                Report.objects.create(
                    reporter=request.user,
                    report_type="user",
                    reported_user=reported,
                    reason=form.cleaned_data["reason"],
                    description=form.cleaned_data["description"],
                )
        except IntegrityError:
            messages.warning(request, "You have already reported this user.")
        else:
            messages.success(request, "Report submitted. Our team will review it.")
        return redirect("user_profile", user_pk=reported.pk)

    return render(
        request,
        "reports/report_user.html",
        {"reported_user": reported, "form": form},
    )


@login_required
@require_POST
def submit_rating(request, delivery_pk):
    """
    Handles rating submission after delivery complete.
    Three types:
    - NGO rates Donor
    - Donor rates Volunteer
    - NGO rates Volunteer
    """
    delivery = get_object_or_404(
        Delivery, pk=delivery_pk,
        is_confirmed=True
    )

    rating_type = request.POST.get('rating_type')
    score = request.POST.get('score')
    comment = request.POST.get('comment', '')

    participant_checks = {
        "ngo_to_donor": request.user.pk == delivery.food_request.ngo_id,
        "donor_to_volunteer": request.user.pk == delivery.food_request.food_post.donor_id,
        "ngo_to_volunteer": request.user.pk == delivery.food_request.ngo_id,
    }
    if not participant_checks.get(rating_type, False):
        messages.error(request, "You are not allowed to submit this rating.")
        return redirect(request.user.get_dashboard_url())

    # Determine who is being rated
    rated_user = None
    if rating_type == 'ngo_to_donor':
        rated_user = delivery.food_request.food_post.donor
    elif rating_type == 'donor_to_volunteer':
        rated_user = delivery.volunteer
    elif rating_type == 'ngo_to_volunteer':
        rated_user = delivery.volunteer

    if not rated_user:
        messages.error(request, 'Could not find user to rate.')
        return redirect('/')

    # Validate score
    try:
        score = int(score)
        if score not in range(1, 6):
            raise ValueError
    except (ValueError, TypeError):
        messages.error(
            request, 'Invalid score. Choose between 1-5.'
        )
        return redirect('/')

    comment = comment.strip()[:1000]
    try:
        with transaction.atomic():
            _, created = Rating.objects.get_or_create(
                rater=request.user,
                rated_user=rated_user,
                delivery=delivery,
                rating_type=rating_type,
                defaults={"score": score, "comment": comment},
            )
    except IntegrityError:
        created = False

    if created:
        messages.success(request, "Thank you. Your rating has been submitted.")
    else:
        messages.warning(request, "You have already submitted this rating.")
    return redirect(request.user.get_dashboard_url())


def user_profile(request, user_pk):
    """
    Public profile page showing ratings and reviews.
    """
    profile_user = get_object_or_404(CustomUser, pk=user_pk)
    ratings = Rating.objects.filter(
        rated_user=profile_user
    ).select_related('rater').order_by('-created_at')
    avg_rating = profile_user.get_average_rating()
    rating_count = profile_user.get_rating_count()
    rating_label = profile_user.get_rating_label()

    # Score breakdown (1-5 count)
    score_breakdown = {}
    for i in range(5, 0, -1):
        score_breakdown[i] = ratings.filter(
            score=i).count()

    trust_score = None
    if profile_user.role == CustomUser.RoleChoices.DONOR:
        trust_score = getattr(profile_user, "donor_profile", None)
    elif profile_user.role == CustomUser.RoleChoices.VOLUNTEER:
        trust_score = getattr(profile_user, "volunteer_profile", None)

    context = {
        'profile_user': profile_user,
        'ratings': ratings,
        'avg_rating': avg_rating,
        'rating_count': rating_count,
        'rating_label': rating_label,
        'score_breakdown': score_breakdown,
        'trust_profile': trust_score,
    }
    return render(
        request, 'profiles/user_profile.html', context
    )


def leaderboard_view(request):
    activity_donors = (
        CustomUser.objects.filter(role=CustomUser.RoleChoices.DONOR)
        .annotate(
            delivered_count=Count(
                "food_posts",
                filter=Q(food_posts__status=FoodPost.StatusChoices.DELIVERED),
            )
        )
        .filter(delivered_count__gt=0)
        .order_by("-delivered_count", "full_name")[:10]
    )
    activity_volunteers = (
        CustomUser.objects.filter(role=CustomUser.RoleChoices.VOLUNTEER)
        .annotate(
            delivery_count=Count(
                "deliveries",
                filter=Q(deliveries__is_confirmed=True),
            )
        )
        .filter(delivery_count__gt=0)
        .order_by("-delivery_count", "full_name")[:10]
    )
    rating_donors = (
        CustomUser.objects.filter(role=CustomUser.RoleChoices.DONOR)
        .annotate(
            avg_score=Avg("ratings_received__score"),
            rating_count=Count("ratings_received"),
        )
        .filter(rating_count__gt=0)
        .order_by("-avg_score", "-rating_count", "full_name")[:10]
    )
    rating_volunteers = (
        CustomUser.objects.filter(role=CustomUser.RoleChoices.VOLUNTEER)
        .annotate(
            avg_score=Avg("ratings_received__score"),
            rating_count=Count("ratings_received"),
        )
        .filter(rating_count__gt=0)
        .order_by("-avg_score", "-rating_count", "full_name")[:10]
    )
    trust_donors = (
        CustomUser.objects.filter(
            role=CustomUser.RoleChoices.DONOR,
            donor_profile__isnull=False,
        )
        .select_related("donor_profile")
        .order_by("-donor_profile__trust_score", "full_name")[:10]
    )
    trust_volunteers = (
        CustomUser.objects.filter(
            role=CustomUser.RoleChoices.VOLUNTEER,
            volunteer_profile__isnull=False,
        )
        .select_related("volunteer_profile")
        .order_by("-volunteer_profile__trust_score", "full_name")[:10]
    )

    return render(request, "leaderboard.html", {
        "activity_donors": activity_donors,
        "activity_volunteers": activity_volunteers,
        "rating_donors": rating_donors,
        "rating_volunteers": rating_volunteers,
        "trust_donors": trust_donors,
        "trust_volunteers": trust_volunteers,
    })


def food_map_view(request):
    posts = (
        FoodPost.objects.filter(
            status=FoodPost.StatusChoices.AVAILABLE,
            expiry_time__gt=timezone.now(),
        )
        .exclude(latitude=None)
        .exclude(longitude=None)
        .select_related("donor")
        .order_by("expiry_time")
    )

    posts_data = []
    for post in posts:
        posts_data.append(
            {
                "id": post.pk,
                "title": post.title,
                "quantity": post.quantity,
                "category": post.get_category_display(),
                "location": post.location,
                "lat": round(float(post.latitude), 6 if request.user.is_authenticated else 3),
                "lng": round(float(post.longitude), 6 if request.user.is_authenticated else 3),
                "expiry": post.expiry_time.isoformat(),
                "donor": post.donor.full_name,
                "request_url": (
                    reverse("request_food", kwargs={"pk": post.pk})
                    if getattr(request.user, "role", None) == CustomUser.RoleChoices.NGO
                    else None
                ),
            }
        )

    return render(
        request,
        "food_map.html",
        {
            "posts": posts,
            "posts_data": posts_data,
            "posts_json": json.dumps(posts_data),
            "total": posts.count(),
            "can_request": getattr(request.user, "role", None) == CustomUser.RoleChoices.NGO,
        },
    )


def heatmap_view(request):
    import json

    # All food posts with coordinates
    posts = FoodPost.objects.exclude(
        latitude=None
    ).exclude(
        longitude=None
    )

    # Aggregate approximate coordinates so public heatmaps do not reveal exact addresses.
    heat_data = []
    for post in posts:
        intensity = 0.5
        if post.status == FoodPost.StatusChoices.DELIVERED:
            intensity = 1.0
        elif post.status == FoodPost.StatusChoices.AVAILABLE and not post.is_expired():
            intensity = 0.7
        heat_data.append([
            round(float(post.latitude), 3),
            round(float(post.longitude), 3),
            intensity,
        ])

    # Stats by status
    stats = {
        'total':     posts.count(),
        'available': posts.filter(
            status='available').count(),
        'delivered': posts.filter(
            status='delivered').count(),
        'expired':   posts.filter(
            status='expired').count(),
    }

    return render(request, 'heatmap.html', {
        'heat_data': heat_data,
        'stats':     stats,
    })


def offline_view(request):
    return render(request, 'offline.html')

