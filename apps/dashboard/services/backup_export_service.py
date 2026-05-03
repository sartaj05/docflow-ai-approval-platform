import csv
import os
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.http import FileResponse
from django.utils import timezone
import traceback
import time

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.dashboard.models import (
    BackupJobLog,
    BackupJobStatus,
    BackupJobType,
)

BACKUP_DIR_NAME = "backups"


def get_backup_root():
    backup_root = Path(settings.MEDIA_ROOT) / BACKUP_DIR_NAME
    backup_root.mkdir(parents=True, exist_ok=True)
    return backup_root


def get_timestamp():
    return timezone.localtime().strftime("%Y%m%d_%H%M%S")


def get_backup_file_response(file_path, download_name=None):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError("Backup/export file not found.")

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename=download_name or file_path.name,
    )


def create_json_database_backup():
    """
    Cross-platform Django backup using dumpdata.
    Works on Windows without pg_dump dependency.
    """
    backup_root = get_backup_root()
    file_path = backup_root / f"database_dump_{get_timestamp()}.json"

    with open(file_path, "w", encoding="utf-8") as output_file:
        call_command(
            "dumpdata",
            "--natural-foreign",
            "--natural-primary",
            indent=2,
            stdout=output_file,
        )

    return file_path


def create_postgres_pg_dump_backup():
    """
    PostgreSQL pg_dump backup.
    Requires pg_dump in PATH.
    Falls back should be handled by caller.
    """
    backup_root = get_backup_root()
    file_path = backup_root / f"postgres_backup_{get_timestamp()}.sql"

    db = settings.DATABASES["default"]

    db_name = db.get("NAME")
    db_user = db.get("USER")
    db_password = db.get("PASSWORD")
    db_host = db.get("HOST", "localhost")
    db_port = str(db.get("PORT", "5432"))

    env = os.environ.copy()

    if db_password:
        env["PGPASSWORD"] = db_password

    command = [
        "pg_dump",
        "-h",
        db_host,
        "-p",
        db_port,
        "-U",
        db_user,
        "-d",
        db_name,
        "-f",
        str(file_path),
    ]

    subprocess.run(
        command,
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )

    return file_path


def create_database_backup(prefer_pg_dump=True):
    if prefer_pg_dump:
        try:
            return create_postgres_pg_dump_backup()
        except Exception:
            return create_json_database_backup()

    return create_json_database_backup()


def create_media_backup_zip():
    backup_root = get_backup_root()
    media_root = Path(settings.MEDIA_ROOT)

    file_path = backup_root / f"media_backup_{get_timestamp()}.zip"

    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if not media_root.exists():
            return file_path

        for item in media_root.rglob("*"):
            if item.is_file():
                if BACKUP_DIR_NAME in item.parts:
                    continue

                archive_name = item.relative_to(media_root)
                zip_file.write(item, archive_name)

    return file_path


def create_full_backup_zip():
    backup_root = get_backup_root()

    db_backup = create_database_backup(prefer_pg_dump=True)
    media_backup = create_media_backup_zip()

    file_path = backup_root / f"full_backup_{get_timestamp()}.zip"

    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(db_backup, db_backup.name)
        zip_file.write(media_backup, media_backup.name)

    return file_path


def create_audit_log_export_csv():
    from apps.audit.models import AuditLog

    backup_root = get_backup_root()
    file_path = backup_root / f"audit_logs_{get_timestamp()}.csv"

    logs = (
        AuditLog.objects.select_related(
            "organization",
            "user",
        )
        .order_by("-created_at")
    )

    with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(
            [
                "ID",
                "Organization",
                "User",
                "Action",
                "Model Name",
                "Object ID",
                "Message",
                "IP Address",
                "User Agent",
                "Created At",
            ]
        )

        for log in logs:
            writer.writerow(
                [
                    log.pk,
                    getattr(log.organization, "name", "") if log.organization else "",
                    getattr(log.user, "display_name", "") if log.user else "",
                    getattr(log, "action", ""),
                    getattr(log, "model_name", ""),
                    getattr(log, "object_id", ""),
                    getattr(log, "message", ""),
                    getattr(log, "ip_address", ""),
                    getattr(log, "user_agent", ""),
                    timezone.localtime(log.created_at).strftime("%d-%m-%Y %I:%M %p")
                    if getattr(log, "created_at", None)
                    else "",
                ]
            )

    return file_path


