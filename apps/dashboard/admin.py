from django.contrib import admin

from apps.dashboard.models import BackupJobLog

from apps.dashboard.models import BackupJobLog, MaintenanceMode, RestoreJobLog
@admin.register(BackupJobLog)
class BackupJobLogAdmin(admin.ModelAdmin):
    list_display = [
        "job_type",
        "status",
        "file_name",
        "file_size_mb",
        "duration_ms",
        "triggered_by",
        "started_at",
        "completed_at",
    ]

    search_fields = [
        "file_name",
        "file_path",
        "error_message",
        "celery_task_id",
        "triggered_by__username",
        "triggered_by__email",
        "triggered_by__full_name",
    ]

    list_filter = [
        "job_type",
        "status",
        "started_at",
        "completed_at",
    ]

    readonly_fields = [
        "started_at",
        "completed_at",
        "duration_ms",
    ]

    autocomplete_fields = [
        "triggered_by",
    ]

    fieldsets = (
        (
            "Job Info",
            {
                "fields": (
                    "job_type",
                    "status",
                    "triggered_by",
                    "celery_task_id",
                    "metadata",
                )
            },
        ),
        (
            "File Info",
            {
                "fields": (
                    "file_path",
                    "file_name",
                    "file_size_mb",
                )
            },
        ),
        (
            "Error Info",
            {
                "fields": (
                    "error_message",
                    "traceback_text",
                )
            },
        ),
        (
            "Timing",
            {
                "fields": (
                    "started_at",
                    "completed_at",
                    "duration_ms",
                )
            },
        ),
    )
    
    
from apps.dashboard.models import BackupJobLog, RestoreJobLog

@admin.register(RestoreJobLog)
class RestoreJobLogAdmin(admin.ModelAdmin):
    list_display = [
        "original_filename",
        "file_type",
        "status",
        "file_size_mb",
        "uploaded_by",
        "is_confirmed",
        "created_at",
        "validated_at",
        "restored_at",
    ]

    search_fields = [
        "original_filename",
        "restore_notes",
        "error_message",
        "uploaded_by__username",
        "uploaded_by__email",
        "uploaded_by__full_name",
    ]

    list_filter = [
        "file_type",
        "status",
        "is_confirmed",
        "created_at",
        "validated_at",
        "restored_at",
    ]

    readonly_fields = [
        "file_size_mb",
        "validation_summary",
        "dry_run_summary",
        "media_preview",
        "error_message",
        "traceback_text",
        "created_at",
        "validated_at",
        "dry_run_at",
        "confirmed_at",
        "restored_at",
    ]

    autocomplete_fields = [
        "uploaded_by",
    ]
    
    
@admin.register(MaintenanceMode)
class MaintenanceModeAdmin(admin.ModelAdmin):
    list_display = [
        "is_enabled",
        "restore_safe_lock",
        "allow_super_admin_bypass",
        "allow_staff_bypass",
        "enabled_by",
        "enabled_at",
        "disabled_by",
        "disabled_at",
        "updated_at",
    ]

    readonly_fields = [
        "enabled_at",
        "disabled_at",
        "created_at",
        "updated_at",
    ]

    autocomplete_fields = [
        "enabled_by",
        "disabled_by",
    ]

    fieldsets = (
        (
            "Maintenance Status",
            {
                "fields": (
                    "is_enabled",
                    "restore_safe_lock",
                    "title",
                    "message",
                )
            },
        ),
        (
            "Bypass Rules",
            {
                "fields": (
                    "allow_super_admin_bypass",
                    "allow_staff_bypass",
                    "allowed_ips",
                )
            },
        ),
        (
            "Audit Info",
            {
                "fields": (
                    "enabled_by",
                    "enabled_at",
                    "disabled_by",
                    "disabled_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return not MaintenanceMode.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False