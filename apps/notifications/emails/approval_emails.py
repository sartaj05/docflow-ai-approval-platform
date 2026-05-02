from django.conf import settings
from django.urls import reverse

from apps.notifications.emails.email_service import build_absolute_url, send_template_email


def send_or_queue_email(task_path, *args, **kwargs):
    """
    If SEND_EMAIL_ASYNC=True, use Celery.
    Otherwise send immediately.
    """

    send_async = getattr(settings, "SEND_EMAIL_ASYNC", False)

    if send_async:
        from apps.notifications.tasks import (
            send_approval_assigned_email_task,
            send_daily_pending_approval_summary_task,
            send_request_approved_email_task,
            send_request_rejected_email_task,
        )

        task_map = {
            "approval_assigned": send_approval_assigned_email_task,
            "request_approved": send_request_approved_email_task,
            "request_rejected": send_request_rejected_email_task,
            "daily_pending_summary": send_daily_pending_approval_summary_task,
        }

        task = task_map.get(task_path)

        if task:
            task.delay(*args, **kwargs)
            return True

    return False


def send_approval_assigned_email(approval_step):
    document_request = approval_step.request
    recipient = approval_step.assigned_to

    if not recipient or not recipient.email:
        return False

    request_path = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    return send_template_email(
        subject=f"Approval Assigned: {document_request.request_number}",
        to_email=recipient.email,
        template_name="emails/approval_assigned.html",
        organization=document_request.organization,
        context={
            "recipient": recipient,
            "document_request": document_request,
            "approval_step": approval_step,
            "request_url": build_absolute_url(request_path),
            "app_url": build_absolute_url("/"),
        },
    )


def send_request_approved_email(document_request, actor=None):
    recipient = document_request.created_by

    if not recipient or not recipient.email:
        return False

    request_path = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    return send_template_email(
        subject=f"Request Approved: {document_request.request_number}",
        to_email=recipient.email,
        template_name="emails/request_approved.html",
        context={
            "recipient": recipient,
            "actor": actor,
            "document_request": document_request,
            "request_url": build_absolute_url(request_path),
            "app_url": build_absolute_url("/"),
        },
    )


def send_request_rejected_email(document_request, actor=None, comment=""):
    recipient = document_request.created_by

    if not recipient or not recipient.email:
        return False

    request_path = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    return send_template_email(
        subject=f"Request Rejected: {document_request.request_number}",
        to_email=recipient.email,
        template_name="emails/request_rejected.html",
        context={
            "recipient": recipient,
            "actor": actor,
            "comment": comment,
            "document_request": document_request,
            "request_url": build_absolute_url(request_path),
            "app_url": build_absolute_url("/"),
        },
    )


def send_daily_pending_approval_summary_email(user, pending_steps):
    if not user or not user.email:
        return False

    inbox_path = reverse("approvals:approval_inbox")

    return send_template_email(
        subject="Daily Pending Approval Summary",
        to_email=user.email,
        template_name="emails/daily_pending_summary.html",
        context={
            "recipient": user,
            "pending_steps": pending_steps,
            "pending_count": pending_steps.count() if hasattr(pending_steps, "count") else len(pending_steps),
            "inbox_url": build_absolute_url(inbox_path),
            "app_url": build_absolute_url("/"),
        },
    )