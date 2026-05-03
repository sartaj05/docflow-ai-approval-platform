from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.decorators import role_required, super_admin_only
from apps.accounts.models import User, UserRole
from apps.accounts.utils import get_dashboard_url_for_user
from apps.approvals.models import (
    ApprovalStep,
    ApprovalStepStatus,
    DocumentRequest,
    RequestStatus,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from apps.dashboard.services.deployment_readiness_service import (
    get_deployment_readiness_summary,
)
from apps.dashboard.forms import MaintenanceModeForm
from apps.dashboard.models import MaintenanceMode
from apps.dashboard.forms import RestoreConfirmForm, RestoreUploadForm
from apps.dashboard.models import RestoreFileType, RestoreJobLog, RestoreJobStatus
from apps.dashboard.services.restore_service import (
    confirm_restore_job,
    get_recent_restore_jobs,
    notify_super_admins_restore_failed,
    perform_restore_dry_run,
    restore_media_zip,
    validate_restore_job,
)
from apps.dashboard.services.backup_export_service import (
    create_audit_log_export_csv,
    create_database_backup,
    create_full_backup_zip,
    create_media_backup_zip,
    create_notification_delivery_export_csv,
    create_request_export_csv,
    delete_old_backups,
    get_backup_dashboard_summary,
    get_backup_file_response,
    get_backup_job_stats,
    get_recent_backup_job_logs,
    run_backup_job,
)
from apps.audit.models import AuditLog
from apps.dashboard.services.analytics import build_dashboard_analytics_context
from apps.departments.models import Department
from apps.organizations.models import Organization
from apps.reports.models import ApprovalCertificateSignature
from apps.dashboard.services.system_health_service import get_system_health_summary
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.models import UserRole
from apps.dashboard.services.backup_export_service import (
    create_audit_log_export_csv,
    create_database_backup,
    create_full_backup_zip,
    create_media_backup_zip,
    create_notification_delivery_export_csv,
    create_request_export_csv,
    delete_old_backups,
    get_backup_dashboard_summary,
    get_backup_file_response,
)
from apps.accounts.models import UserRole
from apps.accounts.utils import get_dashboard_url_for_user
from apps.approvals.models import (
    ApprovalStep,
    ApprovalStepStatus,
    DocumentRequest,
    RequestStatus,
    RequestWatcher,
)
from apps.approvals.services.activity_timeline import build_request_activity_timeline
from apps.notifications.models import Notification
def get_profile(user):
    return getattr(user, "profile", None)
def can_view_backup_export(user):
    return user.is_superuser
def can_manage_maintenance_mode(user):
    return user.is_superuser
def can_view_system_health(user):
    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.AUDITOR,
    ]
def get_org_request_queryset(user):
    profile = get_profile(user)

    if not profile or not profile.organization:
        return DocumentRequest.objects.none()

    qs = DocumentRequest.objects.filter(
        organization=profile.organization,
    )

    if profile.role == UserRole.DEPARTMENT_HEAD:
        if profile.department:
            return qs.filter(department=profile.department)

        return DocumentRequest.objects.none()

    if profile.role == UserRole.STAFF:
        return qs.filter(created_by=user)

    return qs


def get_approver_step_queryset(user):
    if user.is_superuser:
        return ApprovalStep.objects.none()

    return ApprovalStep.objects.select_related(
        "request",
        "request__organization",
        "request__department",
        "request__created_by",
        "assigned_to",
    ).filter(
        assigned_to=user,
    )


def get_org_certificate_queryset(user):
    profile = get_profile(user)

    if not profile or not profile.organization:
        return ApprovalCertificateSignature.objects.none()

    return ApprovalCertificateSignature.objects.filter(
        document_request__organization=profile.organization,
    )


@login_required
def dashboard_home(request):
    return redirect(get_dashboard_url_for_user(request.user))


