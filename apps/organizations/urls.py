from django.urls import path

from apps.organizations import views


app_name = "organizations"

urlpatterns = [
    path("settings/", views.organization_settings, name="settings"),

    path(
        "settings/profile/",
        views.organization_profile_update,
        name="profile_update",
    ),

    path(
        "settings/certificate/",
        views.organization_certificate_update,
        name="certificate_update",
    ),

    path(
        "settings/numbering/",
        views.organization_numbering_update,
        name="numbering_update",
    ),

    path(
        "settings/files/",
        views.organization_file_settings_update,
        name="file_settings_update",
    ),

    path(
        "settings/smtp/",
        views.organization_smtp_update,
        name="smtp_update",
    ),

    path(
        "settings/smtp/test/",
        views.organization_smtp_test,
        name="smtp_test",
    ),
]