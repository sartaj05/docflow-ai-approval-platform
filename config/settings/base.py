from pathlib import Path

from celery.schedules import crontab
from decouple import Csv, config


BASE_DIR = Path(__file__).resolve().parent.parent.parent


# ==============================
# SECURITY
# ==============================

SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-docflow-ai-local-secret-key",
)

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=Csv(),
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:8000,http://127.0.0.1:8000",
    cast=Csv(),
)


# ==============================
# APPLICATIONS
# ==============================

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "django_celery_beat",
    "widget_tweaks",
    "crispy_forms",
    "crispy_bootstrap5",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.organizations",
    "apps.departments",
    "apps.approvals",
    "apps.documents",
    "apps.audit",
    "apps.notifications",
    "apps.reports",
    "apps.search_app",
    "apps.dashboard",
    "apps.superadmin",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# ==============================
# MIDDLEWARE
# ==============================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.dashboard.middleware.MaintenanceModeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ==============================
# URL / WSGI / ASGI
# ==============================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"


# ==============================
# TEMPLATES
# ==============================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",

                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",

                "apps.notifications.context_processors.notification_counts",
            ],
        },
    },
]


# ==============================
# DATABASE
# ==============================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DATABASE_NAME", default="docflow_ai"),
        "USER": config("DATABASE_USER", default="postgres"),
        "PASSWORD": config("DATABASE_PASSWORD", default="postgres"),
        "HOST": config("DATABASE_HOST", default="localhost"),
        "PORT": config("DATABASE_PORT", default="5432"),
        "CONN_MAX_AGE": config("DATABASE_CONN_MAX_AGE", default=60, cast=int),
    }
}


# ==============================
# CUSTOM USER MODEL
# ==============================

AUTH_USER_MODEL = "accounts.User"


# ==============================
# PASSWORD VALIDATION
# ==============================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ==============================
# INTERNATIONALIZATION
# ==============================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True


# ==============================
# STATIC / MEDIA
# ==============================

STATIC_URL = config("STATIC_URL", default="/static/")

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = config("MEDIA_URL", default="/media/")

MEDIA_ROOT = BASE_DIR / "media"


STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"


# ==============================
# DEFAULT PRIMARY KEY
# ==============================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==============================
# AUTH REDIRECTS
# ==============================

LOGIN_URL = "/accounts/login/"

LOGIN_REDIRECT_URL = "/dashboard/"

LOGOUT_REDIRECT_URL = "/accounts/login/"


# ==============================
# SESSION / COOKIE SECURITY
# ==============================

SESSION_COOKIE_AGE = config(
    "SESSION_COOKIE_AGE",
    default=60 * 60 * 8,
    cast=int,
)

SESSION_EXPIRE_AT_BROWSER_CLOSE = config(
    "SESSION_EXPIRE_AT_BROWSER_CLOSE",
    default=False,
    cast=bool,
)

SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_HTTPONLY = False

SESSION_COOKIE_SECURE = config(
    "SESSION_COOKIE_SECURE",
    default=not DEBUG,
    cast=bool,
)

CSRF_COOKIE_SECURE = config(
    "CSRF_COOKIE_SECURE",
    default=not DEBUG,
    cast=bool,
)

SECURE_SSL_REDIRECT = config(
    "SECURE_SSL_REDIRECT",
    default=False,
    cast=bool,
)


# ==============================
# REST FRAMEWORK
# ==============================

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
}


# ==============================
# CRISPY FORMS
# ==============================

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"


# ==============================
# CELERY / REDIS
# ==============================

REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = config(
    "CELERY_BROKER_URL",
    default=REDIS_URL,
)