@super_admin_only
def super_admin_dashboard(request):
    total_organizations = Organization.objects.count()
    active_organizations = Organization.objects.filter(is_active=True).count()
    inactive_organizations = Organization.objects.filter(is_active=False).count()

    total_users = User.objects.count()
    organization_admins = User.objects.filter(
        profile__role=UserRole.ORG_ADMIN,
    ).count()

    total_departments = Department.objects.count()

    total_requests = DocumentRequest.objects.count()
    approved_requests = DocumentRequest.objects.filter(
        status=RequestStatus.APPROVED,
    ).count()
    pending_requests = DocumentRequest.objects.filter(
        status__in=[
            RequestStatus.SUBMITTED,
            RequestStatus.IN_REVIEW,
        ]
    ).count()

    total_certificates = ApprovalCertificateSignature.objects.count()
    valid_certificates = ApprovalCertificateSignature.objects.filter(
        is_valid=True,
    ).count()
    invalid_certificates = ApprovalCertificateSignature.objects.filter(
        is_valid=False,
    ).count()

    recent_organizations = Organization.objects.order_by("-created_at")[:8]

    recent_users = (
        User.objects.select_related("profile", "profile__organization")
        .order_by("-created_at")[:8]
    )

    recent_requests = (
        DocumentRequest.objects.select_related(
            "organization",
            "department",
            "created_by",
        )
        .order_by("-created_at")[:8]
    )

    recent_audit_logs = (
        AuditLog.objects.select_related("organization", "user")
        .order_by("-created_at")[:8]
    )

    context = {
        "page_title": "Super Admin Dashboard",
        "total_organizations": total_organizations,
        "active_organizations": active_organizations,
        "inactive_organizations": inactive_organizations,
        "total_users": total_users,
        "organization_admins": organization_admins,
        "total_departments": total_departments,
        "total_requests": total_requests,
        "approved_requests": approved_requests,
        "pending_requests": pending_requests,
        "total_certificates": total_certificates,
        "valid_certificates": valid_certificates,
        "invalid_certificates": invalid_certificates,
        "recent_organizations": recent_organizations,
        "recent_users": recent_users,
        "recent_requests": recent_requests,
        "recent_audit_logs": recent_audit_logs,
    }

    context.update(build_dashboard_analytics_context(request.user))

    return render(
        request,
        "dashboard/super_admin_dashboard.html",
        context,
    )


@role_required([UserRole.ORG_ADMIN])
def organization_admin_dashboard(request):
    qs = get_org_request_queryset(request.user)
    certificate_qs = get_org_certificate_queryset(request.user)

    context = {
        "page_title": "Organization Admin Dashboard",
        "total_requests": qs.count(),
        "draft_requests": qs.filter(status=RequestStatus.DRAFT).count(),
        "pending_requests": qs.filter(
            status__in=[
                RequestStatus.SUBMITTED,
                RequestStatus.IN_REVIEW,
            ]
        ).count(),
        "approved_requests": qs.filter(status=RequestStatus.APPROVED).count(),
        "rejected_requests": qs.filter(status=RequestStatus.REJECTED).count(),
        "certificate_count": certificate_qs.count(),
        "valid_certificate_count": certificate_qs.filter(is_valid=True).count(),
        "invalid_certificate_count": certificate_qs.filter(is_valid=False).count(),
        "recent_requests": qs.select_related("department", "created_by")[:8],
    }

    context.update(build_dashboard_analytics_context(request.user))

    return render(
        request,
        "dashboard/organization_admin_dashboard.html",
        context,
    )


@role_required([UserRole.DEPARTMENT_HEAD])
def department_head_dashboard(request):
    qs = get_org_request_queryset(request.user)

    context = {
        "page_title": "Department Head Dashboard",
        "total_requests": qs.count(),
        "pending_requests": qs.filter(
            status__in=[
                RequestStatus.SUBMITTED,
                RequestStatus.IN_REVIEW,
            ]
        ).count(),
        "approved_requests": qs.filter(status=RequestStatus.APPROVED).count(),
        "recent_requests": qs.select_related("department", "created_by")[:8],
    }

    context.update(build_dashboard_analytics_context(request.user))

    return render(
        request,
        "dashboard/department_head_dashboard.html",
        context,
    )


@role_required([UserRole.STAFF])
def staff_dashboard(request):
    qs = get_org_request_queryset(request.user)

    context = {
        "page_title": "Staff Dashboard",
        "my_requests": qs.count(),
        "draft_requests": qs.filter(status=RequestStatus.DRAFT).count(),
        "pending_requests": qs.filter(
            status__in=[
                RequestStatus.SUBMITTED,
                RequestStatus.IN_REVIEW,
            ]
        ).count(),
        "approved_requests": qs.filter(status=RequestStatus.APPROVED).count(),
        "rejected_requests": qs.filter(status=RequestStatus.REJECTED).count(),
        "recent_requests": qs.select_related("department", "created_by")[:8],
    }

    context.update(build_dashboard_analytics_context(request.user))

    return render(
        request,
        "dashboard/staff_dashboard.html",
        context,
    )


