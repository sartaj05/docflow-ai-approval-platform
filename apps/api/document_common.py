from apps.accounts.models import UserRole
from apps.api.permissions import scoped_requests
from apps.documents.models import DocumentAttachment


def get_visible_attachment(user, attachment_pk):
    return (
        DocumentAttachment.objects.select_related("request", "request__organization")
        .filter(pk=attachment_pk, request__in=scoped_requests(user))
        .first()
    )


def can_view_version_history(user, attachment):
    if user.is_superuser:
        return True
    profile = getattr(user, "profile", None)
    if not profile or profile.organization_id != attachment.request.organization_id:
        return False
    return attachment.request.created_by_id == user.pk or profile.role in {
        UserRole.ORG_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.APPROVER, UserRole.AUDITOR,
    }


def can_correct_document_text(user, attachment):
    if user.is_superuser:
        return False
    profile = getattr(user, "profile", None)
    if not profile or profile.organization_id != attachment.request.organization_id:
        return False
    return attachment.request.created_by_id == user.pk or profile.role in {
        UserRole.ORG_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.AUDITOR,
    }


def can_restore_document_version(user, attachment):
    return bool(
        not user.is_superuser
        and attachment.request.status == "DRAFT"
        and attachment.request.created_by_id == user.pk
    )


def serialize_document_version(item):
    return {
        "id": item.pk,
        "version_number": item.version_number,
        "filename": item.original_filename,
        "file_type": item.file_type,
        "file_size": item.file_size,
        "extracted_text_length": len(item.extracted_text or ""),
        "risk_level": item.risk_level,
        "ai_processed": item.ai_processed,
        "change_note": item.change_note,
        "changed_by": item.replaced_by.display_name if item.replaced_by_id else None,
        "created_at": item.created_at.isoformat(),
    }
