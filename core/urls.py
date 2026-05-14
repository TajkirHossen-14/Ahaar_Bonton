from django.urls import path

from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("transparency/", views.transparency_view, name="transparency"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
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
