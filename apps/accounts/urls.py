from django.urls import path

from apps.accounts import views


app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("super-admin-login/", views.super_admin_login, name="super_admin_login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),

    path(
        "register-organization/",
        views.register_organization,
        name="register_organization",
    ),

    # Organization user management
    path("users/", views.organization_user_list, name="org_user_list"),
    path("users/create/", views.organization_user_create, name="org_user_create"),
    path("users/<int:pk>/", views.organization_user_detail, name="org_user_detail"),
    path("users/<int:pk>/edit/", views.organization_user_update, name="org_user_update"),

    path(
        "users/<int:pk>/toggle-status/",
        views.organization_user_toggle_status,
        name="org_user_toggle_status",
    ),

    path(
        "users/<int:pk>/reset-password/",
        views.organization_user_reset_password,
        name="org_user_reset_password",
    ),

    path(
        "profile/signature/",
        views.profile_signature_update,
        name="profile_signature_update",
    ),
]