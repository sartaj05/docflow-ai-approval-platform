import os
import shutil
import socket
import time
from pathlib import Path

from django.conf import settings
from django.core.mail import get_connection
from django.db import connection
from django.urls import reverse
from django.utils import timezone


CHECK_PASS = "PASS"
CHECK_WARNING = "WARNING"
CHECK_FAIL = "FAIL"
CHECK_INFO = "INFO"


def make_check(
    key,
    title,
    status,
    message,
    recommendation="",
    details=None,
):
    return {
        "key": key,
        "title": title,
        "status": status,
        "message": message,
        "recommendation": recommendation,
        "details": details or {},
    }


def env_bool(name, default=None):
    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in ["1", "true", "yes", "on"]


def check_debug_setting():
    if settings.DEBUG:
        return make_check(
            key="debug",
            title="DEBUG Mode",
            status=CHECK_FAIL,
            message="DEBUG is enabled.",
            recommendation="Set DEBUG=False in production.",
            details={
                "DEBUG": settings.DEBUG,
            },
        )

    return make_check(
        key="debug",
        title="DEBUG Mode",
        status=CHECK_PASS,
        message="DEBUG is disabled.",
        details={
            "DEBUG": settings.DEBUG,
        },
    )


def check_secret_key():
    secret_key = getattr(settings, "SECRET_KEY", "")

    weak_indicators = [
        "django-insecure",
        "change-me",
        "secret",
        "local",
        "dev",
    ]

    if not secret_key:
        return make_check(
            key="secret_key",
            title="SECRET_KEY",
            status=CHECK_FAIL,
            message="SECRET_KEY is missing.",
            recommendation="Set a strong SECRET_KEY in environment variables.",
        )

    if any(item in secret_key.lower() for item in weak_indicators):
        return make_check(
            key="secret_key",
            title="SECRET_KEY",
            status=CHECK_FAIL,
            message="SECRET_KEY looks like a development key.",
            recommendation="Generate and configure a strong production SECRET_KEY.",
        )

    if len(secret_key) < 40:
        return make_check(
            key="secret_key",
            title="SECRET_KEY",
            status=CHECK_WARNING,
            message="SECRET_KEY is shorter than recommended.",
            recommendation="Use a long random key of at least 50 characters.",
        )

    return make_check(
        key="secret_key",
        title="SECRET_KEY",
        status=CHECK_PASS,
        message="SECRET_KEY appears configured.",
    )


def check_allowed_hosts():
    allowed_hosts = list(getattr(settings, "ALLOWED_HOSTS", []))

    if not allowed_hosts:
        return make_check(
            key="allowed_hosts",
            title="ALLOWED_HOSTS",
            status=CHECK_FAIL,
            message="ALLOWED_HOSTS is empty.",
            recommendation="Add your production domain/IP to ALLOWED_HOSTS.",
            details={
                "ALLOWED_HOSTS": allowed_hosts,
            },
        )

    if "*" in allowed_hosts:
        return make_check(
            key="allowed_hosts",
            title="ALLOWED_HOSTS",
            status=CHECK_FAIL,
            message="ALLOWED_HOSTS contains '*'.",
            recommendation="Remove wildcard host and use exact domains.",
            details={
                "ALLOWED_HOSTS": allowed_hosts,
            },
        )

    localhost_values = {"localhost", "127.0.0.1", "[::1]"}

    if set(allowed_hosts).issubset(localhost_values):
        return make_check(
            key="allowed_hosts",
            title="ALLOWED_HOSTS",
            status=CHECK_WARNING,
            message="ALLOWED_HOSTS only contains local development hosts.",
            recommendation="Add your production domain before deployment.",
            details={
                "ALLOWED_HOSTS": allowed_hosts,
            },
        )

    return make_check(
        key="allowed_hosts",
        title="ALLOWED_HOSTS",
        status=CHECK_PASS,
        message="ALLOWED_HOSTS is configured.",
        details={
            "ALLOWED_HOSTS": allowed_hosts,
        },
    )