@role_required([UserRole.APPROVER])
def approver_dashboard(request):
    steps = get_approver_step_queryset(request.user)

    pending_steps = steps.filter(
        status=ApprovalStepStatus.PENDING,
        is_current=True,
    )

    urgent_steps = pending_steps.filter(
        request__priority="URGENT",
    )

    history_steps = steps.filter(
        status__in=[
            ApprovalStepStatus.APPROVED,
            ApprovalStepStatus.REJECTED,
        ]
    )

    recent_requests = (
        DocumentRequest.objects.select_related(
            "department",
            "created_by",
            "organization",
        )
        .filter(
            approval_steps__assigned_to=request.user,
        )
        .distinct()
        .order_by("-created_at")[:8]
    )

    context = {
        "page_title": "Approver Dashboard",
        "assigned_approvals": pending_steps.count(),
        "urgent_approvals": urgent_steps.count(),
        "approval_history": history_steps.count(),
        "recent_requests": recent_requests,
    }

    context.update(build_dashboard_analytics_context(request.user))

    return render(
        request,
        "dashboard/approver_dashboard.html",
        context,
    )


@role_required([UserRole.AUDITOR])
def auditor_dashboard(request):
    qs = get_org_request_queryset(request.user)

    profile = get_profile(request.user)

    audit_logs = AuditLog.objects.none()
    valid_certificate_count = 0
    invalid_certificate_count = 0

    if profile and profile.organization:
        audit_logs = (
            AuditLog.objects.select_related("organization", "user")
            .filter(organization=profile.organization)
            .order_by("-created_at")[:8]
        )

        certificate_qs = ApprovalCertificateSignature.objects.filter(
            document_request__organization=profile.organization,
        )

        valid_certificate_count = certificate_qs.filter(is_valid=True).count()
        invalid_certificate_count = certificate_qs.filter(is_valid=False).count()

    context = {
        "page_title": "Auditor Dashboard",
        "total_requests": qs.count(),
        "approved_requests": qs.filter(status=RequestStatus.APPROVED).count(),
        "rejected_requests": qs.filter(status=RequestStatus.REJECTED).count(),
        "valid_certificate_count": valid_certificate_count,
        "invalid_certificate_count": invalid_certificate_count,
        "recent_requests": qs.select_related("department", "created_by")[:8],
        "recent_audit_logs": audit_logs,
    }

    context.update(build_dashboard_analytics_context(request.user))

    return render(
        request,
        "dashboard/auditor_dashboard.html",
        context,
    )
    
    
