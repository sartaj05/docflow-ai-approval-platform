from dataclasses import dataclass
from typing import Any

from django.utils import timezone


@dataclass
class ActivityItem:
    timestamp: Any
    activity_type: str
    icon: str
    title: str
    description: str
    actor: Any = None
    badge: str = "status-draft"
    target_url: str = ""
    meta: dict | None = None


def actor_name(user):
    if not user:
        return "System"

    return getattr(user, "display_name", None) or user.get_full_name() or user.username


def safe_local_time(value):
    if not value:
        return None

    try:
        return timezone.localtime(value)
    except Exception:
        return value


def collect_approval_action_items(document_request):
    items = []

    actions = (
        document_request.approval_actions.select_related(
            "action_by",
            "step",
        )
        .order_by("-created_at")
    )

    for action in actions:
        badge = "status-draft"
        icon = "🔔"

        if action.action_type == "SUBMITTED":
            badge = "status-submitted"
            icon = "📤"
        elif action.action_type == "APPROVED":
            badge = "status-approved"
            icon = "✅"
        elif action.action_type == "REJECTED":
            badge = "status-rejected"
            icon = "❌"
        elif action.action_type == "COMMENTED":
            badge = "status-review"
            icon = "💬"
        elif action.action_type == "CANCELLED":
            badge = "status-rejected"
            icon = "⛔"

        step_text = ""

        if action.step:
            step_text = f" — Step {action.step.step_order}"

        description = action.comment or "No comment provided."

        items.append(
            ActivityItem(
                timestamp=safe_local_time(action.created_at),
                activity_type="approval_action",
                icon=icon,
                title=f"{action.get_action_type_display()}{step_text}",
                description=description,
                actor=action.action_by,
                badge=badge,
                meta={
                    "old_status": action.old_status,
                    "new_status": action.new_status,
                },
            )
        )

    return items


def collect_discussion_items(document_request):
    items = []

    comments = (
        document_request.discussion_comments.select_related(
            "author",
            "parent",
        )
        .prefetch_related(
            "attachments",
            "mentioned_users",
        )
        .order_by("-created_at")
    )

    for comment in comments:
        if comment.parent_id:
            title = "Discussion reply added"
            icon = "↩️"
        else:
            title = "Discussion comment added"
            icon = "💬"

        if comment.is_deleted:
            description = "This comment was deleted."
            badge = "status-rejected"
        else:
            description = comment.message
            badge = "status-submitted"

        mentioned = [
            user.username
            for user in comment.mentioned_users.all()
        ]

        attachments = [
            attachment.original_filename
            for attachment in comment.attachments.all()
        ]

        items.append(
            ActivityItem(
                timestamp=safe_local_time(comment.created_at),
                activity_type="discussion",
                icon=icon,
                title=title,
                description=description,
                actor=comment.author,
                badge=badge,
                target_url="#discussion",
                meta={
                    "mentioned": mentioned,
                    "attachments": attachments,
                    "is_deleted": comment.is_deleted,
                },
            )
        )

    return items


def collect_document_items(document_request):
    items = []

    attachments = (
        document_request.attachments.select_related("uploaded_by")
        .order_by("-created_at")
    )

    for attachment in attachments:
        items.append(
            ActivityItem(
                timestamp=safe_local_time(attachment.created_at),
                activity_type="document",
                icon="📎",
                title="Document uploaded",
                description=attachment.original_filename,
                actor=attachment.uploaded_by,
                badge="status-submitted",
                target_url="",
                meta={
                    "file_type": getattr(attachment, "display_file_type", ""),
                    "file_size": getattr(attachment, "file_size_mb", ""),
                    "ai_processed": getattr(attachment, "ai_processed", False),
                    "risk_level": getattr(attachment, "risk_level", ""),
                },
            )
        )

        versions = getattr(attachment, "versions", None)

        if versions:
            for version in versions.select_related("replaced_by").order_by("-created_at"):
                items.append(
                    ActivityItem(
                        timestamp=safe_local_time(version.created_at),
                        activity_type="document_version",
                        icon="🗂️",
                        title=f"Document version v{version.version_number}",
                        description=version.original_filename,
                        actor=version.replaced_by,
                        badge="status-draft",
                        meta={
                            "change_note": getattr(version, "change_note", ""),
                            "is_current_snapshot": getattr(version, "is_current_snapshot", False),
                        },
                    )
                )

    return items


