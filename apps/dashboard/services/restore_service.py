import json
import shutil
import traceback
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from apps.dashboard.models import (
    RestoreFileType,
    RestoreJobLog,
    RestoreJobStatus,
)


def detect_restore_file_type(file_path):
    file_path = Path(file_path)
    name = file_path.name.lower()

    if name.endswith(".json"):
        return RestoreFileType.DATABASE_JSON

    if name.endswith(".sql"):
        return RestoreFileType.DATABASE_SQL

    if name.endswith(".zip"):
        try:
            with zipfile.ZipFile(file_path, "r") as zip_file:
                names = zip_file.namelist()

                has_db = any(
                    item.endswith(".json") or item.endswith(".sql")
                    for item in names
                )

                has_media = any(
                    not item.endswith(".json") and not item.endswith(".sql")
                    for item in names
                )

                if has_db and has_media:
                    return RestoreFileType.FULL_ZIP

                return RestoreFileType.MEDIA_ZIP
        except Exception:
            return RestoreFileType.UNKNOWN

    return RestoreFileType.UNKNOWN


def update_file_size(restore_job):
    file_path = Path(restore_job.uploaded_file.path)

    restore_job.file_size_mb = round(
        file_path.stat().st_size / (1024 * 1024),
        2,
    )

    restore_job.save(
        update_fields=[
            "file_size_mb",
        ]
    )

    return restore_job


def validate_json_dump(file_path):
    with open(file_path, "r", encoding="utf-8") as json_file:
        data = json.load(json_file)

    if not isinstance(data, list):
        raise ValueError("Django dumpdata JSON must be a list of objects.")

    model_counts = {}

    for item in data:
        model_name = item.get("model", "unknown")
        model_counts[model_name] = model_counts.get(model_name, 0) + 1

    return {
        "valid": True,
        "type": "database_json",
        "object_count": len(data),
        "model_count": len(model_counts),
        "models": model_counts,
    }


def validate_sql_dump(file_path):
    file_path = Path(file_path)
    size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)

    with open(file_path, "r", encoding="utf-8", errors="ignore") as sql_file:
        head = sql_file.read(5000)

    looks_like_pg_dump = (
        "PostgreSQL database dump" in head
        or "CREATE TABLE" in head
        or "COPY " in head
        or "INSERT INTO" in head
    )

    if not looks_like_pg_dump:
        raise ValueError("SQL file does not look like a valid database dump.")

    return {
        "valid": True,
        "type": "database_sql",
        "size_mb": size_mb,
        "restore_mode": "manual_psql_required",
    }


def preview_zip(file_path, limit=200):
    with zipfile.ZipFile(file_path, "r") as zip_file:
        infos = zip_file.infolist()

        file_entries = []
        total_size = 0

        for info in infos:
            if info.is_dir():
                continue

            total_size += info.file_size

            if len(file_entries) < limit:
                file_entries.append(
                    {
                        "name": info.filename,
                        "size_mb": round(info.file_size / (1024 * 1024), 2),
                    }
                )

        return {
            "valid": True,
            "file_count": len([info for info in infos if not info.is_dir()]),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "preview_limit": limit,
            "files": file_entries,
        }


def validate_restore_job(restore_job):
    try:
        update_file_size(restore_job)

        file_path = Path(restore_job.uploaded_file.path)

        restore_job.file_type = detect_restore_file_type(file_path)

        if restore_job.file_type == RestoreFileType.DATABASE_JSON:
            summary = validate_json_dump(file_path)

        elif restore_job.file_type == RestoreFileType.DATABASE_SQL:
            summary = validate_sql_dump(file_path)

        elif restore_job.file_type in [
            RestoreFileType.MEDIA_ZIP,
            RestoreFileType.FULL_ZIP,
        ]:
            summary = preview_zip(file_path)

        else:
            raise ValueError("Unknown or unsupported restore file type.")

        restore_job.status = RestoreJobStatus.VALIDATED
        restore_job.validation_summary = summary
        restore_job.validated_at = timezone.now()
        restore_job.error_message = ""
        restore_job.traceback_text = ""
        restore_job.save(
            update_fields=[
                "file_type",
                "status",
                "file_size_mb",
                "validation_summary",
                "validated_at",
                "error_message",
                "traceback_text",
            ]
        )

    except Exception as exc:
        restore_job.status = RestoreJobStatus.FAILED_VALIDATION
        restore_job.error_message = str(exc)
        restore_job.traceback_text = traceback.format_exc()
        restore_job.save(
            update_fields=[
                "status",
                "error_message",
                "traceback_text",
            ]
        )

    return restore_job