@login_required
def my_activity_dashboard(request):
    """
    Personal activity dashboard.

    Shows:
    - watched requests
    - overdue watched approvals
    - my pending approvals
    - recent notifications
    - recent activity from watched requests
    - role-wise shortcuts
    """

    user = request.user
    profile = getattr(user, "profile", None)

    if user.is_superuser:
        watched_requests = DocumentRequest.objects.none()
        watched_request_ids = []
    else:
        watched_queryset = (
            RequestWatcher.objects.select_related(
                "request",
                "request__organization",
                "request__department",
                "request__created_by",
                "request__workflow",
            )
            .filter(
                user=user,
                is_active=True,
                request__organization=profile.organization if profile else None,
            )
            .order_by("-updated_at")
        )

        watched_requests = [
            watcher.request
            for watcher in watched_queryset[:12]
        ]

        watched_request_ids = [
            watcher.request_id
            for watcher in watched_queryset
        ]

    my_pending_steps = (
        ApprovalStep.objects.select_related(
            "request",
            "request__organization",
            "request__department",
            "request__created_by",
            "assigned_to",
        )
        .filter(
            assigned_to=user,
            status=ApprovalStepStatus.PENDING,
            is_current=True,
        )
        .order_by(
            "due_at",
            "-request__priority",
            "-created_at",
        )
    )

    overdue_pending_steps = my_pending_steps.filter(
        Q(is_overdue=True)
        | Q(due_at__lt=timezone.now())
    )

    overdue_watched_steps = ApprovalStep.objects.none()

    if watched_request_ids:
        overdue_watched_steps = (
            ApprovalStep.objects.select_related(
                "request",
                "request__organization",
                "request__department",
                "assigned_to",
            )
            .filter(
                request_id__in=watched_request_ids,
                status=ApprovalStepStatus.PENDING,
                is_current=True,
            )
            .filter(
                Q(is_overdue=True)
                | Q(due_at__lt=timezone.now())
            )
            .order_by("due_at")
        )

    recent_notifications = (
        Notification.objects.select_related(
            "actor",
            "organization",
        )
        .filter(
            recipient=user,
        )
        .order_by("-created_at")[:10]
    )

    recent_activity_items = []

    for document_request in watched_requests[:6]:
        timeline_items = build_request_activity_timeline(
            document_request=document_request,
            limit=8,
        )

        for item in timeline_items:
            item.meta = item.meta or {}
            item.meta["request_number"] = document_request.request_number
            item.meta["request_title"] = document_request.title
            item.meta["request_id"] = document_request.pk
            recent_activity_items.append(item)

    recent_activity_items = sorted(
        recent_activity_items,
        key=lambda item: item.timestamp,
        reverse=True,
    )[:20]

    watched_count = len(watched_request_ids)
    pending_count = my_pending_steps.count()
    overdue_count = overdue_pending_steps.count()
    unread_notifications_count = Notification.objects.filter(
        recipient=user,
        is_read=False,
    ).count()

    can_open_approval_inbox = (
        not user.is_superuser
        and profile
        and profile.role in [
            UserRole.ORG_ADMIN,
            UserRole.DEPARTMENT_HEAD,
            UserRole.APPROVER,
        ]
    )

    return render(
        request,
        "dashboard/my_activity_dashboard.html",
        {
            "page_title": "My Activity",
            "watched_requests": watched_requests,
            "watched_count": watched_count,
            "my_pending_steps": my_pending_steps[:10],
            "pending_count": pending_count,
            "overdue_pending_steps": overdue_pending_steps[:10],
            "overdue_watched_steps": overdue_watched_steps[:10],
            "overdue_count": overdue_count,
            "recent_notifications": recent_notifications,
            "unread_notifications_count": unread_notifications_count,
            "recent_activity_items": recent_activity_items,
            "can_open_approval_inbox": can_open_approval_inbox,
            "profile": profile,
        },
    )
    
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.models import UserRole
@login_required
def system_health_dashboard(request):
    if not can_view_system_health(request.user):
        messages.error(request, "You do not have permission to view system health.")
        return redirect("dashboard:home")

    health_summary = get_system_health_summary()

    return render(
        request,
        "dashboard/system_health_dashboard.html",
        {
            "page_title": "System Health",
            "health_summary": health_summary,
        },
    )
    
@login_required
def backup_export_dashboard(request):
    if not can_view_backup_export(request.user):
        messages.error(request, "Only Super Admin can access backup and export tools.")
        return redirect("dashboard:home")

    summary = get_backup_dashboard_summary()
    backup_logs = get_recent_backup_job_logs(limit=20)
    backup_stats = get_backup_job_stats()

    return render(
        request,
        "dashboard/backup_export_dashboard.html",
        {
            "page_title": "Backup & Export",
            "summary": summary,
            "backup_logs": backup_logs,
            "backup_stats": backup_stats,
        },
    )
@login_required
def backup_export_action(request):
    if not can_view_backup_export(request.user):
        messages.error(request, "Only Super Admin can perform backup/export actions.")
        return redirect("dashboard:home")

    if request.method != "POST":
        return redirect("dashboard:backup_export")

    action = request.POST.get("action", "").strip()

    try:
        if action in [
            "database",
            "media",
            "full",
            "audit",
            "notifications",
            "requests",
        ]:
            job_log = run_backup_job(
                action=action,
                triggered_by=request.user,
                metadata={
                    "source": "manual_dashboard",
                    "user_id": request.user.pk,
                    "username": request.user.username,
                },
            )

            if job_log.status == "SUCCESS":
                messages.success(
                    request,
                    f"{job_log.get_job_type_display()} created successfully.",
                )
                return get_backup_file_response(job_log.file_path)

            messages.error(
                request,
                f"Backup/export failed: {job_log.error_message}",
            )
            return redirect("dashboard:backup_export")

        if action == "cleanup":
            deleted_count = delete_old_backups(days=15)
            messages.success(
                request,
                f"Old backup cleanup completed. Deleted {deleted_count} file(s).",
            )
            return redirect("dashboard:backup_export")

        messages.error(request, "Invalid backup/export action selected.")
        return redirect("dashboard:backup_export")

    except Exception as exc:
        messages.error(request, f"Backup/export failed: {exc}")
        return redirect("dashboard:backup_export")
    
    