def check_csrf_trusted_origins():
    origins = list(getattr(settings, "CSRF_TRUSTED_ORIGINS", []))

    if not origins:
        return make_check(
            key="csrf",
            title="CSRF Trusted Origins",
            status=CHECK_WARNING,
            message="CSRF_TRUSTED_ORIGINS is empty.",
            recommendation="Add HTTPS production origin, for example https://your-domain.com.",
        )

    insecure = [
        origin for origin in origins
        if origin.startswith("http://") and "localhost" not in origin and "127.0.0.1" not in origin
    ]

    if insecure:
        return make_check(
            key="csrf",
            title="CSRF Trusted Origins",
            status=CHECK_WARNING,
            message="Some CSRF trusted origins use plain HTTP.",
            recommendation="Use HTTPS origins in production.",
            details={
                "insecure_origins": insecure,
                "origins": origins,
            },
        )

    return make_check(
        key="csrf",
        title="CSRF Trusted Origins",
        status=CHECK_PASS,
        message="CSRF_TRUSTED_ORIGINS is configured.",
        details={
            "origins": origins,
        },
    )


def check_cookie_security():
    session_secure = getattr(settings, "SESSION_COOKIE_SECURE", False)
    csrf_secure = getattr(settings, "CSRF_COOKIE_SECURE", False)

    if not session_secure or not csrf_secure:
        return make_check(
            key="cookies",
            title="Secure Cookies",
            status=CHECK_WARNING,
            message="SESSION_COOKIE_SECURE or CSRF_COOKIE_SECURE is disabled.",
            recommendation="Enable secure cookies behind HTTPS in production.",
            details={
                "SESSION_COOKIE_SECURE": session_secure,
                "CSRF_COOKIE_SECURE": csrf_secure,
            },
        )

    return make_check(
        key="cookies",
        title="Secure Cookies",
        status=CHECK_PASS,
        message="Secure cookies are enabled.",
        details={
            "SESSION_COOKIE_SECURE": session_secure,
            "CSRF_COOKIE_SECURE": csrf_secure,
        },
    )


def check_ssl_redirect():
    secure_ssl_redirect = getattr(settings, "SECURE_SSL_REDIRECT", False)

    if not secure_ssl_redirect:
        return make_check(
            key="ssl_redirect",
            title="SSL Redirect",
            status=CHECK_WARNING,
            message="SECURE_SSL_REDIRECT is disabled.",
            recommendation="Enable SECURE_SSL_REDIRECT=True in production behind HTTPS.",
            details={
                "SECURE_SSL_REDIRECT": secure_ssl_redirect,
            },
        )

    return make_check(
        key="ssl_redirect",
        title="SSL Redirect",
        status=CHECK_PASS,
        message="SSL redirect is enabled.",
        details={
            "SECURE_SSL_REDIRECT": secure_ssl_redirect,
        },
    )


def check_database_connection():
    start = time.perf_counter()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return make_check(
            key="database",
            title="Database Connection",
            status=CHECK_PASS,
            message="Database connection is working.",
            details={
                "response_time_ms": round((time.perf_counter() - start) * 1000),
                "engine": settings.DATABASES["default"].get("ENGINE", ""),
                "name": settings.DATABASES["default"].get("NAME", ""),
                "host": settings.DATABASES["default"].get("HOST", ""),
                "port": settings.DATABASES["default"].get("PORT", ""),
            },
        )

    except Exception as exc:
        return make_check(
            key="database",
            title="Database Connection",
            status=CHECK_FAIL,
            message=str(exc),
            recommendation="Fix database credentials, host, port, and migrations.",
        )


