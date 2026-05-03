from django.conf import settings
from django.db import models


class BackupJobType(models.TextChoices):
    DATABASE = "DATABASE", "Database"
    MEDIA = "MEDIA", "Media"
    FULL = "FULL", "Full Backup"
    AUDIT = "AUDIT", "Audit Export"
    NOTIFICATIONS = "NOTIFICATIONS", "Notification Export"
    REQUESTS = "REQUESTS", "Approval Request Export"


class BackupJobStatus(models.TextChoices):
    STARTED = "STARTED", "Started"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    CLEANED = "CLEANED", "Cleaned"


class BackupJobLog(models.Model):
    job_type = models.CharField(
        max_length=30,
        choices=BackupJobType.choices,
    )

    status = models.CharField(
        max_length=30,
        choices=BackupJobStatus.choices,
        default=BackupJobStatus.STARTED,
    )

    file_path = models.TextField(blank=True)
    file_name = models.CharField(max_length=255, blank=True)

    file_size_mb = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    duration_ms = models.PositiveIntegerField(default=0)

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="triggered_backup_jobs",
        blank=True,
        null=True,
    )

    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    error_message = models.TextField(blank=True)
    traceback_text = models.TextField(blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["job_type", "status"]),
            models.Index(fields=["status", "started_at"]),
            models.Index(fields=["started_at"]),
            models.Index(fields=["celery_task_id"]),
        ]

    def __str__(self):
        return f"{self.get_job_type_display()} - {self.get_status_display()}"

    @property
    def is_success(self):
        return self.status == BackupJobStatus.SUCCESS

    @property
    def is_failed(self):
        return self.status == BackupJobStatus.FAILED
    
    
class RestoreJobStatus(models.TextChoices):
    UPLOADED = "UPLOADED", "Uploaded"
    VALIDATED = "VALIDATED", "Validated"
    FAILED_VALIDATION = "FAILED_VALIDATION", "Failed Validation"
    DRY_RUN = "DRY_RUN", "Dry Run"
    READY_FOR_RESTORE = "READY_FOR_RESTORE", "Ready For Restore"
    RESTORED = "RESTORED", "Restored"
    FAILED = "FAILED", "Failed"


class RestoreFileType(models.TextChoices):
    DATABASE_JSON = "DATABASE_JSON", "Database JSON"
    DATABASE_SQL = "DATABASE_SQL", "Database SQL"
    MEDIA_ZIP = "MEDIA_ZIP", "Media ZIP"
    FULL_ZIP = "FULL_ZIP", "Full Backup ZIP"
    UNKNOWN = "UNKNOWN", "Unknown"


class RestoreJobLog(models.Model):
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="restore_jobs",
        blank=True,
        null=True,
    )

    uploaded_file = models.FileField(
        upload_to="restore_uploads/",
    )

    original_filename = models.CharField(max_length=255)

    file_type = models.CharField(
        max_length=30,
        choices=RestoreFileType.choices,
        default=RestoreFileType.UNKNOWN,
    )

    status = models.CharField(
        max_length=30,
        choices=RestoreJobStatus.choices,
        default=RestoreJobStatus.UPLOADED,
    )

    file_size_mb = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    validation_summary = models.JSONField(default=dict, blank=True)

    dry_run_summary = models.JSONField(default=dict, blank=True)

    media_preview = models.JSONField(default=dict, blank=True)

    restore_notes = models.TextField(blank=True)

    confirmation_text = models.CharField(max_length=255, blank=True)

    is_confirmed = models.BooleanField(default=False)

    error_message = models.TextField(blank=True)

    traceback_text = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(blank=True, null=True)
    dry_run_at = models.DateTimeField(blank=True, null=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    restored_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["file_type", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["uploaded_by", "created_at"]),
        ]

    def __str__(self):
        return f"{self.original_filename} - {self.get_status_display()}"

    @property
    def can_dry_run(self):
        return self.status in [
            RestoreJobStatus.VALIDATED,
            RestoreJobStatus.DRY_RUN,
            RestoreJobStatus.READY_FOR_RESTORE,
        ]

    @property
    def can_confirm(self):
        return self.status in [
            RestoreJobStatus.DRY_RUN,
            RestoreJobStatus.READY_FOR_RESTORE,
        ]

    @property
    def can_restore_media(self):
        return (
            self.is_confirmed
            and self.file_type in [
                RestoreFileType.MEDIA_ZIP,
                RestoreFileType.FULL_ZIP,
            ]
            and self.status == RestoreJobStatus.READY_FOR_RESTORE
        )
        
        
class MaintenanceMode(models.Model):
    is_enabled = models.BooleanField(default=False)

    title = models.CharField(
        max_length=255,
        default="System Maintenance",
    )

    message = models.TextField(
        default="DocFlow AI is currently under maintenance. Please try again later.",
    )

    restore_safe_lock = models.BooleanField(
        default=False,
        help_text="When enabled, only super admin users can access the system. Useful during restore operations.",
    )

    allow_super_admin_bypass = models.BooleanField(
        default=True,
    )

    allow_staff_bypass = models.BooleanField(
        default=False,
        help_text="Allow Django staff users to bypass maintenance mode.",
    )

    allowed_ips = models.TextField(
        blank=True,
        help_text="Optional comma-separated IP addresses allowed during maintenance.",
    )

    enabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="enabled_maintenance_modes",
        blank=True,
        null=True,
    )

    disabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="disabled_maintenance_modes",
        blank=True,
        null=True,
    )

    enabled_at = models.DateTimeField(blank=True, null=True)
    disabled_at = models.DateTimeField(blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Maintenance Mode"
        verbose_name_plural = "Maintenance Mode"

    def __str__(self):
        return "Maintenance Mode"

    @classmethod
    def get_config(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def allowed_ip_list(self):
        return [
            ip.strip()
            for ip in self.allowed_ips.split(",")
            if ip.strip()
        ]

    def enable(self, user=None, restore_safe_lock=False):
        from django.utils import timezone

        self.is_enabled = True
        self.restore_safe_lock = restore_safe_lock
        self.enabled_by = user
        self.enabled_at = timezone.now()
        self.disabled_by = None
        self.disabled_at = None
        self.save(
            update_fields=[
                "is_enabled",
                "restore_safe_lock",
                "enabled_by",
                "enabled_at",
                "disabled_by",
                "disabled_at",
                "updated_at",
            ]
        )

    def disable(self, user=None):
        from django.utils import timezone

        self.is_enabled = False
        self.restore_safe_lock = False
        self.disabled_by = user
        self.disabled_at = timezone.now()
        self.save(
            update_fields=[
                "is_enabled",
                "restore_safe_lock",
                "disabled_by",
                "disabled_at",
                "updated_at",
            ]
        )