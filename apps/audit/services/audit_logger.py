from apps.audit.models import AuditLog


def get_client_ip(request):
    if not request:
        return None

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


def get_user_agent(request):
    if not request:
        return ""

    return request.META.get("HTTP_USER_AGENT", "")


def get_user_organization(user):
    if not user or not user.is_authenticated:
        return None

    if user.is_superuser:
        return None

    profile = getattr(user, "profile", None)

    if not profile:
        return None

    return profile.organization


def create_audit_log(
    *,
    request=None,
    user=None,
    organization=None,
    action,
    model_name,
    object_id="",
    message,
    extra_data=None,
):
    if request and not user:
        user = request.user if request.user.is_authenticated else None

    if request and not organization:
        organization = get_user_organization(user)

    return AuditLog.objects.create(
        organization=organization,
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else "",
        message=message,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_data=extra_data or {},
    )