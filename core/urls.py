from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("transparency/", views.transparency_view, name="transparency"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Password Reset URLs
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="auth/password_reset.html",
            email_template_name="auth/password_reset_email.html",
            subject_template_name="auth/password_reset_subject.txt",
            success_url="/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="auth/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="auth/password_reset_confirm.html",
            success_url="/reset/done/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="auth/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("profile/", views.profile_view, name="profile"),
    path("dashboard/", views.dashboard_redirect, name="dashboard"),
    path("donor/dashboard/", views.donor_dashboard, name="donor_dashboard"),
    path("donor/add/", views.add_food_post, name="add_food"),
    path("donor/edit/<int:pk>/", views.edit_food_post, name="edit_food"),
    path("donor/delete/<int:pk>/", views.delete_food_post, name="delete_food"),
    path("donor/requests/", views.donor_requests, name="donor_requests"),
    path(
        "donor/requests/<int:pk>/handle/",
        views.handle_request,
        name="handle_request",
    ),
    path("ngo/dashboard/", views.ngo_dashboard, name="ngo_dashboard"),
    path("ngo/request/<int:pk>/", views.request_food, name="request_food"),
    path("ngo/my-requests/", views.ngo_my_requests, name="ngo_my_requests"),
    # Volunteer
    path(
        "volunteer/dashboard/",
        views.volunteer_dashboard,
        name="volunteer_dashboard",
    ),
    path(
        "volunteer/accept/<int:pk>/",
        views.accept_delivery,
        name="accept_delivery",
    ),
    path(
        "volunteer/pickup/<int:pk>/",
        views.confirm_pickup,
        name="confirm_pickup",
    ),
    path(
        "volunteer/confirm/<int:pk>/",
        views.confirm_delivery,
        name="confirm_delivery",
    ),
    path("admin-panel/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-panel/expire/", views.admin_expire_food, name="admin_expire_food"),
]
