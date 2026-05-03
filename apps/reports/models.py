import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
class RequestShareLink(models.Model):
    document_request = models.ForeignKey(
        "approvals.DocumentRequest",
        on_delete=models.CASCADE,
        related_name="share_links",
    )

    token = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
    )

    title = models.CharField(
        max_length=150,
        default="Public Share Link",
    )

    allow_summary_view = models.BooleanField(default=True)

    allow_archive_download = models.BooleanField(default=False)

    expires_at = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_request_share_links",
        blank=True,
        null=True,
    )

    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="revoked_request_share_links",
        blank=True,
        null=True,
    )

    revoked_at = models.DateTimeField(blank=True, null=True)

    last_accessed_at = models.DateTimeField(blank=True, null=True)

    access_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["document_request", "is_active"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.document_request.request_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()

        super().save(*args, **kwargs)

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(48)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return self.is_active and not self.is_expired

    def mark_accessed(self):
        self.access_count += 1
        self.last_accessed_at = timezone.now()
        self.save(
            update_fields=[
                "access_count",
                "last_accessed_at",
            ]
        )

    def revoke(self, user=None):
        self.is_active = False
        self.revoked_by = user
        self.revoked_at = timezone.now()
        self.save(
            update_fields=[
                "is_active",
                "revoked_by",
                "revoked_at",
            ]
        )
        
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

class ApprovalCertificateSignature(models.Model):
    document_request = models.OneToOneField(
        "approvals.DocumentRequest",
        on_delete=models.CASCADE,
        related_name="certificate_signature",
    )

    certificate_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="signed_approval_certificates",
        blank=True,
        null=True,
    )

    signed_by_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Snapshot of signer name at signing time.",
    )

    signed_by_role = models.CharField(
        max_length=100,
        blank=True,
        help_text="Snapshot of signer role/designation at signing time.",
    )

    organization_name = models.CharField(
        max_length=180,
        blank=True,
        help_text="Snapshot of organization name at signing time.",
    )

    certificate_hash = models.CharField(
        max_length=128,
        blank=True,
        db_index=True,
        help_text="SHA-256 hash generated from certificate metadata.",
    )

    verification_code = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text="Short verification code for public verification.",
    )

    verification_url = models.CharField(
        max_length=500,
        blank=True,
    )

    signed_at = models.DateTimeField(
        default=timezone.now,
    )

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
    )

    user_agent = models.TextField(blank=True)

    is_valid = models.BooleanField(default=True)

    invalidated_at = models.DateTimeField(blank=True, null=True)

    invalidated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="invalidated_approval_certificates",
        blank=True,
        null=True,
    )

    invalidation_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-signed_at"]
        indexes = [
            models.Index(fields=["certificate_uuid"]),
            models.Index(fields=["verification_code"]),
            models.Index(fields=["certificate_hash"]),
            models.Index(fields=["signed_at"]),
            models.Index(fields=["is_valid"]),
        ]

    def __str__(self):
        return f"{self.document_request.request_number} - {self.verification_code}"

    def invalidate(self, user=None, reason=""):
        self.is_valid = False
        self.invalidated_at = timezone.now()
        self.invalidated_by = user
        self.invalidation_reason = reason
        self.save(
            update_fields=[
                "is_valid",
                "invalidated_at",
                "invalidated_by",
                "invalidation_reason",
            ]
        )