def check_redis_connection():
    redis_url = getattr(settings, "CELERY_BROKER_URL", "") or getattr(settings, "REDIS_URL", "")

    if not redis_url:
        return make_check(
            key="redis",
            title="Redis Connection",
            status=CHECK_FAIL,
            message="Redis/Celery broker URL is missing.",
            recommendation="Set REDIS_URL or CELERY_BROKER_URL.",
        )

    try:
        import redis

        client = redis.from_url(
            redis_url,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        client.ping()

        return make_check(
            key="redis",
            title="Redis Connection",
            status=CHECK_PASS,
            message="Redis is reachable.",
            details={
                "broker_url_configured": True,
            },
        )

    except Exception as exc:
        return make_check(
            key="redis",
            title="Redis Connection",
            status=CHECK_FAIL,
            message=str(exc),
            recommendation="Start Redis and verify CELERY_BROKER_URL.",
        )


def check_celery_worker():
    try:
        from config.celery import app

        inspector = app.control.inspect(timeout=3)
        response = inspector.ping() or {}

        if not response:
            return make_check(
                key="celery_worker",
                title="Celery Worker",
                status=CHECK_FAIL,
                message="No Celery worker responded.",
                recommendation="Start worker: celery -A config worker -l info -P solo",
            )

        return make_check(
            key="celery_worker",
            title="Celery Worker",
            status=CHECK_PASS,
            message="Celery worker is online.",
            details={
                "workers": list(response.keys()),
                "worker_count": len(response),
            },
        )

    except Exception as exc:
        return make_check(
            key="celery_worker",
            title="Celery Worker",
            status=CHECK_FAIL,
            message=str(exc),
            recommendation="Verify Celery app and Redis broker.",
        )


def check_celery_beat_schedule():
    schedule = getattr(settings, "CELERY_BEAT_SCHEDULE", {})

    if not schedule:
        return make_check(
            key="celery_beat",
            title="Celery Beat Schedule",
            status=CHECK_WARNING,
            message="No CELERY_BEAT_SCHEDULE entries found.",
            recommendation="Configure scheduled digest, SLA, and backup tasks.",
        )

    required_tasks = [
        "apps.notifications.tasks.send_daily_notification_digest_task",
        "apps.notifications.tasks.send_weekly_notification_digest_task",
        "apps.dashboard.tasks.scheduled_database_backup_task",
        "apps.dashboard.tasks.scheduled_backup_cleanup_task",
    ]

    configured_tasks = [
        item.get("task", "")
        for item in schedule.values()
    ]

    missing = [
        task for task in required_tasks
        if task not in configured_tasks
    ]

    if missing:
        return make_check(
            key="celery_beat",
            title="Celery Beat Schedule",
            status=CHECK_WARNING,
            message="Some recommended scheduled tasks are missing.",
            recommendation="Add missing Celery Beat scheduled jobs.",
            details={
                "missing_tasks": missing,
                "configured_count": len(schedule),
            },
        )

    return make_check(
        key="celery_beat",
        title="Celery Beat Schedule",
        status=CHECK_PASS,
        message="Celery Beat schedule contains required production jobs.",
        details={
            "configured_count": len(schedule),
        },
    )


def check_smtp_connection():
    try:
        backend = getattr(settings, "EMAIL_BACKEND", "")
        host = getattr(settings, "EMAIL_HOST", "")
        username = getattr(settings, "EMAIL_HOST_USER", "")

        if "console" in backend:
            return make_check(
                key="smtp",
                title="SMTP Email",
                status=CHECK_WARNING,
                message="Console email backend is active.",
                recommendation="Use SMTP email backend in production.",
                details={
                    "EMAIL_BACKEND": backend,
                },
            )

        if not host:
            return make_check(
                key="smtp",
                title="SMTP Email",
                status=CHECK_FAIL,
                message="EMAIL_HOST is missing.",
                recommendation="Configure SMTP host, port, username, and password.",
            )

        connection_obj = get_connection(timeout=5)
        connection_obj.open()
        connection_obj.close()

        return make_check(
            key="smtp",
            title="SMTP Email",
            status=CHECK_PASS,
            message="SMTP connection opened successfully.",
            details={
                "EMAIL_BACKEND": backend,
                "EMAIL_HOST": host,
                "EMAIL_PORT": getattr(settings, "EMAIL_PORT", ""),
                "EMAIL_HOST_USER": username,
            },
        )

    except Exception as exc:
        return make_check(
            key="smtp",
            title="SMTP Email",
            status=CHECK_FAIL,
            message=str(exc),
            recommendation="Verify SMTP credentials, app password, TLS/SSL, and firewall.",
        )


def check_staticfiles():
    static_root = Path(getattr(settings, "STATIC_ROOT", ""))

    if not static_root:
        return make_check(
            key="staticfiles",
            title="Static Files",
            status=CHECK_WARNING,
            message="STATIC_ROOT is not configured.",
            recommendation="Configure STATIC_ROOT and run collectstatic.",
        )

    if not static_root.exists():
        return make_check(
            key="staticfiles",
            title="Static Files",
            status=CHECK_WARNING,
            message="STATIC_ROOT folder does not exist.",
            recommendation="Run python manage.py collectstatic.",
            details={
                "STATIC_ROOT": str(static_root),
            },
        )

    file_count = sum(1 for item in static_root.rglob("*") if item.is_file())

    if file_count == 0:
        return make_check(
            key="staticfiles",
            title="Static Files",
            status=CHECK_WARNING,
            message="STATIC_ROOT exists but has no files.",
            recommendation="Run python manage.py collectstatic.",
            details={
                "STATIC_ROOT": str(static_root),
            },
        )

    return make_check(
        key="staticfiles",
        title="Static Files",
        status=CHECK_PASS,
        message="Static files appear collected.",
        details={
            "STATIC_ROOT": str(static_root),
            "file_count": file_count,
        },
    )


def check_media_root():
    media_root = Path(getattr(settings, "MEDIA_ROOT", ""))

    if not media_root:
        return make_check(
            key="media",
            title="Media Root",
            status=CHECK_WARNING,
            message="MEDIA_ROOT is not configured.",
            recommendation="Configure MEDIA_ROOT for uploads.",
        )

    if not media_root.exists():
        return make_check(
            key="media",
            title="Media Root",
            status=CHECK_WARNING,
            message="MEDIA_ROOT folder does not exist.",
            recommendation="Create media directory and check permissions.",
            details={
                "MEDIA_ROOT": str(media_root),
            },
        )

    writable_test_file = media_root / ".write_test"

    try:
        writable_test_file.write_text("ok", encoding="utf-8")
        writable_test_file.unlink(missing_ok=True)

        return make_check(
            key="media",
            title="Media Root",
            status=CHECK_PASS,
            message="MEDIA_ROOT exists and is writable.",
            details={
                "MEDIA_ROOT": str(media_root),
            },
        )

    except Exception as exc:
        return make_check(
            key="media",
            title="Media Root",
            status=CHECK_FAIL,
            message=str(exc),
            recommendation="Fix media directory permissions.",
        )


def check_backup_system():
    try:
        from apps.dashboard.services.backup_export_service import get_backup_root

        backup_root = get_backup_root()

        if not backup_root.exists():
            return make_check(
                key="backup",
                title="Backup Directory",
                status=CHECK_FAIL,
                message="Backup directory could not be created.",
                recommendation="Check MEDIA_ROOT permissions.",
            )

        test_file = backup_root / ".backup_write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)

        return make_check(
            key="backup",
            title="Backup Directory",
            status=CHECK_PASS,
            message="Backup directory exists and is writable.",
            details={
                "backup_root": str(backup_root),
            },
        )

    except Exception as exc:
        return make_check(
            key="backup",
            title="Backup Directory",
            status=CHECK_FAIL,
            message=str(exc),
            recommendation="Fix backup directory path and permissions.",
        )


def check_disk_usage():
    try:
        usage = shutil.disk_usage(settings.BASE_DIR)
        used_percent = round((usage.used / usage.total) * 100, 2)

        if used_percent >= 90:
            status = CHECK_FAIL
            message = "Disk usage is critical."
            recommendation = "Free disk space or increase storage before deployment."
        elif used_percent >= 75:
            status = CHECK_WARNING
            message = "Disk usage is high."
            recommendation = "Review backup/media storage before launch."
        else:
            status = CHECK_PASS
            message = "Disk usage is acceptable."
            recommendation = ""

        return make_check(
            key="disk",
            title="Disk Usage",
            status=status,
            message=message,
            recommendation=recommendation,
            details={
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "used_percent": used_percent,
            },
        )

    except Exception as exc:
        return make_check(
            key="disk",
            title="Disk Usage",
            status=CHECK_WARNING,
            message=str(exc),
            recommendation="Check disk manually.",
        )


def check_maintenance_mode():
    try:
        from apps.dashboard.models import MaintenanceMode

        maintenance = MaintenanceMode.get_config()

        if maintenance.is_enabled:
            return make_check(
                key="maintenance",
                title="Maintenance Mode",
                status=CHECK_WARNING,
                message="Maintenance mode is currently enabled.",
                recommendation="Disable maintenance mode before public launch unless intentionally deploying a maintenance page.",
                details={
                    "restore_safe_lock": maintenance.restore_safe_lock,
                },
            )

        return make_check(
            key="maintenance",
            title="Maintenance Mode",
            status=CHECK_PASS,
            message="Maintenance mode is disabled.",
        )

    except Exception as exc:
        return make_check(
            key="maintenance",
            title="Maintenance Mode",
            status=CHECK_WARNING,
            message=str(exc),
            recommendation="Run migrations for dashboard app.",
        )


def check_recent_backup_success():
    try:
        from apps.dashboard.models import BackupJobLog, BackupJobStatus

        latest_success = (
            BackupJobLog.objects.filter(status=BackupJobStatus.SUCCESS)
            .order_by("-completed_at")
            .first()
        )

        if not latest_success:
            return make_check(
                key="recent_backup",
                title="Recent Backup",
                status=CHECK_WARNING,
                message="No successful backup job found.",
                recommendation="Run a manual full backup before deployment.",
            )

        return make_check(
            key="recent_backup",
            title="Recent Backup",
            status=CHECK_PASS,
            message="A successful backup exists.",
            details={
                "file_name": latest_success.file_name,
                "completed_at": latest_success.completed_at,
                "file_size_mb": str(latest_success.file_size_mb),
            },
        )

    except Exception as exc:
        return make_check(
            key="recent_backup",
            title="Recent Backup",
            status=CHECK_WARNING,
            message=str(exc),
            recommendation="Run migrations and test backup module.",
        )


def get_launch_checklist():
    return [
        {
            "group": "Environment",
            "items": [
                "Set DEBUG=False.",
                "Use strong SECRET_KEY from environment variable.",
                "Configure production ALLOWED_HOSTS.",
                "Configure CSRF_TRUSTED_ORIGINS with HTTPS domain.",
                "Set TIME_ZONE correctly.",
            ],
        },
        {
            "group": "Security",
            "items": [
                "Enable HTTPS in reverse proxy.",
                "Enable SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE.",
                "Review admin user accounts.",
                "Disable test/demo users.",
                "Run python manage.py check --deploy.",
            ],
        },
        {
            "group": "Services",
            "items": [
                "Database is reachable.",
                "Redis is running.",
                "Celery worker is running.",
                "Celery Beat is running.",
                "SMTP email is tested.",
            ],
        },
        {
            "group": "Files",
            "items": [
                "Run collectstatic.",
                "Verify media directory permissions.",
                "Verify backup directory permissions.",
                "Create full backup before launch.",
            ],
        },
        {
            "group": "Operational",
            "items": [
                "Check System Health dashboard.",
                "Check Delivery Monitor.",
                "Check Backup & Export dashboard.",
                "Disable Maintenance Mode.",
                "Document rollback plan.",
            ],
        },
    ]


def get_deployment_readiness_summary():
    checks = [
        check_debug_setting(),
        check_secret_key(),
        check_allowed_hosts(),
        check_csrf_trusted_origins(),
        check_cookie_security(),
        check_ssl_redirect(),
        check_database_connection(),
        check_redis_connection(),
        check_celery_worker(),
        check_celery_beat_schedule(),
        check_smtp_connection(),
        check_staticfiles(),
        check_media_root(),
        check_backup_system(),
        check_disk_usage(),
        check_maintenance_mode(),
        check_recent_backup_success(),
    ]

    pass_count = len([item for item in checks if item["status"] == CHECK_PASS])
    warning_count = len([item for item in checks if item["status"] == CHECK_WARNING])
    fail_count = len([item for item in checks if item["status"] == CHECK_FAIL])
    info_count = len([item for item in checks if item["status"] == CHECK_INFO])

    if fail_count:
        overall_status = CHECK_FAIL
        overall_message = "Deployment is not ready. Critical checks failed."
    elif warning_count:
        overall_status = CHECK_WARNING
        overall_message = "Deployment is almost ready, but warnings need review."
    else:
        overall_status = CHECK_PASS
        overall_message = "Deployment readiness checks passed."

    return {
        "overall_status": overall_status,
        "overall_message": overall_message,
        "pass_count": pass_count,
        "warning_count": warning_count,
        "fail_count": fail_count,
        "info_count": info_count,
        "checks": checks,
        "launch_checklist": get_launch_checklist(),
        "checked_at": timezone.now(),
        "hostname": socket.gethostname(),
    }