def create_notification_delivery_export_csv():
    from apps.notifications.models import NotificationDeliveryLog

    backup_root = get_backup_root()
    file_path = backup_root / f"notification_delivery_logs_{get_timestamp()}.csv"

    logs = (
        NotificationDeliveryLog.objects.select_related(
            "recipient",
            "organization",
        )
        .order_by("-created_at")
    )

    with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(
            [
                "ID",
                "Recipient",
                "Recipient Email",
                "Organization",
                "Channel",
                "Status",
                "Subject",
                "Preference Category",
                "Retry Count",
                "Max Retries",
                "Error Message",
                "Created At",
                "Sent At",
                "Failed At",
            ]
        )

        for log in logs:
            writer.writerow(
                [
                    log.pk,
                    getattr(log.recipient, "display_name", "") if log.recipient else "",
                    getattr(log, "recipient_email", ""),
                    getattr(log.organization, "name", "") if log.organization else "",
                    getattr(log, "channel", ""),
                    getattr(log, "status", ""),
                    getattr(log, "subject", ""),
                    getattr(log, "preference_category", ""),
                    getattr(log, "retry_count", ""),
                    getattr(log, "max_retries", ""),
                    getattr(log, "error_message", ""),
                    timezone.localtime(log.created_at).strftime("%d-%m-%Y %I:%M %p")
                    if getattr(log, "created_at", None)
                    else "",
                    timezone.localtime(log.sent_at).strftime("%d-%m-%Y %I:%M %p")
                    if getattr(log, "sent_at", None)
                    else "",
                    timezone.localtime(log.failed_at).strftime("%d-%m-%Y %I:%M %p")
                    if getattr(log, "failed_at", None)
                    else "",
                ]
            )

    return file_path


def create_request_export_csv():
    from apps.approvals.models import DocumentRequest

    backup_root = get_backup_root()
    file_path = backup_root / f"approval_requests_{get_timestamp()}.csv"

    requests = (
        DocumentRequest.objects.select_related(
            "organization",
            "department",
            "created_by",
            "workflow",
        )
        .order_by("-created_at")
    )

    with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(
            [
                "ID",
                "Request Number",
                "Title",
                "Organization",
                "Department",
                "Created By",
                "Workflow",
                "Category",
                "Priority",
                "Status",
                "Risk Level",
                "Created At",
                "Submitted At",
                "Approved At",
                "Rejected At",
            ]
        )

        for item in requests:
            writer.writerow(
                [
                    item.pk,
                    item.request_number,
                    item.title,
                    item.organization.name if item.organization else "",
                    item.department.name if item.department else "",
                    item.created_by.display_name if item.created_by else "",
                    item.workflow.name if item.workflow else "",
                    item.get_category_display() if hasattr(item, "get_category_display") else item.category,
                    item.get_priority_display() if hasattr(item, "get_priority_display") else item.priority,
                    item.get_status_display() if hasattr(item, "get_status_display") else item.status,
                    item.risk_level,
                    timezone.localtime(item.created_at).strftime("%d-%m-%Y %I:%M %p")
                    if item.created_at
                    else "",
                    timezone.localtime(item.submitted_at).strftime("%d-%m-%Y %I:%M %p")
                    if item.submitted_at
                    else "",
                    timezone.localtime(item.approved_at).strftime("%d-%m-%Y %I:%M %p")
                    if item.approved_at
                    else "",
                    timezone.localtime(item.rejected_at).strftime("%d-%m-%Y %I:%M %p")
                    if item.rejected_at
                    else "",
                ]
            )

    return file_path


