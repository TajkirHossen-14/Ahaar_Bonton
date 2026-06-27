import calendar
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Case, Count, IntegerField, When
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

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

    status_counts_qs = FoodPost.objects.values("status").annotate(total=Count("id"))
    status_count_map = {row["status"]: row["total"] for row in status_counts_qs}
    status_order = [
        (FoodPost.StatusChoices.AVAILABLE, "Available"),
        (FoodPost.StatusChoices.CLAIMED, "Claimed"),
        (FoodPost.StatusChoices.DELIVERED, "Delivered"),
        (FoodPost.StatusChoices.EXPIRED, "Expired"),
    ]
    status_chart_labels = [label for _, label in status_order]
    status_chart_values = [status_count_map.get(code, 0) for code, _ in status_order]

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


@login_required
def report_post(request, post_pk):
    post = get_object_or_404(FoodPost, pk=post_pk)
    if request.method == 'POST':
        reason = request.POST.get('reason')
        description = request.POST.get('description', '')

        # Already reported check
        already = Report.objects.filter(
            reporter=request.user,
            reported_post=post
        ).exists()

        if already:
            messages.warning(
                request,
                'You have already reported this post.'
            )
            return redirect('ngo_dashboard')

        Report.objects.create(
            reporter=request.user,
            report_type='post',
            reported_post=post,
            reason=reason,
            description=description
        )
        messages.success(
            request,
            'Report submitted. Our team will review it.'
        )
        return redirect('ngo_dashboard')

    return render(
        request, 'reports/report_post.html',
        {'post': post}
    )


@login_required
def report_user(request, user_pk):
    reported = get_object_or_404(
        CustomUser, pk=user_pk
    )
    if request.method == 'POST':
        reason = request.POST.get('reason')
        description = request.POST.get('description', '')

        already = Report.objects.filter(
            reporter=request.user,
            reported_user=reported
        ).exists()

        if already:
            messages.warning(
                request,
                'You have already reported this user.'
            )
            return redirect('/')

        Report.objects.create(
            reporter=request.user,
            report_type='user',
            reported_user=reported,
            reason=reason,
            description=description
        )
        messages.success(
            request,
            'Report submitted. Our team will review it.'
        )
        return redirect('/')

    return render(
        request, 'reports/report_user.html',
        {'reported_user': reported}
    )


@login_required
def submit_rating(request, delivery_pk):
    """
    Handles rating submission after delivery complete.
    Three types:
    - NGO rates Donor
    - Donor rates Volunteer
    - NGO rates Volunteer
    """
    if request.method != 'POST':
        return redirect('/')

    delivery = get_object_or_404(
        Delivery, pk=delivery_pk,
        is_confirmed=True
    )

    rating_type = request.POST.get('rating_type')
    score = request.POST.get('score')
    comment = request.POST.get('comment', '')

    # Validate rating type based on user role
    valid_types = {
        'ngo': [
            'ngo_to_donor',
            'ngo_to_volunteer'
        ],
        'donor': ['donor_to_volunteer'],
    }

    user_role = request.user.role
    if rating_type not in valid_types.get(user_role, []):
        messages.error(request, 'Invalid rating type.')
        return redirect('/')

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

    # Check already rated
    already_rated = Rating.objects.filter(
        rater=request.user,
        delivery=delivery,
        rating_type=rating_type
    ).exists()

    if already_rated:
        messages.warning(
            request,
            'You have already submitted this rating.'
        )
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

    # Create rating
    Rating.objects.create(
        rater=request.user,
        rated_user=rated_user,
        delivery=delivery,
        rating_type=rating_type,
        score=score,
        comment=comment
    )

    messages.success(
        request,
        f'Thank you! Your rating has been submitted.'
    )

    # Redirect back to appropriate dashboard
    if request.user.role == 'donor':
        return redirect('donor_requests')
    elif request.user.role == 'ngo':
        return redirect('ngo_my_requests')
    return redirect('/')


@login_required
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

    context = {
        'profile_user': profile_user,
        'ratings': ratings,
        'avg_rating': avg_rating,
        'rating_count': rating_count,
        'rating_label': rating_label,
        'score_breakdown': score_breakdown,
    }
    return render(
        request, 'profiles/user_profile.html', context
    )


def leaderboard_view(request):
    from django.db.models import Avg, Q

    # Top Donors — most delivered food posts
    top_donors = (
        CustomUser.objects.filter(role='donor')
        .annotate(
            delivered_count=Count(
                'food_posts',
                filter=Q(food_posts__status='delivered'),
            ),
            avg_rating=Avg('ratings_received__score'),
        )
        .filter(delivered_count__gt=0)
        .order_by('-delivered_count')[:10]
    )

    # Top Volunteers — most confirmed deliveries
    top_volunteers = (
        CustomUser.objects.filter(role='volunteer')
        .annotate(
            delivery_count=Count(
                'deliveries',
                filter=Q(deliveries__is_confirmed=True),
            ),
            avg_rating=Avg('ratings_received__score'),
        )
        .filter(delivery_count__gt=0)
        .order_by('-delivery_count')[:10]
    )

    return render(request, 'leaderboard.html', {
        'top_donors': top_donors,
        'top_volunteers': top_volunteers,
    })


def food_map_view(request):
    import json

    posts = (
        FoodPost.objects.filter(status='available')
        .exclude(latitude=None)
        .exclude(longitude=None)
        .select_related('donor')
    )

    posts_data = []
    for post in posts:
        posts_data.append({
            'id': post.pk,
            'title': post.title,
            'quantity': post.quantity,
            'category': post.get_category_display(),
            'location': post.location,
            'lat': float(post.latitude),
            'lng': float(post.longitude),
            'expiry': post.time_remaining(),
            'donor': post.donor.full_name,
            'request_url': f'/ngo/request/{post.pk}/',
        })

    return render(request, 'food_map.html', {
        'posts': posts,
        'posts_json': json.dumps(posts_data),
        'total': posts.count(),
    })


def heatmap_view(request):
    import json

    # All food posts with coordinates
    posts = FoodPost.objects.exclude(
        latitude=None
    ).exclude(
        longitude=None
    )

    # Heatmap data: [lat, lng, intensity]
    heat_data = []
    for post in posts:
        # Higher intensity for recent/delivered posts
        intensity = 0.5
        if post.status == 'delivered':
            intensity = 1.0
        elif post.status == 'available':
            intensity = 0.7

        heat_data.append([
            float(post.latitude),
            float(post.longitude),
            intensity
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
        'heat_data': json.dumps(heat_data),
        'stats':     stats,
    })


def offline_view(request):
    return render(request, 'offline.html')

