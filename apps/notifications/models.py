from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationType(models.TextChoices):
    INFO = "INFO", "Info"

    REQUEST_ASSIGNED = "REQUEST_ASSIGNED", "Request Assigned"
    REQUEST_APPROVED = "REQUEST_APPROVED", "Request Approved"
    REQUEST_REJECTED = "REQUEST_REJECTED", "Request Rejected"
    REQUEST_COMMENTED = "REQUEST_COMMENTED", "Request Commented"

    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED", "Document Uploaded"
    WORKFLOW_UPDATED = "WORKFLOW_UPDATED", "Workflow Updated"

    SLA_REMINDER = "SLA_REMINDER", "SLA Reminder"
    SLA_OVERDUE = "SLA_OVERDUE", "SLA Overdue"
    SLA_ESCALATED = "SLA_ESCALATED", "SLA Escalated"
    APPROVAL_REMINDER = "APPROVAL_REMINDER", "Approval Reminder"
    BULK_ACTION = "BULK_ACTION", "Bulk Action"  


class Notification(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="notifications",
        blank=True,
        null=True,
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="sent_notifications",
        blank=True,
        null=True,
    )

    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
    )

    title = models.CharField(max_length=255)

    message = models.TextField()

    target_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Internal URL where user should go after clicking notification.",
    )

    object_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Example: DocumentRequest, ApprovalStep, DocumentAttachment",
    )

    object_id = models.CharField(
        max_length=100,
        blank=True,
    )

    is_read = models.BooleanField(default=False)

    read_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["recipient", "created_at"]),
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["notification_type"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(
                update_fields=[
                    "is_read",
                    "read_at",
                ]
            )
            
            
class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )

    # Master switches
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)

    # Watched request / general request activity
    watched_request_in_app = models.BooleanField(default=True)
    watched_request_email = models.BooleanField(default=True)

    # Comments / mentions / discussion
    comments_in_app = models.BooleanField(default=True)
    comments_email = models.BooleanField(default=True)

    # Approval assigned / approved / rejected / commented
    approvals_in_app = models.BooleanField(default=True)
    approvals_email = models.BooleanField(default=True)

    # Document upload / replace / version activity
    documents_in_app = models.BooleanField(default=True)
    documents_email = models.BooleanField(default=False)

    # AI / OCR / risk processing
    ai_in_app = models.BooleanField(default=True)
    ai_email = models.BooleanField(default=False)

    # SLA reminders / manual reminders / overdue alerts
    reminders_in_app = models.BooleanField(default=True)
    reminders_email = models.BooleanField(default=True)

    # Certificate generation / invalidation / verification
    certificates_in_app = models.BooleanField(default=True)
    certificates_email = models.BooleanField(default=True)

    # Weekly/daily summaries
    daily_summary_email = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["email_enabled"]),
            models.Index(fields=["in_app_enabled"]),
        ]

    def __str__(self):
        return f"Notification Preferences - {self.user}"
    
    
class NotificationDigestLog(models.Model):
    class DigestType(models.TextChoices):
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_digest_logs",
    )

    digest_type = models.CharField(
        max_length=20,
        choices=DigestType.choices,
    )

    subject = models.CharField(max_length=255)

    sent_to_email = models.EmailField()

    unread_notification_count = models.PositiveIntegerField(default=0)
    pending_approval_count = models.PositiveIntegerField(default=0)
    overdue_approval_count = models.PositiveIntegerField(default=0)
    watched_request_count = models.PositiveIntegerField(default=0)
    watched_activity_count = models.PositiveIntegerField(default=0)

    success = models.BooleanField(default=False)

    error_message = models.TextField(blank=True)

    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["user", "digest_type"]),
            models.Index(fields=["success"]),
            models.Index(fields=["sent_at"]),
        ]

    def __str__(self):
        return f"{self.get_digest_type_display()} digest for {self.user} - {self.sent_at}"
    
    
    
class NotificationDeliveryStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    RETRYING = "RETRYING", "Retrying"
    SKIPPED = "SKIPPED", "Skipped"


class NotificationDeliveryChannel(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    IN_APP = "IN_APP", "In-App"


class NotificationDeliveryLog(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_delivery_logs",
    )

    notification = models.ForeignKey(
        "notifications.Notification",
        on_delete=models.SET_NULL,
        related_name="delivery_logs",
        blank=True,
        null=True,
    )

    digest_log = models.ForeignKey(
        "notifications.NotificationDigestLog",
        on_delete=models.SET_NULL,
        related_name="delivery_logs",
        blank=True,
        null=True,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        related_name="notification_delivery_logs",
        blank=True,
        null=True,
    )

    channel = models.CharField(
        max_length=20,
        choices=NotificationDeliveryChannel.choices,
        default=NotificationDeliveryChannel.EMAIL,
    )

    status = models.CharField(
        max_length=20,
        choices=NotificationDeliveryStatus.choices,
        default=NotificationDeliveryStatus.PENDING,
    )

    notification_type = models.CharField(
        max_length=80,
        blank=True,
        default="",
    )

    preference_category = models.CharField(
        max_length=80,
        blank=True,
        default="",
    )

    subject = models.CharField(max_length=255)

    message = models.TextField(blank=True)

    target_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    recipient_email = models.EmailField(blank=True, default="")

    from_email = models.EmailField(blank=True, default="")

    provider = models.CharField(
        max_length=100,
        blank=True,
        default="SMTP",
    )

    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    retry_count = models.PositiveIntegerField(default=0)

    max_retries = models.PositiveIntegerField(default=3)

    error_message = models.TextField(blank=True, default="")

    traceback_text = models.TextField(blank=True, default="")

    metadata = models.JSONField(default=dict, blank=True)

    queued_at = models.DateTimeField(blank=True, null=True)

    sent_at = models.DateTimeField(blank=True, null=True)

    failed_at = models.DateTimeField(blank=True, null=True)

    skipped_at = models.DateTimeField(blank=True, null=True)

    last_attempt_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "created_at"]),
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["notification_type"]),
            models.Index(fields=["preference_category"]),
            models.Index(fields=["celery_task_id"]),
        ]

    def __str__(self):
        return f"{self.channel} | {self.status} | {self.recipient}"

    @property
    def can_retry(self):
        return (
            self.channel == NotificationDeliveryChannel.EMAIL
            and self.status == NotificationDeliveryStatus.FAILED
            and self.retry_count < self.max_retries
        )