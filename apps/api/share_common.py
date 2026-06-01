from apps.accounts.models import UserRole
from apps.api.permissions import scoped_requests
from apps.reports.models import RequestShareLink
from apps.reports.services.share_link_service import (
    build_absolute_share_archive_url,
    build_absolute_share_summary_url,
)


def get_share_request(user, request_pk):
    return scoped_requests(user).filter(pk=request_pk).first()


def can_manage_share_links(user, document_request):
    if user.is_superuser:
        return True
    profile = getattr(user, "profile", None)
    if not profile or profile.organization_id != document_request.organization_id:
        return False
    return profile.role in {
        UserRole.ORG_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.AUDITOR,
    } or document_request.created_by_id == user.pk


def serialize_share_link(item, request):
    return {
        "id": item.pk,
        "title": item.title,
        "summary_url": build_absolute_share_summary_url(request, item),
        "archive_url": (
            build_absolute_share_archive_url(request, item)
            if item.allow_archive_download else None
        ),
        "allow_summary_view": item.allow_summary_view,
        "allow_archive_download": item.allow_archive_download,
        "expires_at": item.expires_at.isoformat(),
        "is_active": item.is_active,
        "is_expired": item.is_expired,
        "is_valid": item.is_valid,
        "access_count": item.access_count,
        "last_accessed_at": item.last_accessed_at.isoformat() if item.last_accessed_at else None,
        "created_at": item.created_at.isoformat(),
    }


def find_public_share_link(token):
    return RequestShareLink.objects.select_related(
        "document_request", "document_request__organization", "document_request__department"
    ).filter(token=token).first()
