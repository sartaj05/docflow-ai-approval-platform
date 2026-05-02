from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    CREATED = "CREATED", "Created"
    UPDATED = "UPDATED", "Updated"
    DELETED = "DELETED", "Deleted"
    SUBMITTED = "SUBMITTED", "Submitted"
    CANCELLED = "CANCELLED", "Cancelled"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    COMMENTED = "COMMENTED", "Commented"
    UPLOADED = "UPLOADED", "Uploaded"
    DOWNLOADED = "DOWNLOADED", "Downloaded"
    LOGIN = "LOGIN", "Login"
    LOGOUT = "LOGOUT", "Logout"
    AI_PROCESSED = "AI_PROCESSED", "AI Processed"
    PDF_GENERATED = "PDF_GENERATED", "PDF Generated"
    STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"
    EXPORTED = "EXPORTED", "Exported"
    PRINTED = "PRINTED", "Printed"


class AuditLog(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        blank=True,
        null=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        blank=True,
        null=True,
    )

    action = models.CharField(
        max_length=40,
        choices=AuditAction.choices,
    )

    model_name = models.CharField(max_length=100)

    object_id = models.CharField(max_length=100, blank=True)

    message = models.TextField()

    ip_address = models.GenericIPAddressField(blank=True, null=True)

    user_agent = models.TextField(blank=True)

    extra_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["action"]),
            models.Index(fields=["model_name"]),
            models.Index(fields=["object_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.model_name} - {self.created_at}"