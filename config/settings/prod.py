from .base import *

DEBUG = False


# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True


# Production email backend
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"



from .base import *  # noqa


DEBUG = False

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

USE_X_FORWARDED_HOST = config(
    "USE_X_FORWARDED_HOST",
    default=True,
    cast=bool,
)

USE_X_FORWARDED_PORT = config(
    "USE_X_FORWARDED_PORT",
    default=True,
    cast=bool,
)

SESSION_COOKIE_SECURE = config(
    "SESSION_COOKIE_SECURE",
    default=True,
    cast=bool,
)

CSRF_COOKIE_SECURE = config(
    "CSRF_COOKIE_SECURE",
    default=True,
    cast=bool,
)

SECURE_SSL_REDIRECT = config(
    "SECURE_SSL_REDIRECT",
    default=False,
    cast=bool,
)

SECURE_HSTS_SECONDS = config(
    "SECURE_HSTS_SECONDS",
    default=0,
    cast=int,
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,
    cast=bool,
)

SECURE_HSTS_PRELOAD = config(
    "SECURE_HSTS_PRELOAD",
    default=False,
    cast=bool,
)

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

CSRF_COOKIE_SAMESITE = "Lax"

SESSION_COOKIE_SAMESITE = "Lax"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True