import shutil
import socket
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from django.conf import settings
from django.core.mail import get_connection
from django.db import connection
from django.utils import timezone


@dataclass
class HealthCheckResult:
    name: str
    status: str
    message: str
    details: dict
    checked_at: object
    response_time_ms: int = 0


STATUS_HEALTHY = "HEALTHY"
STATUS_WARNING = "WARNING"
STATUS_DOWN = "DOWN"
STATUS_UNKNOWN = "UNKNOWN"


def now():
    return timezone.now()


def build_result(name, status, message, details=None, start_time=None):
    response_time_ms = 0

    if start_time:
        response_time_ms = round((time.perf_counter() - start_time) * 1000)

    return HealthCheckResult(
        name=name,
        status=status,
        message=message,
        details=details or {},
        checked_at=now(),
        response_time_ms=response_time_ms,
    )


def check_database():
    start_time = time.perf_counter()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return build_result(
            name="Database",
            status=STATUS_HEALTHY,
            message="Database connection is healthy.",
            details={
                "engine": settings.DATABASES["default"].get("ENGINE", ""),
                "name": settings.DATABASES["default"].get("NAME", ""),
                "host": settings.DATABASES["default"].get("HOST", ""),
                "port": settings.DATABASES["default"].get("PORT", ""),
            },
            start_time=start_time,
        )

    except Exception as exc:
        return build_result(
            name="Database",
            status=STATUS_DOWN,
            message=str(exc),
            details={},
            start_time=start_time,
        )


def check_redis():
    start_time = time.perf_counter()

    redis_url = getattr(
        settings,
        "CELERY_BROKER_URL",
        getattr(settings, "REDIS_URL", ""),
    )

    if not redis_url:
        return build_result(
            name="Redis",
            status=STATUS_UNKNOWN,
            message="Redis URL is not configured.",
            details={},
            start_time=start_time,
        )

    try:
        import redis

        client = redis.from_url(
            redis_url,
            socket_connect_timeout=3,
            socket_timeout=3,
        )

        pong = client.ping()

        return build_result(
            name="Redis",
            status=STATUS_HEALTHY if pong else STATUS_WARNING,
            message="Redis broker is reachable.",
            details={
                "url": mask_url(redis_url),
                "ping": pong,
            },
            start_time=start_time,
        )

    except Exception as exc:
        return build_result(
            name="Redis",
            status=STATUS_DOWN,
            message=str(exc),
            details={
                "url": mask_url(redis_url),
            },
            start_time=start_time,
        )


def mask_url(url):
    if not url:
        return ""

    parsed = urlparse(url)

    if parsed.password:
        safe_netloc = parsed.netloc.replace(parsed.password, "********")
        return parsed._replace(netloc=safe_netloc).geturl()

    return url


def check_celery_worker():
    start_time = time.perf_counter()

    try:
        from config.celery import app

        inspector = app.control.inspect(timeout=3)

        ping_response = inspector.ping() or {}
        stats_response = inspector.stats() or {}

        if ping_response:
            return build_result(
                name="Celery Worker",
                status=STATUS_HEALTHY,
                message="Celery worker is online.",
                details={
                    "workers": list(ping_response.keys()),
                    "worker_count": len(ping_response),
                    "stats_available": bool(stats_response),
                },
                start_time=start_time,
            )

        return build_result(
            name="Celery Worker",
            status=STATUS_DOWN,
            message="No Celery workers responded. Start worker with: celery -A config worker -l info -P solo",
            details={},
            start_time=start_time,
        )

    except Exception as exc:
        return build_result(
            name="Celery Worker",
            status=STATUS_DOWN,
            message=str(exc),
            details={},
            start_time=start_time,
        )


def check_celery_beat():
    start_time = time.perf_counter()

    beat_schedule = getattr(settings, "CELERY_BEAT_SCHEDULE", {})

    try:
        from django_celery_beat.models import PeriodicTask

        enabled_tasks = PeriodicTask.objects.filter(enabled=True)
        latest_run = (
            enabled_tasks.exclude(last_run_at__isnull=True)
            .order_by("-last_run_at")
            .first()
        )

        details = {
            "settings_schedule_count": len(beat_schedule),
            "database_periodic_tasks": enabled_tasks.count(),
            "latest_database_task": latest_run.name if latest_run else "",
            "latest_database_task_run_at": latest_run.last_run_at if latest_run else None,
        }

        if beat_schedule or enabled_tasks.exists():
            return build_result(
                name="Celery Beat",
                status=STATUS_HEALTHY if latest_run else STATUS_WARNING,
                message=(
                    "Celery Beat schedule is configured."
                    if latest_run
                    else "Celery Beat schedule exists, but no database task run is recorded yet."
                ),
                details=details,
                start_time=start_time,
            )

        return build_result(
            name="Celery Beat",
            status=STATUS_WARNING,
            message="No Celery Beat schedule found.",
            details=details,
            start_time=start_time,
        )

    except Exception:
        if beat_schedule:
            return build_result(
                name="Celery Beat",
                status=STATUS_WARNING,
                message="CELERY_BEAT_SCHEDULE exists, but django-celery-beat runtime status is unavailable.",
                details={
                    "settings_schedule_count": len(beat_schedule),
                    "tasks": list(beat_schedule.keys()),
                },
                start_time=start_time,
            )

        return build_result(
            name="Celery Beat",
            status=STATUS_UNKNOWN,
            message="Celery Beat status could not be determined.",
            details={},
            start_time=start_time,
        )


