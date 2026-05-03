import csv

from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.approvals.models import DocumentRequest, RequestStatus, RiskLevel


def get_user_profile(user):
    return getattr(user, "profile", None)


def get_user_organization(user):
    if user.is_superuser:
        return None

    profile = get_user_profile(user)

    if not profile:
        return None

    return profile.organization


def can_view_reports(user):
    if user.is_superuser:
        return True

    profile = get_user_profile(user)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.DEPARTMENT_HEAD,
        UserRole.AUDITOR,
    ]


def get_report_queryset(user):
    if user.is_superuser:
        return DocumentRequest.objects.select_related(
            "organization",
            "department",
            "workflow",
            "created_by",
        ).all()

    profile = get_user_profile(user)

    if not profile or not profile.organization:
        return DocumentRequest.objects.none()

    qs = DocumentRequest.objects.select_related(
        "organization",
        "department",
        "workflow",
        "created_by",
    ).filter(
        organization=profile.organization,
    )

    if profile.role == UserRole.DEPARTMENT_HEAD:
        if profile.department:
            return qs.filter(department=profile.department)

        return DocumentRequest.objects.none()

    if profile.role == UserRole.ORG_ADMIN:
        return qs

    if profile.role == UserRole.AUDITOR:
        return qs

    return DocumentRequest.objects.none()


def apply_report_filters(queryset, request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()
    priority = request.GET.get("priority", "").strip()
    risk_level = request.GET.get("risk_level", "").strip()
    department = request.GET.get("department", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if q:
        request_id_query = Q()

        if q.upper().startswith("REQ-"):
            try:
                request_id = int(q.upper().replace("REQ-", ""))
                request_id_query = Q(id=request_id)
            except ValueError:
                request_id_query = Q()

        queryset = queryset.filter(
            request_id_query
            | Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(ai_summary__icontains=q)
            | Q(ai_category__icontains=q)
            | Q(risk_notes__icontains=q)
            | Q(created_by__username__icontains=q)
            | Q(created_by__email__icontains=q)
            | Q(created_by__full_name__icontains=q)
            | Q(department__name__icontains=q)
            | Q(organization__name__icontains=q)
        )

    if status:
        queryset = queryset.filter(status=status)

    if category:
        queryset = queryset.filter(category=category)

    if priority:
        queryset = queryset.filter(priority=priority)

    if risk_level:
        queryset = queryset.filter(risk_level=risk_level)

    if department:
        queryset = queryset.filter(department_id=department)

    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)

    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    return queryset


def build_report_summary(queryset):
    return {
        "total_requests": queryset.count(),
        "draft_count": queryset.filter(status=RequestStatus.DRAFT).count(),
        "submitted_count": queryset.filter(status=RequestStatus.SUBMITTED).count(),
        "in_review_count": queryset.filter(status=RequestStatus.IN_REVIEW).count(),
        "approved_count": queryset.filter(status=RequestStatus.APPROVED).count(),
        "rejected_count": queryset.filter(status=RequestStatus.REJECTED).count(),
        "cancelled_count": queryset.filter(status=RequestStatus.CANCELLED).count(),
        "high_risk_count": queryset.filter(risk_level=RiskLevel.HIGH).count(),
        "medium_risk_count": queryset.filter(risk_level=RiskLevel.MEDIUM).count(),
        "low_risk_count": queryset.filter(risk_level=RiskLevel.LOW).count(),
        "pending_risk_count": queryset.filter(
            Q(risk_level__isnull=True) | Q(risk_level="")
        ).count(),
    }


def get_department_summary(queryset):
    return (
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
        .order_by("department__name")
    )


def get_risk_summary(queryset):
    return (
        queryset.values("risk_level")
        .annotate(total=Count("id"))
        .order_by("risk_level")
    )


def csv_response(filename):
    response = HttpResponse(content_type="text/csv")
    current_date = timezone.localtime().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = f'attachment; filename="{filename}_{current_date}.csv"'
    return response


def export_requests_to_csv(queryset):
    response = csv_response("approval_requests_report")
    writer = csv.writer(response)

    writer.writerow(
        [
            "Request No",
            "Title",
            "Organization",
            "Department",
            "Workflow",
            "Category",
            "Priority",
            "Status",
            "Risk Level",
            "Created By",
            "Created At",
            "Submitted At",
            "Approved At",
            "Rejected At",
            "AI Category",
            "AI Summary",
            "Risk Notes",
        ]
    )

    for item in queryset:
        writer.writerow(
            [
                item.request_number,
                item.title,
                item.organization.name if item.organization else "",
                item.department.name if item.department else "",
                item.workflow.name if item.workflow else "",
                item.get_category_display(),
                item.get_priority_display(),
                item.get_status_display(),
                item.get_risk_level_display() if item.risk_level else "",
                item.created_by.display_name if item.created_by else "",
                item.created_at.strftime("%d-%m-%Y %I:%M %p") if item.created_at else "",
                item.submitted_at.strftime("%d-%m-%Y %I:%M %p") if item.submitted_at else "",
                item.approved_at.strftime("%d-%m-%Y %I:%M %p") if item.approved_at else "",
                item.rejected_at.strftime("%d-%m-%Y %I:%M %p") if item.rejected_at else "",
                item.ai_category or "",
                item.ai_summary or "",
                item.risk_notes or "",
            ]
        )

    return response


def export_department_summary_to_csv(queryset):
    response = csv_response("department_wise_report")
    writer = csv.writer(response)

    writer.writerow(
        [
            "Department",
            "Total Requests",
            "Approved",
            "Rejected",
            "In Review",
            "High Risk",
        ]
    )

    for row in get_department_summary(queryset):
        writer.writerow(
            [
                row["department__name"] or "No Department",
                row["total"],
                row["approved"],
                row["rejected"],
                row["in_review"],
                row["high_risk"],
            ]
        )

    return response


def export_risk_summary_to_csv(queryset):
    response = csv_response("risk_level_report")
    writer = csv.writer(response)

    writer.writerow(
        [
            "Risk Level",
            "Total Requests",
        ]
    )

    for row in get_risk_summary(queryset):
        writer.writerow(
            [
                row["risk_level"] or "Pending",
                row["total"],
            ]
        )

    return response