def perform_restore_dry_run(restore_job):
    try:
        file_path = Path(restore_job.uploaded_file.path)

        if restore_job.file_type == RestoreFileType.DATABASE_JSON:
            summary = validate_json_dump(file_path)
            summary["dry_run_note"] = (
                "JSON structure is valid. Restore command can be run manually with loaddata."
            )
            summary["manual_command"] = (
                f"python manage.py loaddata \"{file_path}\""
            )

        elif restore_job.file_type == RestoreFileType.DATABASE_SQL:
            summary = validate_sql_dump(file_path)
            summary["dry_run_note"] = (
                "SQL dump appears valid. Restore should be run manually using psql after maintenance-mode backup."
            )
            summary["manual_command"] = (
                f"psql -h <host> -p <port> -U <user> -d <database> -f \"{file_path}\""
            )

        elif restore_job.file_type in [
            RestoreFileType.MEDIA_ZIP,
            RestoreFileType.FULL_ZIP,
        ]:
            summary = preview_zip(file_path)
            summary["dry_run_note"] = (
                "ZIP can be read. Media files can be previewed before extraction."
            )

        else:
            raise ValueError("Unsupported restore file type.")

        restore_job.status = RestoreJobStatus.DRY_RUN
        restore_job.dry_run_summary = summary
        restore_job.media_preview = summary if "files" in summary else {}
        restore_job.dry_run_at = timezone.now()
        restore_job.save(
            update_fields=[
                "status",
                "dry_run_summary",
                "media_preview",
                "dry_run_at",
            ]
        )

    except Exception as exc:
        restore_job.status = RestoreJobStatus.FAILED
        restore_job.error_message = str(exc)
        restore_job.traceback_text = traceback.format_exc()
        restore_job.save(
            update_fields=[
                "status",
                "error_message",
                "traceback_text",
            ]
        )

    return restore_job


def confirm_restore_job(restore_job, confirmation_text):
    restore_job.confirmation_text = confirmation_text
    restore_job.is_confirmed = True
    restore_job.status = RestoreJobStatus.READY_FOR_RESTORE
    restore_job.confirmed_at = timezone.now()
    restore_job.save(
        update_fields=[
            "confirmation_text",
            "is_confirmed",
            "status",
            "confirmed_at",
        ]
    )

    return restore_job


def restore_media_zip(restore_job):
    if not restore_job.can_restore_media:
        raise ValueError("Restore job is not confirmed or not valid for media restore.")

    file_path = Path(restore_job.uploaded_file.path)
    media_root = Path(settings.MEDIA_ROOT)
    restore_target = media_root / "restored_media_preview"

    restore_target.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(file_path, "r") as zip_file:
        for member in zip_file.infolist():
            if member.is_dir():
                continue

            safe_name = Path(member.filename)

            if safe_name.is_absolute() or ".." in safe_name.parts:
                continue

            zip_file.extract(member, restore_target)

    restore_job.status = RestoreJobStatus.RESTORED
    restore_job.restored_at = timezone.now()
    restore_job.save(
        update_fields=[
            "status",
            "restored_at",
        ]
    )

    return restore_job


def get_recent_restore_jobs(limit=20):
    return (
        RestoreJobLog.objects.select_related("uploaded_by")
        .order_by("-created_at")[:limit]
    )


def notify_super_admins_restore_failed(restore_job):
    try:
        from django.contrib.auth import get_user_model

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
                title="Restore job failed",
                message=(
                    f"Restore validation/action failed for {restore_job.original_filename}. "
                    f"Reason: {restore_job.error_message}"
                ),
                notification_type=NotificationType.INFO,
                target_url="/dashboard/restore/",
                object_type="RestoreJobLog",
                object_id=restore_job.pk,
                send_email=True,
            )

    except Exception:
        pass