def check_smtp():
    start_time = time.perf_counter()

    try:
        backend = getattr(settings, "EMAIL_BACKEND", "")
        host = getattr(settings, "EMAIL_HOST", "")
        port = getattr(settings, "EMAIL_PORT", "")
        username = getattr(settings, "EMAIL_HOST_USER", "")
        use_tls = getattr(settings, "EMAIL_USE_TLS", False)
        use_ssl = getattr(settings, "EMAIL_USE_SSL", False)

        if "console" in backend:
            return build_result(
                name="SMTP Email",
                status=STATUS_WARNING,
                message="Email backend is console backend. Emails will print to console only.",
                details={
                    "backend": backend,
                },
                start_time=start_time,
            )

        connection_obj = get_connection(timeout=5)
        connection_obj.open()
        connection_obj.close()

        return build_result(
            name="SMTP Email",
            status=STATUS_HEALTHY,
            message="SMTP connection opened successfully.",
            details={
                "backend": backend,
                "host": host,
                "port": port,
                "username": username,
                "use_tls": use_tls,
                "use_ssl": use_ssl,
            },
            start_time=start_time,
        )

    except Exception as exc:
        return build_result(
            name="SMTP Email",
            status=STATUS_DOWN,
            message=str(exc),
            details={
                "backend": getattr(settings, "EMAIL_BACKEND", ""),
                "host": getattr(settings, "EMAIL_HOST", ""),
                "port": getattr(settings, "EMAIL_PORT", ""),
                "username": getattr(settings, "EMAIL_HOST_USER", ""),
            },
            start_time=start_time,
        )


def check_disk_usage():
    start_time = time.perf_counter()

    try:
        base_dir = getattr(settings, "BASE_DIR", ".")
        usage = shutil.disk_usage(base_dir)

        total_gb = round(usage.total / (1024 ** 3), 2)
        used_gb = round(usage.used / (1024 ** 3), 2)
        free_gb = round(usage.free / (1024 ** 3), 2)
        used_percent = round((usage.used / usage.total) * 100, 2)

        if used_percent >= 90:
            status = STATUS_DOWN
            message = "Disk usage is critical."
        elif used_percent >= 75:
            status = STATUS_WARNING
            message = "Disk usage is high."
        else:
            status = STATUS_HEALTHY
            message = "Disk usage is normal."

        return build_result(
            name="Disk Usage",
            status=status,
            message=message,
            details={
                "path": str(base_dir),
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "used_percent": used_percent,
            },
            start_time=start_time,
        )

    except Exception as exc:
        return build_result(
            name="Disk Usage",
            status=STATUS_UNKNOWN,
            message=str(exc),
            details={},
            start_time=start_time,
        )


def get_scheduled_jobs():
    jobs = []

    beat_schedule = getattr(settings, "CELERY_BEAT_SCHEDULE", {})

    for name, config in beat_schedule.items():
        jobs.append(
            {
                "name": name,
                "task": config.get("task", ""),
                "schedule": str(config.get("schedule", "")),
                "source": "settings",
                "enabled": True,
                "last_run_at": None,
                "total_run_count": None,
            }
        )

    try:
        from django_celery_beat.models import PeriodicTask

        for task in PeriodicTask.objects.all().order_by("name"):
            jobs.append(
                {
                    "name": task.name,
                    "task": task.task,
                    "schedule": str(task.schedule),
                    "source": "database",
                    "enabled": task.enabled,
                    "last_run_at": task.last_run_at,
                    "total_run_count": task.total_run_count,
                }
            )

    except Exception:
        pass

    return jobs


def get_recent_notification_failures(limit=8):
    try:
        from apps.notifications.models import (
            NotificationDeliveryLog,
            NotificationDeliveryStatus,
        )

        return (
            NotificationDeliveryLog.objects.select_related("recipient")
            .filter(status=NotificationDeliveryStatus.FAILED)
            .order_by("-created_at")[:limit]
        )

    except Exception:
        return []


def get_system_health_summary():
    checks = [
        check_database(),
        check_redis(),
        check_celery_worker(),
        check_celery_beat(),
        check_smtp(),
        check_disk_usage(),
    ]

    down_count = len([item for item in checks if item.status == STATUS_DOWN])
    warning_count = len([item for item in checks if item.status == STATUS_WARNING])
    healthy_count = len([item for item in checks if item.status == STATUS_HEALTHY])

    if down_count:
        overall_status = STATUS_DOWN
        overall_message = "Some critical services are down."
    elif warning_count:
        overall_status = STATUS_WARNING
        overall_message = "System is running with warnings."
    else:
        overall_status = STATUS_HEALTHY
        overall_message = "All monitored services are healthy."

    return {
        "overall_status": overall_status,
        "overall_message": overall_message,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "down_count": down_count,
        "checks": checks,
        "scheduled_jobs": get_scheduled_jobs(),
        "recent_notification_failures": get_recent_notification_failures(),
        "checked_at": now(),
        "hostname": socket.gethostname(),
    }