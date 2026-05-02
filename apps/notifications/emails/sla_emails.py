from django.urls import reverse

from apps.notifications.emails.email_service import build_absolute_url, send_template_email


def send_sla_reminder_email(approval_step):
    document_request = approval_step.request
    recipient = approval_step.assigned_to

    if not recipient or not recipient.email:
        return False

    request_path = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    return send_template_email(
        subject=f"Approval Due Soon: {document_request.request_number}",
        to_email=recipient.email,
        template_name="emails/sla_reminder.html",
        organization=document_request.organization,
        context={
            "recipient": recipient,
            "approval_step": approval_step,
            "document_request": document_request,
            "request_url": build_absolute_url(request_path),
            "app_url": build_absolute_url("/"),
        },
    )


def send_sla_overdue_email(approval_step):
    document_request = approval_step.request
    recipient = approval_step.assigned_to

    if not recipient or not recipient.email:
        return False

    request_path = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    return send_template_email(
        subject=f"Approval Overdue: {document_request.request_number}",
        to_email=recipient.email,
        template_name="emails/sla_overdue.html",
        organization=document_request.organization,
        context={
            "recipient": recipient,
            "approval_step": approval_step,
            "document_request": document_request,
            "request_url": build_absolute_url(request_path),
            "app_url": build_absolute_url("/"),
        },
    )


def send_sla_escalated_email(approval_step, escalation_user):
    document_request = approval_step.request

    if not escalation_user or not escalation_user.email:
        return False

    request_path = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    return send_template_email(
        subject=f"Approval Escalated: {document_request.request_number}",
        to_email=escalation_user.email,
        template_name="emails/sla_escalated.html",
        organization=document_request.organization,
        context={
            "recipient": escalation_user,
            "approval_step": approval_step,
            "document_request": document_request,
            "request_url": build_absolute_url(request_path),
            "app_url": build_absolute_url("/"),
        },
    )