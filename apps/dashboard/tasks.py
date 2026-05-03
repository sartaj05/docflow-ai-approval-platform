from celery import shared_task

from apps.dashboard.services.backup_export_service import (
    cleanup_old_backup_files_with_log,
    run_backup_job,
)


@shared_task(bind=True)
def scheduled_database_backup_task(self):
    job_log = run_backup_job(
        action="database",
        celery_task_id=self.request.id,
        metadata={
            "source": "celery",
            "schedule": "scheduled_database_backup_task",
        },
    )

    return {
        "job_log_id": job_log.pk,
        "status": job_log.status,
        "file_name": job_log.file_name,
    }


@shared_task(bind=True)
def scheduled_media_backup_task(self):
    job_log = run_backup_job(
        action="media",
        celery_task_id=self.request.id,
        metadata={
            "source": "celery",
            "schedule": "scheduled_media_backup_task",
        },
    )

    return {
        "job_log_id": job_log.pk,
        "status": job_log.status,
        "file_name": job_log.file_name,
    }


@shared_task(bind=True)
def scheduled_full_backup_task(self):
    job_log = run_backup_job(
        action="full",
        celery_task_id=self.request.id,
        metadata={
            "source": "celery",
            "schedule": "scheduled_full_backup_task",
        },
    )

    return {
        "job_log_id": job_log.pk,
        "status": job_log.status,
        "file_name": job_log.file_name,
    }


@shared_task(bind=True)
def scheduled_audit_export_task(self):
    job_log = run_backup_job(
        action="audit",
        celery_task_id=self.request.id,
        metadata={
            "source": "celery",
            "schedule": "scheduled_audit_export_task",
        },
    )

    return {
        "job_log_id": job_log.pk,
        "status": job_log.status,
        "file_name": job_log.file_name,
    }


@shared_task(bind=True)
def scheduled_notification_export_task(self):
    job_log = run_backup_job(
        action="notifications",
        celery_task_id=self.request.id,
        metadata={
            "source": "celery",
            "schedule": "scheduled_notification_export_task",
        },
    )

    return {
        "job_log_id": job_log.pk,
        "status": job_log.status,
        "file_name": job_log.file_name,
    }


@shared_task(bind=True)
def scheduled_backup_cleanup_task(self):
    job_log = cleanup_old_backup_files_with_log(
        days=15,
        celery_task_id=self.request.id,
    )

    return {
        "job_log_id": job_log.pk,
        "status": job_log.status,
        "metadata": job_log.metadata,
    }