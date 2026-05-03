from django.urls import path

from apps.superadmin import views

app_name = "superadmin"

urlpatterns = [
    path("organizations/", views.organization_list, name="organizations"),
    path(
        "organizations/<int:pk>/",
        views.organization_detail,
        name="organization_detail",
    ),
    path(
        "organizations/<int:pk>/toggle-status/",
        views.organization_toggle_status,
        name="organization_toggle_status",
    ),

    path("users/", views.user_list, name="users"),
    path(
        "users/<int:pk>/toggle-status/",
        views.user_toggle_status,
        name="user_toggle_status",
    ),
]