@login_required
def restore_dashboard(request):
    if not can_view_backup_export(request.user):
        messages.error(request, "Only Super Admin can access restore tools.")
        return redirect("dashboard:home")

    upload_form = RestoreUploadForm()
    recent_restore_jobs = get_recent_restore_jobs(limit=20)

    return render(
        request,
        "dashboard/restore_dashboard.html",
        {
            "page_title": "Restore Center",
            "upload_form": upload_form,
            "recent_restore_jobs": recent_restore_jobs,
        },
    )


@login_required
def restore_upload(request):
    if not can_view_backup_export(request.user):
        messages.error(request, "Only Super Admin can upload restore files.")
        return redirect("dashboard:home")

    if request.method != "POST":
        return redirect("dashboard:restore_dashboard")

    form = RestoreUploadForm(request.POST, request.FILES)

    if not form.is_valid():
        messages.error(request, "Please upload a valid restore file.")
        return redirect("dashboard:restore_dashboard")

    restore_job = form.save(commit=False)
    restore_job.uploaded_by = request.user
    restore_job.original_filename = restore_job.uploaded_file.name
    restore_job.status = RestoreJobStatus.UPLOADED
    restore_job.save()

    restore_job = validate_restore_job(restore_job)

    if restore_job.status == RestoreJobStatus.FAILED_VALIDATION:
        notify_super_admins_restore_failed(restore_job)
        messages.error(request, f"Restore validation failed: {restore_job.error_message}")
    else:
        messages.success(request, "Restore file uploaded and validated successfully.")

    return redirect("dashboard:restore_detail", pk=restore_job.pk)


@login_required
def restore_detail(request, pk):
    if not can_view_backup_export(request.user):
        messages.error(request, "Only Super Admin can view restore jobs.")
        return redirect("dashboard:home")

    restore_job = get_object_or_404(
        RestoreJobLog.objects.select_related("uploaded_by"),
        pk=pk,
    )

    confirm_form = RestoreConfirmForm()

    return render(
        request,
        "dashboard/restore_detail.html",
        {
            "page_title": "Restore Detail",
            "restore_job": restore_job,
            "confirm_form": confirm_form,
        },
    )


@login_required
def restore_dry_run(request, pk):
    if not can_view_backup_export(request.user):
        messages.error(request, "Only Super Admin can run restore dry-run.")
        return redirect("dashboard:home")

    restore_job = get_object_or_404(RestoreJobLog, pk=pk)

    if request.method != "POST":
        return redirect("dashboard:restore_detail", pk=restore_job.pk)

    restore_job = perform_restore_dry_run(restore_job)

    if restore_job.status == RestoreJobStatus.FAILED:
        notify_super_admins_restore_failed(restore_job)
        messages.error(request, f"Dry-run failed: {restore_job.error_message}")
    else:
        messages.success(request, "Restore dry-run completed successfully.")

    return redirect("dashboard:restore_detail", pk=restore_job.pk)


@login_required
def restore_confirm(request, pk):
    if not can_view_backup_export(request.user):
        messages.error(request, "Only Super Admin can confirm restore jobs.")
        return redirect("dashboard:home")

    restore_job = get_object_or_404(RestoreJobLog, pk=pk)

    if request.method != "POST":
        return redirect("dashboard:restore_detail", pk=restore_job.pk)

    form = RestoreConfirmForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Confirmation text is incorrect.")
        return redirect("dashboard:restore_detail", pk=restore_job.pk)

    restore_job = confirm_restore_job(
        restore_job=restore_job,
        confirmation_text=form.cleaned_data["confirmation_text"],
    )

    messages.success(
        request,
        "Restore job confirmed. Follow the safe restore instructions below.",
    )

    return redirect("dashboard:restore_detail", pk=restore_job.pk)


