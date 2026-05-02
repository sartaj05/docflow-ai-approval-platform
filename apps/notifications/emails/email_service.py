import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags


logger = logging.getLogger(__name__)


def is_email_enabled():
    return getattr(settings, "ENABLE_EMAIL_NOTIFICATIONS", True)


def get_app_url():
    return getattr(settings, "DOCFLOW_APP_URL", "http://127.0.0.1:8000").rstrip("/")


def build_absolute_url(path):
    if not path:
        return get_app_url()

    if path.startswith("http://") or path.startswith("https://"):
        return path

    if not path.startswith("/"):
        path = f"/{path}"

    return f"{get_app_url()}{path}"


def get_email_connection_for_organization(organization=None):
    if organization and organization.use_custom_smtp:
        return get_connection(
            host=organization.smtp_host,
            port=organization.smtp_port,
            username=organization.smtp_username,
            password=organization.smtp_password,
            use_tls=organization.smtp_use_tls,
            use_ssl=organization.smtp_use_ssl,
            timeout=getattr(settings, "EMAIL_TIMEOUT", 15),
        )

    return None


def get_from_email_for_organization(organization=None):
    if organization and organization.use_custom_smtp and organization.smtp_from_email:
        from_name = organization.smtp_from_name or organization.name
        return f"{from_name} <{organization.smtp_from_email}>"

    return settings.DEFAULT_FROM_EMAIL


def send_template_email(
    *,
    subject,
    to_email,
    template_name,
    context=None,
    from_email=None,
    organization=None,
):
    if not is_email_enabled():
        logger.info("Email notification skipped because ENABLE_EMAIL_NOTIFICATIONS=False")
        return False

    if not to_email:
        logger.warning("Email notification skipped because recipient email is missing.")
        return False

    context = context or {}

    try:
        html_body = render_to_string(template_name, context)
        text_body = strip_tags(html_body)

        connection = get_email_connection_for_organization(organization)
        resolved_from_email = from_email or get_from_email_for_organization(organization)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=resolved_from_email,
            to=[to_email],
            connection=connection,
        )

        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)

        logger.info("Email sent successfully to %s with subject %s", to_email, subject)
        return True

    except Exception as exc:
        logger.exception("Failed to send email to %s: %s", to_email, exc)
        return False