def collect_ai_processing_items(document_request):
    items = []

    attachments = document_request.attachments.all()

    for attachment in attachments:
        histories = getattr(attachment, "ai_processing_histories", None)

        if not histories:
            histories = getattr(attachment, "ai_history", None)

        if histories:
            for history in histories.select_related("processed_by").order_by("-created_at"):
                success = getattr(history, "success", False)

                items.append(
                    ActivityItem(
                        timestamp=safe_local_time(getattr(history, "created_at", None)),
                        activity_type="ai_processing",
                        icon="🤖",
                        title="AI analysis processed" if success else "AI analysis failed",
                        description=getattr(history, "error_message", "") or getattr(history, "risk_notes", "") or "AI analysis completed.",
                        actor=getattr(history, "processed_by", None),
                        badge="status-approved" if success else "status-rejected",
                        meta={
                            "attachment": attachment.original_filename,
                            "risk_level": getattr(history, "risk_level", ""),
                            "processing_time_ms": getattr(history, "processing_time_ms", ""),
                            "source_text_type": getattr(history, "source_text_type", ""),
                        },
                    )
                )

        if getattr(attachment, "ai_processed", False):
            items.append(
                ActivityItem(
                    timestamp=safe_local_time(getattr(attachment, "updated_at", None) or attachment.created_at),
                    activity_type="ai_summary",
                    icon="🧠",
                    title="AI summary saved",
                    description=getattr(attachment, "ai_summary", "") or "AI fields were saved on document.",
                    actor=None,
                    badge="status-approved",
                    meta={
                        "risk_level": getattr(attachment, "risk_level", ""),
                        "category": getattr(attachment, "ai_category", ""),
                    },
                )
            )

        ocr_status = getattr(attachment, "ocr_status", "")

        if ocr_status:
            items.append(
                ActivityItem(
                    timestamp=safe_local_time(getattr(attachment, "updated_at", None) or attachment.created_at),
                    activity_type="ocr",
                    icon="🔍",
                    title=f"OCR status: {ocr_status}",
                    description=getattr(attachment, "ocr_error", "") or "OCR processing information updated.",
                    actor=None,
                    badge="status-approved" if ocr_status in ["SUCCESS", "MANUAL_CORRECTED"] else "status-review",
                    meta={
                        "confidence": getattr(attachment, "ocr_confidence", ""),
                    },
                )
            )

    return items


def collect_reminder_items(document_request):
    items = []

    reminders = getattr(document_request, "reminders", None)

    if not reminders:
        return items

    reminders = reminders.select_related(
        "step",
        "sent_to",
        "sent_by",
    ).order_by("-created_at")

    for reminder in reminders:
        items.append(
            ActivityItem(
                timestamp=safe_local_time(reminder.created_at),
                activity_type="reminder",
                icon="🔔",
                title="Approval reminder sent",
                description=reminder.message or "Reminder sent to approver.",
                actor=reminder.sent_by,
                badge="status-review",
                meta={
                    "sent_to": actor_name(reminder.sent_to),
                    "step": reminder.step.step_order if reminder.step else "",
                },
            )
        )

    return items


def collect_certificate_items(document_request):
    items = []

    certificate = getattr(document_request, "certificate_signature", None)

    if not certificate:
        return items

    items.append(
        ActivityItem(
            timestamp=safe_local_time(certificate.signed_at),
            activity_type="certificate",
            icon="📜",
            title="Certificate generated",
            description=f"Verification code: {certificate.verification_code}",
            actor=certificate.signed_by,
            badge="status-approved" if certificate.is_valid else "status-rejected",
            meta={
                "verification_code": certificate.verification_code,
                "certificate_hash": certificate.certificate_hash,
                "is_valid": certificate.is_valid,
            },
        )
    )

    if certificate.invalidated_at:
        items.append(
            ActivityItem(
                timestamp=safe_local_time(certificate.invalidated_at),
                activity_type="certificate_invalidated",
                icon="⛔",
                title="Certificate invalidated",
                description=certificate.invalidation_reason or "Certificate was invalidated.",
                actor=certificate.invalidated_by,
                badge="status-rejected",
                meta={
                    "verification_code": certificate.verification_code,
                },
            )
        )

    return items


def collect_audit_log_items(document_request):
    items = []

    try:
        from apps.audit.models import AuditLog
    except Exception:
        return items

    audit_logs = (
        AuditLog.objects.select_related(
            "user",
            "organization",
        )
        .filter(
            organization=document_request.organization,
            object_id=str(document_request.pk),
        )
        .order_by("-created_at")
    )

    for log in audit_logs:
        items.append(
            ActivityItem(
                timestamp=safe_local_time(log.created_at),
                activity_type="audit",
                icon="🛡️",
                title=f"Audit: {getattr(log, 'get_action_display', lambda: log.action)()}",
                description=log.message,
                actor=log.user,
                badge="status-draft",
                meta={
                    "model_name": log.model_name,
                    "action": log.action,
                },
            )
        )

    return items


def build_request_activity_timeline(document_request, limit=100):
    items = []

    collectors = [
        collect_approval_action_items,
        collect_discussion_items,
        collect_document_items,
        collect_ai_processing_items,
        collect_reminder_items,
        collect_certificate_items,
        collect_audit_log_items,
    ]

    for collector in collectors:
        try:
            items.extend(collector(document_request))
        except Exception:
            continue

    items = [
        item
        for item in items
        if item.timestamp
    ]

    items.sort(
        key=lambda item: item.timestamp,
        reverse=True,
    )

    return items[:limit]