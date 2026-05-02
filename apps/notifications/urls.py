from django.urls import path

from apps.notifications import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path(
        "<int:pk>/read/",
        views.notification_mark_read,
        name="mark_read",
    ),
    path(
        "mark-all-read/",
        views.notification_mark_all_read,
        name="mark_all_read",
    ),
    path(
        "preferences/",
        views.notification_preferences,
        name="preferences",
    ),
    path(
        "digest/",
        views.digest_preview,
        name="digest_preview",
    ),

    path(
        "digest/send-test/",
        views.send_test_digest,
        name="send_test_digest",
    ),
    path(
        "deliveries/",
        views.delivery_dashboard,
        name="delivery_dashboard",
    ),

    path(
        "deliveries/<int:pk>/",
        views.delivery_detail,
        name="delivery_detail",
    ),

    path(
        "deliveries/<int:pk>/retry/",
        views.delivery_retry,
        name="delivery_retry",
    ),
]