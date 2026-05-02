from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog


def can_view_audit_logs(user):
    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.AUDITOR,
    ]


def get_scoped_audit_logs(user):
    if user.is_superuser:
        return AuditLog.objects.select_related(
            "organization",
            "user",
        ).all()

    profile = getattr(user, "profile", None)

    if not profile or not profile.organization:
        return AuditLog.objects.none()

    return AuditLog.objects.select_related(
        "organization",
        "user",
    ).filter(
        organization=profile.organization,
    )


@login_required
def audit_log_list(request):
    if not can_view_audit_logs(request.user):
        messages.error(request, "You do not have permission to view audit logs.")
        return redirect("dashboard:home")

    logs = get_scoped_audit_logs(request.user)

    search = request.GET.get("q", "").strip()
    action = request.GET.get("action", "").strip()
    model_name = request.GET.get("model_name", "").strip()

    if search:
        logs = logs.filter(
            Q(message__icontains=search)
            | Q(model_name__icontains=search)
            | Q(object_id__icontains=search)
            | Q(user__username__icontains=search)
            | Q(user__email__icontains=search)
            | Q(user__full_name__icontains=search)
            | Q(organization__name__icontains=search)
            | Q(ip_address__icontains=search)
        )

    if action:
        logs = logs.filter(action=action)

    if model_name:
        logs = logs.filter(model_name__icontains=model_name)

    recent_logs_count = logs.count()

    return render(
        request,
        "audit/audit_log_list.html",
        {
            "page_title": "Audit Logs",
            "logs": logs[:300],
            "search": search,
            "selected_action": action,
            "model_name": model_name,
            "action_choices": AuditAction.choices,
            "recent_logs_count": recent_logs_count,
        },
    )


@login_required
def audit_log_detail(request, pk):
    if not can_view_audit_logs(request.user):
        messages.error(request, "You do not have permission to view audit logs.")
        return redirect("dashboard:home")

    audit_log = get_object_or_404(
        get_scoped_audit_logs(request.user),
        pk=pk,
    )

    return render(
        request,
        "audit/audit_log_detail.html",
        {
            "page_title": "Audit Log Detail",
            "audit_log": audit_log,
        },
    )