@login_required
def restore_media_execute(request, pk):
    if not can_view_backup_export(request.user):
        messages.error(request, "Only Super Admin can execute media restore.")
        return redirect("dashboard:home")

    restore_job = get_object_or_404(RestoreJobLog, pk=pk)

    if request.method != "POST":
        return redirect("dashboard:restore_detail", pk=restore_job.pk)

    try:
        restore_job = restore_media_zip(restore_job)
        messages.success(
            request,
            "Media ZIP restored into media/restored_media_preview safely.",
        )

    except Exception as exc:
        restore_job.status = RestoreJobStatus.FAILED
        restore_job.error_message = str(exc)
        restore_job.save(update_fields=["status", "error_message"])
        notify_super_admins_restore_failed(restore_job)
        messages.error(request, f"Media restore failed: {exc}")

    return redirect("dashboard:restore_detail", pk=restore_job.pk)


@login_required
def maintenance_mode_dashboard(request):
    if not can_manage_maintenance_mode(request.user):
        messages.error(request, "Only Super Admin can manage maintenance mode.")
        return redirect("dashboard:home")

    maintenance = MaintenanceMode.get_config()

    form = MaintenanceModeForm(
        request.POST or None,
        instance=maintenance,
    )

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "save_settings":
            if form.is_valid():
                form.save()

                messages.success(
                    request,
                    "Maintenance settings updated successfully.",
                )
                return redirect("dashboard:maintenance_mode")

        elif action == "enable":
            maintenance.enable(
                user=request.user,
                restore_safe_lock=False,
            )

            create_maintenance_audit_log(
                request=request,
                action="ENABLED",
                maintenance=maintenance,
            )

            messages.success(
                request,
                "Maintenance mode enabled successfully.",
            )
            return redirect("dashboard:maintenance_mode")

        elif action == "enable_restore_lock":
            maintenance.enable(
                user=request.user,
                restore_safe_lock=True,
            )

            create_maintenance_audit_log(
                request=request,
                action="RESTORE_LOCK_ENABLED",
                maintenance=maintenance,
            )

            messages.success(
                request,
                "Restore-safe lock mode enabled successfully.",
            )
            return redirect("dashboard:maintenance_mode")

        elif action == "disable":
            maintenance.disable(
                user=request.user,
            )

            create_maintenance_audit_log(
                request=request,
                action="DISABLED",
                maintenance=maintenance,
            )

            messages.success(
                request,
                "Maintenance mode disabled successfully.",
            )
            return redirect("dashboard:maintenance_mode")

    return render(
        request,
        "dashboard/maintenance_mode.html",
        {
            "page_title": "Maintenance Mode",
            "maintenance": maintenance,
            "form": form,
        },
    )


def maintenance_public(request):
    maintenance = MaintenanceMode.get_config()

    return render(
        request,
        "dashboard/maintenance_public.html",
        {
            "maintenance": maintenance,
            "restore_safe_lock": maintenance.restore_safe_lock,
        },
        status=503 if maintenance.is_enabled else 200,
    )


def create_maintenance_audit_log(request, action, maintenance):
    try:
        from apps.audit.models import AuditAction
        from apps.audit.services import create_audit_log

        create_audit_log(
            request=request,
            organization=None,
            action=AuditAction.UPDATED,
            model_name="MaintenanceMode",
            object_id=maintenance.pk,
            message=f"Maintenance mode action: {action}",
            extra_data={
                "action": action,
                "is_enabled": maintenance.is_enabled,
                "restore_safe_lock": maintenance.restore_safe_lock,
                "enabled_by": request.user.username if request.user else "",
                "enabled_at": (
                    maintenance.enabled_at.isoformat()
                    if maintenance.enabled_at
                    else ""
                ),
            },
        )

    except Exception:
        pass
    
    
@login_required
def deployment_readiness_dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, "Only Super Admin can view deployment readiness.")
        return redirect("dashboard:home")

    readiness = get_deployment_readiness_summary()

    return render(
        request,
        "dashboard/deployment_readiness.html",
        {
            "page_title": "Deployment Readiness",
            "readiness": readiness,
        },
    )