CELERY_RESULT_BACKEND = config(
    "CELERY_RESULT_BACKEND",
    default="redis://localhost:6379/1",
)

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_BEAT_SCHEDULE = {
    "send-daily-pending-approval-summary": {
        "task": "apps.notifications.tasks.send_daily_pending_approval_summary_task",
        "schedule": crontab(hour=9, minute=0),
    },

    "send-daily-notification-digest": {
        "task": "apps.notifications.tasks.send_daily_notification_digest_task",
        "schedule": crontab(hour=8, minute=30),
    },

    "send-weekly-notification-digest": {
        "task": "apps.notifications.tasks.send_weekly_notification_digest_task",
        "schedule": crontab(hour=9, minute=30, day_of_week="monday"),
    },

    "scheduled-database-backup": {
        "task": "apps.dashboard.tasks.scheduled_database_backup_task",
        "schedule": crontab(hour=23, minute=30),
    },

    "scheduled-media-backup": {
        "task": "apps.dashboard.tasks.scheduled_media_backup_task",
        "schedule": crontab(hour=23, minute=45, day_of_week="sunday"),
    },

    "scheduled-full-backup": {
        "task": "apps.dashboard.tasks.scheduled_full_backup_task",
        "schedule": crontab(hour=1, minute=0, day_of_week="monday"),
    },

    "scheduled-audit-export": {
        "task": "apps.dashboard.tasks.scheduled_audit_export_task",
        "schedule": crontab(hour=0, minute=20),
    },

    "scheduled-notification-export": {
        "task": "apps.dashboard.tasks.scheduled_notification_export_task",
        "schedule": crontab(hour=0, minute=40),
    },

    "scheduled-backup-cleanup": {
        "task": "apps.dashboard.tasks.scheduled_backup_cleanup_task",
        "schedule": crontab(hour=2, minute=0),
    },
}
# ==============================
# AI SERVICE
# ==============================

AI_SERVICE_URL = config(
    "AI_SERVICE_URL",
    default="http://localhost:8001",
)

AI_SERVICE_TIMEOUT = config(
    "AI_SERVICE_TIMEOUT",
    default=15,
    cast=int,
)


# ==============================
# EMAIL
# ==============================

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)

EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")

EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)

EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")

EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")

EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)

EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)

DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default=EMAIL_HOST_USER or "noreply@docflowai.local",
)

SERVER_EMAIL = DEFAULT_FROM_EMAIL

EMAIL_TIMEOUT = config("EMAIL_TIMEOUT", default=15, cast=int)


# ==============================
# EMAIL NOTIFICATION SETTINGS
# ==============================

ENABLE_EMAIL_NOTIFICATIONS = config(
    "ENABLE_EMAIL_NOTIFICATIONS",
    default=True,
    cast=bool,
)

SEND_EMAIL_ASYNC = config(
    "SEND_EMAIL_ASYNC",
    default=False,
    cast=bool,
)

DOCFLOW_APP_URL = config(
    "DOCFLOW_APP_URL",
    default="http://127.0.0.1:8000",
)


# ==============================
# FILE UPLOAD SECURITY
# ==============================

MAX_UPLOAD_SIZE = 10 * 1024 * 1024

DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE

FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE

ALLOWED_DOCUMENT_EXTENSIONS = [
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".doc",
    ".docx",
]


# ==============================
# LOGGING
# ==============================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": config("DJANGO_LOG_LEVEL", default="INFO"),
        },
        "apps": {
            "handlers": ["console"],
            "level": config("APP_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": config("CELERY_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}

# ==============================
# OCR SETTINGS
# ==============================

OCR_ENABLED = config(
    "OCR_ENABLED",
    default=True,
    cast=bool,
)

TESSERACT_CMD = config(
    "TESSERACT_CMD",
    default=r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)

OCR_LANGUAGE = config(
    "OCR_LANGUAGE",
    default="eng",
)

OCR_MIN_CONFIDENCE = config(
    "OCR_MIN_CONFIDENCE",
    default=60,
    cast=int,
)

OCR_PDF_MAX_PAGES = config(
    "OCR_PDF_MAX_PAGES",
    default=5,
    cast=int,
)

POPPLER_PATH = config(
    "POPPLER_PATH",
    default="",
)