def list_recent_backup_files(limit=30):
    backup_root = get_backup_root()

    files = []

    for item in backup_root.iterdir():
        if item.is_file():
            files.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "size_mb": round(item.stat().st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(item.stat().st_mtime),
                }
            )

    files.sort(key=lambda item: item["created_at"], reverse=True)

    return files[:limit]


def delete_old_backups(days=15):
    backup_root = get_backup_root()
    cutoff = timezone.now().timestamp() - (days * 24 * 60 * 60)

    deleted_count = 0

    for item in backup_root.iterdir():
        if item.is_file() and item.stat().st_mtime < cutoff:
            item.unlink()
            deleted_count += 1

    return deleted_count


def get_backup_dashboard_summary():
    backup_root = get_backup_root()
    files = list_recent_backup_files(limit=50)

    total_size_mb = round(
        sum(file_item["size_mb"] for file_item in files),
        2,
    )

    disk_usage = shutil.disk_usage(settings.BASE_DIR)

    return {
        "backup_root": backup_root,
        "recent_files": files,
        "total_files": len(files),
        "total_size_mb": total_size_mb,
        "disk_total_gb": round(disk_usage.total / (1024 ** 3), 2),
        "disk_free_gb": round(disk_usage.free / (1024 ** 3), 2),
        "disk_used_percent": round((disk_usage.used / disk_usage.total) * 100, 2),
    }
    
def get_backup_job_type_from_action(action):
    mapping = {
        "database": BackupJobType.DATABASE,
        "media": BackupJobType.MEDIA,
        "full": BackupJobType.FULL,
        "audit": BackupJobType.AUDIT,
        "notifications": BackupJobType.NOTIFICATIONS,
        "requests": BackupJobType.REQUESTS,
    }

    return mapping.get(action, BackupJobType.FULL)


def get_action_from_backup_job_type(job_type):
    mapping = {
        BackupJobType.DATABASE: "database",
        BackupJobType.MEDIA: "media",
        BackupJobType.FULL: "full",
        BackupJobType.AUDIT: "audit",
        BackupJobType.NOTIFICATIONS: "notifications",
        BackupJobType.REQUESTS: "requests",
    }

    return mapping.get(job_type, "full")


def create_backup_by_action(action):
    if action == "database":
        return create_database_backup(prefer_pg_dump=True)

    if action == "media":
        return create_media_backup_zip()

    if action == "full":
        return create_full_backup_zip()

    if action == "audit":
        return create_audit_log_export_csv()

    if action == "notifications":
        return create_notification_delivery_export_csv()

    if action == "requests":
        return create_request_export_csv()

    raise ValueError("Invalid backup action selected.")


def create_backup_job_log(job_type, triggered_by=None, celery_task_id="", metadata=None):
    return BackupJobLog.objects.create(
        job_type=job_type,
        status=BackupJobStatus.STARTED,
        triggered_by=triggered_by,
        celery_task_id=celery_task_id or "",
        metadata=metadata or {},
    )


def mark_backup_job_success(job_log, file_path, started_perf):
    file_path = Path(file_path)

    file_size_mb = 0

    if file_path.exists():
        file_size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)

    job_log.status = BackupJobStatus.SUCCESS
    job_log.file_path = str(file_path)
    job_log.file_name = file_path.name
    job_log.file_size_mb = file_size_mb
    job_log.completed_at = timezone.now()
    job_log.duration_ms = round((time.perf_counter() - started_perf) * 1000)
    job_log.error_message = ""
    job_log.traceback_text = ""
    job_log.save(
        update_fields=[
            "status",
            "file_path",
            "file_name",
            "file_size_mb",
            "completed_at",
            "duration_ms",
            "error_message",
            "traceback_text",
        ]
    )

    return job_log


