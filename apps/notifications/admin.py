from django.contrib import admin

from apps.notifications.models import Notification
from apps.notifications.models import Notification, NotificationPreference

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "recipient",
        "notification_type",
        "organization",
        "is_read",
        "created_at",
    ]

    search_fields = [
        "title",
        "message",
        "recipient__username",
        "recipient__email",
        "recipient__full_name",
        "actor__username",
        "actor__email",
        "organization__name",
        "object_type",
        "object_id",
    ]

    list_filter = [
        "notification_type",
        "is_read",
        "organization",
        "created_at",
    ]

    readonly_fields = [
        "created_at",
        "read_at",
    ]

    autocomplete_fields = [
        "recipient",
        "actor",
        "organization",
    ]
    
    
@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "in_app_enabled",
        "email_enabled",
        "watched_request_in_app",
        "watched_request_email",
        "comments_in_app",
        "comments_email",
        "approvals_in_app",
        "approvals_email",
        "daily_summary_email",
        "updated_at",
    ]

    search_fields = [
        "user__username",
        "user__email",
        "user__full_name",
    ]

    list_filter = [
        "in_app_enabled",
        "email_enabled",
        "watched_request_in_app",
        "watched_request_email",
        "comments_in_app",
        "comments_email",
        "approvals_in_app",
        "approvals_email",
        "documents_in_app",
        "documents_email",
        "ai_in_app",
        "ai_email",
        "reminders_in_app",
        "reminders_email",
        "certificates_in_app",
        "certificates_email",
        "daily_summary_email",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    autocomplete_fields = [
        "user",
    ]
    
from apps.notifications.models import (
    Notification,
    NotificationDigestLog,
    NotificationPreference,
)
@admin.register(NotificationDigestLog)
class NotificationDigestLogAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "digest_type",
        "sent_to_email",
        "unread_notification_count",
        "pending_approval_count",
        "overdue_approval_count",
        "watched_request_count",
        "watched_activity_count",
        "success",
        "sent_at",
    ]

    search_fields = [
        "user__username",
        "user__email",
        "user__full_name",
        "subject",
        "sent_to_email",
        "error_message",
    ]

    list_filter = [
        "digest_type",
        "success",
        "sent_at",
    ]

    readonly_fields = [
        "sent_at",
    ]

    autocomplete_fields = [
        "user",
    ]
    
from apps.notifications.models import (
    Notification,
    NotificationDeliveryLog,
    NotificationDigestLog,
    NotificationPreference,
)


@admin.register(NotificationDeliveryLog)
class NotificationDeliveryLogAdmin(admin.ModelAdmin):
    list_display = [
        "recipient",
        "channel",
        "status",
        "subject",
        "recipient_email",
        "retry_count",
        "max_retries",
        "created_at",
        "sent_at",
        "failed_at",
    ]

    search_fields = [
        "recipient__username",
        "recipient__email",
        "recipient__full_name",
        "subject",
        "message",
        "recipient_email",
        "error_message",
        "celery_task_id",
    ]

    list_filter = [
        "channel",
        "status",
        "notification_type",
        "preference_category",
        "provider",
        "created_at",
        "sent_at",
        "failed_at",
    ]

    readonly_fields = [
        "queued_at",
        "sent_at",
        "failed_at",
        "skipped_at",
        "last_attempt_at",
        "created_at",
        "updated_at",
    ]

    autocomplete_fields = [
        "recipient",
        "notification",
        "digest_log",
        "organization",
    ]

    fieldsets = (
        (
            "Delivery Info",
            {
                "fields": (
                    "recipient",
                    "notification",
                    "digest_log",
                    "organization",
                    "channel",
                    "status",
                    "notification_type",
                    "preference_category",
                )
            },
        ),
        (
            "Email Content",
            {
                "fields": (
                    "subject",
                    "message",
                    "target_url",
                    "recipient_email",
                    "from_email",
                    "provider",
                )
            },
        ),
        (
            "Retry / Error",
            {
                "fields": (
                    "retry_count",
                    "max_retries",
                    "celery_task_id",
                    "error_message",
                    "traceback_text",
                    "metadata",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "queued_at",
                    "sent_at",
                    "failed_at",
                    "skipped_at",
                    "last_attempt_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )