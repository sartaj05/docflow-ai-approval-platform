from collections import OrderedDict

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.approvals.models import (
    ApprovalStep,
    ApprovalStepStatus,
    DocumentRequest,
    RequestStatus,
    RiskLevel,
)
from apps.audit.models import AuditLog
from apps.departments.models import Department
from apps.notifications.models import Notification
from apps.organizations.models import Organization


def get_profile(user):
    return getattr(user, "profile", None)


def get_user_organization(user):
    if user.is_superuser:
        return None

    profile = get_profile(user)

    if not profile:
        return None

    return profile.organization


def get_scoped_request_queryset(user):
    if user.is_superuser:
        return DocumentRequest.objects.select_related(
            "organization",
            "department",
            "created_by",
            "workflow",
        ).all()

    profile = get_profile(user)

    if not profile or not profile.organization:
        return DocumentRequest.objects.none()

    qs = DocumentRequest.objects.select_related(
        "organization",
        "department",
        "created_by",
        "workflow",
    ).filter(
        organization=profile.organization,
    )

    if profile.role == UserRole.ORG_ADMIN:
        return qs

    if profile.role == UserRole.DEPARTMENT_HEAD:
        if profile.department:
            return qs.filter(department=profile.department)

        return DocumentRequest.objects.none()

    if profile.role == UserRole.STAFF:
        return qs.filter(created_by=user)

    if profile.role == UserRole.APPROVER:
        return qs.filter(approval_steps__assigned_to=user).distinct()

    if profile.role == UserRole.AUDITOR:
        return qs

    return DocumentRequest.objects.none()


def get_scoped_approval_steps(user):
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


def build_status_summary(queryset):
    return {
        "total": queryset.count(),
        "draft": queryset.filter(status=RequestStatus.DRAFT).count(),
        "submitted": queryset.filter(status=RequestStatus.SUBMITTED).count(),
        "in_review": queryset.filter(status=RequestStatus.IN_REVIEW).count(),
        "approved": queryset.filter(status=RequestStatus.APPROVED).count(),
        "rejected": queryset.filter(status=RequestStatus.REJECTED).count(),
        "cancelled": queryset.filter(status=RequestStatus.CANCELLED).count(),
    }


def build_risk_summary(queryset):
    return {
        "high": queryset.filter(risk_level=RiskLevel.HIGH).count(),
        "medium": queryset.filter(risk_level=RiskLevel.MEDIUM).count(),
        "low": queryset.filter(risk_level=RiskLevel.LOW).count(),
        "pending": queryset.filter(
            Q(risk_level__isnull=True) | Q(risk_level="")
        ).count(),
    }


def build_month_labels(month_count=6):
    today = timezone.localdate()
    labels = OrderedDict()

    year = today.year
    month = today.month

    for index in range(month_count - 1, -1, -1):
        m = month - index
        y = year

        while m <= 0:
            m += 12
            y -= 1

        key = f"{y}-{str(m).zfill(2)}"
        label = timezone.datetime(y, m, 1).strftime("%b %Y")
        labels[key] = {
            "label": label,
            "total": 0,
            "approved": 0,
            "rejected": 0,
            "in_review": 0,
        }

    return labels


def build_monthly_trends(queryset, month_count=6):
    labels = build_month_labels(month_count)

    monthly_rows = (
        queryset.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            total=Count("id"),
            approved=Count("id", filter=Q(status=RequestStatus.APPROVED)),
            rejected=Count("id", filter=Q(status=RequestStatus.REJECTED)),
            in_review=Count("id", filter=Q(status=RequestStatus.IN_REVIEW)),
        )
        .order_by("month")
    )

    for row in monthly_rows:
        if not row["month"]:
            continue

        key = row["month"].strftime("%Y-%m")

        if key in labels:
            labels[key]["total"] = row["total"]
            labels[key]["approved"] = row["approved"]
            labels[key]["rejected"] = row["rejected"]
            labels[key]["in_review"] = row["in_review"]

    return {
        "labels": [item["label"] for item in labels.values()],
        "total": [item["total"] for item in labels.values()],
        "approved": [item["approved"] for item in labels.values()],
        "rejected": [item["rejected"] for item in labels.values()],
        "in_review": [item["in_review"] for item in labels.values()],
    }

def build_department_performance(queryset):
    rows = list(
        queryset.values(
            "department__id",
            "department__name",
        )
        .annotate(
            total=Count("id"),
            approved=Count("id", filter=Q(status=RequestStatus.APPROVED)),
            rejected=Count("id", filter=Q(status=RequestStatus.REJECTED)),
            in_review=Count("id", filter=Q(status=RequestStatus.IN_REVIEW)),
            high_risk=Count("id", filter=Q(risk_level=RiskLevel.HIGH)),
        )
        .order_by("-total")[:8]
    )

    labels = []
    total = []
    approved = []
    rejected = []
    high_risk = []

    for row in rows:
        labels.append(row["department__name"] or "No Department")
        total.append(row["total"])
        approved.append(row["approved"])
        rejected.append(row["rejected"])
        high_risk.append(row["high_risk"])

    return {
        "labels": labels,
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "high_risk": high_risk,
        "rows": rows,
    }
def build_risk_distribution_chart(queryset):
    risk_summary = build_risk_summary(queryset)

    return {
        "labels": ["High", "Medium", "Low", "Pending"],
        "values": [
            risk_summary["high"],
            risk_summary["medium"],
            risk_summary["low"],
            risk_summary["pending"],
        ],
    }


def get_recent_activity(user, limit=10):
    organization = get_user_organization(user)

    if user.is_superuser:
        audit_logs = AuditLog.objects.select_related(
            "organization",
            "user",
        ).order_by("-created_at")[:limit]
    elif organization:
        audit_logs = (
            AuditLog.objects.select_related(
                "organization",
                "user",
            )
            .filter(organization=organization)
            .order_by("-created_at")[:limit]
        )
    else:
        audit_logs = AuditLog.objects.none()

    return audit_logs


def get_recent_notifications(user, limit=8):
    if not user.is_authenticated:
        return Notification.objects.none()

    return (
        Notification.objects.select_related(
            "recipient",
            "actor",
            "organization",
        )
        .filter(recipient=user)
        .order_by("-created_at")[:limit]
    )


def get_unread_notifications_count(user):
    if not user.is_authenticated:
        return 0

    return Notification.objects.filter(
        recipient=user,
        is_read=False,
    ).count()


def build_role_widgets(user):
    if user.is_superuser:
        return build_super_admin_widgets(user)

    profile = get_profile(user)

    if not profile:
        return {}

    if profile.role == UserRole.ORG_ADMIN:
        return build_org_admin_widgets(user)

    if profile.role == UserRole.DEPARTMENT_HEAD:
        return build_department_head_widgets(user)

    if profile.role == UserRole.STAFF:
        return build_staff_widgets(user)

    if profile.role == UserRole.APPROVER:
        return build_approver_widgets(user)

    if profile.role == UserRole.AUDITOR:
        return build_auditor_widgets(user)

    return {}


def build_super_admin_widgets(user):
    return {
        "total_organizations": Organization.objects.count(),
        "active_organizations": Organization.objects.filter(is_active=True).count(),
        "inactive_organizations": Organization.objects.filter(is_active=False).count(),
        "total_departments": Department.objects.count(),
    }


def build_org_admin_widgets(user):
    organization = get_user_organization(user)
    qs = get_scoped_request_queryset(user)

    return {
        "total_users": organization.users.count() if organization and hasattr(organization, "users") else 0,
        "total_departments": Department.objects.filter(organization=organization).count() if organization else 0,
        "active_departments": Department.objects.filter(organization=organization, is_active=True).count() if organization else 0,
        "pending_requests": qs.filter(status__in=[RequestStatus.SUBMITTED, RequestStatus.IN_REVIEW]).count(),
    }


def build_department_head_widgets(user):
    profile = get_profile(user)
    qs = get_scoped_request_queryset(user)

    return {
        "department_name": profile.department.name if profile and profile.department else "No Department",
        "department_requests": qs.count(),
        "department_pending": qs.filter(status__in=[RequestStatus.SUBMITTED, RequestStatus.IN_REVIEW]).count(),
        "department_high_risk": qs.filter(risk_level=RiskLevel.HIGH).count(),
    }


def build_staff_widgets(user):
    qs = get_scoped_request_queryset(user)

    return {
        "my_requests": qs.count(),
        "my_drafts": qs.filter(status=RequestStatus.DRAFT).count(),
        "my_pending": qs.filter(status__in=[RequestStatus.SUBMITTED, RequestStatus.IN_REVIEW]).count(),
        "my_approved": qs.filter(status=RequestStatus.APPROVED).count(),
    }


def build_approver_widgets(user):
    steps = get_scoped_approval_steps(user)

    return {
        "assigned_pending": steps.filter(status=ApprovalStepStatus.PENDING, is_current=True).count(),
        "urgent_pending": steps.filter(
            status=ApprovalStepStatus.PENDING,
            is_current=True,
            request__priority="URGENT",
        ).count(),
        "approved_by_me": steps.filter(status=ApprovalStepStatus.APPROVED).count(),
        "rejected_by_me": steps.filter(status=ApprovalStepStatus.REJECTED).count(),
    }


def build_auditor_widgets(user):
    qs = get_scoped_request_queryset(user)
    organization = get_user_organization(user)

    return {
        "audit_logs": AuditLog.objects.filter(organization=organization).count() if organization else 0,
        "approved_requests": qs.filter(status=RequestStatus.APPROVED).count(),
        "rejected_requests": qs.filter(status=RequestStatus.REJECTED).count(),
        "high_risk_requests": qs.filter(risk_level=RiskLevel.HIGH).count(),
    }


def build_dashboard_analytics_context(user):
    queryset = get_scoped_request_queryset(user)

    return {
        "analytics_status": build_status_summary(queryset),
        "analytics_risk": build_risk_summary(queryset),
        "monthly_trends": build_monthly_trends(queryset),
        "department_performance": build_department_performance(queryset),
        "risk_distribution": build_risk_distribution_chart(queryset),
        "recent_activity": get_recent_activity(user),
        "recent_notifications": get_recent_notifications(user),
        "role_widgets": build_role_widgets(user),
        "sla_widgets": build_sla_widgets(user),
        "unread_notifications_count": get_unread_notifications_count(user),
    }
    
def build_sla_widgets(user):
    if user.is_superuser:
        qs = ApprovalStep.objects.select_related("request").filter(
            status=ApprovalStepStatus.PENDING,
            is_current=True,
        )
    else:
        request_qs = get_scoped_request_queryset(user)
        qs = ApprovalStep.objects.select_related("request").filter(
            request__in=request_qs,
            status=ApprovalStepStatus.PENDING,
            is_current=True,
        )

    return {
        "pending_sla_steps": qs.count(),
        "overdue_steps": qs.filter(is_overdue=True).count(),
        "escalated_steps": qs.filter(escalated_at__isnull=False).count(),
        "due_today": qs.filter(
            due_at__date=timezone.localdate(),
        ).count(),
    }