def mark_backup_job_failed(job_log, exc, started_perf):
    job_log.status = BackupJobStatus.FAILED
    job_log.completed_at = timezone.now()
    job_log.duration_ms = round((time.perf_counter() - started_perf) * 1000)
    job_log.error_message = str(exc)
    job_log.traceback_text = traceback.format_exc()
    job_log.save(
        update_fields=[
            "status",
            "completed_at",
            "duration_ms",
            "error_message",
            "traceback_text",
        ]
    )

    return job_log


def notify_super_admins_backup_failed(job_log):
    try:
        from apps.notifications.models import NotificationType
        from apps.notifications.services.notification_service import create_notification

        User = get_user_model()

        super_admins = User.objects.filter(
            is_superuser=True,
            is_active=True,
        )

        for admin_user in super_admins:
            create_notification(
                recipient=admin_user,
                title="Backup job failed",
                message=(
                    f"{job_log.get_job_type_display()} backup failed. "
                    f"Reason: {job_log.error_message}"
                ),
                notification_type=NotificationType.INFO,
                organization=None,
                actor=None,
                target_url="/dashboard/backup-export/",
                object_type="BackupJobLog",
                object_id=job_log.pk,
                preference_category="general",
                send_email=True,
            )

    except Exception:
        pass


def run_backup_job(action, triggered_by=None, celery_task_id="", metadata=None):
    job_type = get_backup_job_type_from_action(action)

    job_log = create_backup_job_log(
        job_type=job_type,
        triggered_by=triggered_by,
        celery_task_id=celery_task_id,
        metadata=metadata,
    )

    started_perf = time.perf_counter()

    try:
        file_path = create_backup_by_action(action)

        return mark_backup_job_success(
            job_log=job_log,
            file_path=file_path,
            started_perf=started_perf,
        )

    except Exception as exc:
        job_log = mark_backup_job_failed(
            job_log=job_log,
            exc=exc,
            started_perf=started_perf,
        )

        notify_super_admins_backup_failed(job_log)

        return job_log


def cleanup_old_backup_files_with_log(days=15, triggered_by=None, celery_task_id=""):
    job_log = create_backup_job_log(
        job_type=BackupJobType.FULL,
        triggered_by=triggered_by,
        celery_task_id=celery_task_id,
        metadata={
            "cleanup_days": days,
            "action": "cleanup",
        },
    )

    started_perf = time.perf_counter()

    try:
        deleted_count = delete_old_backups(days=days)

        job_log.status = BackupJobStatus.CLEANED
        job_log.completed_at = timezone.now()
        job_log.duration_ms = round((time.perf_counter() - started_perf) * 1000)
        job_log.metadata = {
            **(job_log.metadata or {}),
            "deleted_count": deleted_count,
        }
        job_log.save(
            update_fields=[
                "status",
                "completed_at",
                "duration_ms",
                "metadata",
            ]
        )

        return job_log

    except Exception as exc:
        job_log = mark_backup_job_failed(
            job_log=job_log,
            exc=exc,
            started_perf=started_perf,
        )

        notify_super_admins_backup_failed(job_log)

        return job_log


def get_recent_backup_job_logs(limit=20):
    return (
        BackupJobLog.objects.select_related("triggered_by")
        .order_by("-started_at")[:limit]
    )


def get_backup_job_stats():
    total = BackupJobLog.objects.count()
    success = BackupJobLog.objects.filter(status=BackupJobStatus.SUCCESS).count()
    failed = BackupJobLog.objects.filter(status=BackupJobStatus.FAILED).count()
    cleaned = BackupJobLog.objects.filter(status=BackupJobStatus.CLEANED).count()
    started = BackupJobLog.objects.filter(status=BackupJobStatus.STARTED).count()

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "cleaned": cleaned,
        "started": started,
    }