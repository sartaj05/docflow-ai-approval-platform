from django.db.models import Q

from apps.accounts.models import User, UserRole
from apps.approvals.models import DocumentRequest
from apps.audit.models import AuditLog
from apps.departments.models import Department
from apps.documents.models import DocumentAttachment
from apps.approvals.models import ApprovalDelegation

def get_profile(user):
    return getattr(user, "profile", None)


def get_user_organization(user):
    if user.is_superuser:
        return None

    profile = get_profile(user)

    if not profile:
        return None

    return profile.organization


def can_search_users(user):
    if user.is_superuser:
        return True

    profile = get_profile(user)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.AUDITOR,
    ]


def can_search_audit_logs(user):
    if user.is_superuser:
        return True

    profile = get_profile(user)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.AUDITOR,
    ]


def get_scoped_requests(user):
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
        return qs.filter(
            approval_steps__assigned_to=user,
        ).distinct()

    if profile.role == UserRole.AUDITOR:
        return qs

    return DocumentRequest.objects.none()


def get_scoped_departments(user):
    if user.is_superuser:
        return Department.objects.select_related(
            "organization",
            "head",
        ).all()

    profile = get_profile(user)

    if not profile or not profile.organization:
        return Department.objects.none()

    if profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.DEPARTMENT_HEAD,
        UserRole.APPROVER,
        UserRole.AUDITOR,
    ]:
        return Department.objects.select_related(
            "organization",
            "head",
        ).filter(
            organization=profile.organization,
        )

    return Department.objects.none()


def get_scoped_users(user):
    if not can_search_users(user):
        return User.objects.none()

    if user.is_superuser:
        return User.objects.select_related(
            "profile",
            "profile__organization",
            "profile__department",
        ).all()

    organization = get_user_organization(user)

    if not organization:
        return User.objects.none()

    return User.objects.select_related(
        "profile",
        "profile__organization",
        "profile__department",
    ).filter(
        profile__organization=organization,
    )


def get_scoped_documents(user):
    request_qs = get_scoped_requests(user)

    return DocumentAttachment.objects.select_related(
        "request",
        "request__organization",
        "request__department",
        "uploaded_by",
    ).filter(
        request__in=request_qs,
    )


def get_scoped_audit_logs(user):
    if not can_search_audit_logs(user):
        return AuditLog.objects.none()

    if user.is_superuser:
        return AuditLog.objects.select_related(
            "organization",
            "user",
        ).all()

    organization = get_user_organization(user)

    if not organization:
        return AuditLog.objects.none()

    return AuditLog.objects.select_related(
        "organization",
        "user",
    ).filter(
        organization=organization,
    )


def apply_date_filters(queryset, date_from=None, date_to=None, field_name="created_at"):
    if date_from:
        queryset = queryset.filter(**{f"{field_name}__date__gte": date_from})

    if date_to:
        queryset = queryset.filter(**{f"{field_name}__date__lte": date_to})

    return queryset


def search_requests(user, query, status=None, risk_level=None, date_from=None, date_to=None, limit=25):
    qs = get_scoped_requests(user)

    if query:
        request_id_query = Q()

        cleaned_query = query.strip()

        if cleaned_query.upper().startswith("REQ-"):
            try:
                request_id = int(cleaned_query.upper().split("-")[-1])
                request_id_query = Q(id=request_id)
            except ValueError:
                request_id_query = Q()

        qs = qs.filter(
            request_id_query
            | Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(ai_summary__icontains=query)
            | Q(ai_category__icontains=query)
            | Q(risk_notes__icontains=query)
            | Q(department__name__icontains=query)
            | Q(organization__name__icontains=query)
            | Q(created_by__username__icontains=query)
            | Q(created_by__email__icontains=query)
            | Q(created_by__full_name__icontains=query)
            | Q(workflow__name__icontains=query)
        )

    if status:
        qs = qs.filter(status=status)

    if risk_level:
        qs = qs.filter(risk_level=risk_level)

    qs = apply_date_filters(qs, date_from, date_to)

    return qs.order_by("-created_at")[:limit]


def search_users(user, query, date_from=None, date_to=None, limit=25):
    qs = get_scoped_users(user)

    if query:
        qs = qs.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(full_name__icontains=query)
            | Q(profile__designation__icontains=query)
            | Q(profile__phone__icontains=query)
            | Q(profile__organization__name__icontains=query)
            | Q(profile__department__name__icontains=query)
        )

    qs = apply_date_filters(qs, date_from, date_to, field_name="date_joined")

    return qs.order_by("-date_joined")[:limit]


def search_departments(user, query, date_from=None, date_to=None, limit=25):
    qs = get_scoped_departments(user)

    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(organization__name__icontains=query)
            | Q(head__username__icontains=query)
            | Q(head__email__icontains=query)
            | Q(head__full_name__icontains=query)
        )

    qs = apply_date_filters(qs, date_from, date_to)

    return qs.order_by("name")[:limit]


def search_documents(user, query, date_from=None, date_to=None, limit=25):
    qs = get_scoped_documents(user)

    if query:
        qs = qs.filter(
            Q(original_filename__icontains=query)
            | Q(file_type__icontains=query)
            | Q(extracted_text__icontains=query)
            | Q(ai_summary__icontains=query)
            | Q(ai_category__icontains=query)
            | Q(risk_notes__icontains=query)
            | Q(request__title__icontains=query)
            | Q(request__description__icontains=query)
            | Q(uploaded_by__username__icontains=query)
            | Q(uploaded_by__email__icontains=query)
            | Q(uploaded_by__full_name__icontains=query)
        )

    qs = apply_date_filters(qs, date_from, date_to)

    return qs.order_by("-created_at")[:limit]


def search_audit_logs(user, query, date_from=None, date_to=None, limit=25):
    qs = get_scoped_audit_logs(user)

    if query:
        qs = qs.filter(
            Q(message__icontains=query)
            | Q(model_name__icontains=query)
            | Q(object_id__icontains=query)
            | Q(ip_address__icontains=query)
            | Q(user_agent__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
            | Q(user__full_name__icontains=query)
            | Q(organization__name__icontains=query)
        )

    qs = apply_date_filters(qs, date_from, date_to)

    return qs.order_by("-created_at")[:limit]


def build_global_search_results(user, cleaned_data):
    query = cleaned_data.get("q", "").strip()
    search_type = cleaned_data.get("search_type") or "all"
    status = cleaned_data.get("status")
    risk_level = cleaned_data.get("risk_level")
    date_from = cleaned_data.get("date_from")
    date_to = cleaned_data.get("date_to")

    results = {
        "query": query,
        "search_type": search_type,
        "requests": [],
        "users": [],
        "departments": [],
        "documents": [],
        "audit_logs": [],
        "counts": {
            "requests": 0,
            "users": 0,
            "departments": 0,
            "documents": 0,
            "audit_logs": 0,
            "total": 0,
        },
    }

    if not query and not status and not risk_level and not date_from and not date_to:
        return results

    if search_type in ["all", "requests"]:
        requests = list(
            search_requests(
                user=user,
                query=query,
                status=status,
                risk_level=risk_level,
                date_from=date_from,
                date_to=date_to,
            )
        )

        results["requests"] = requests
        results["counts"]["requests"] = len(requests)

    if search_type in ["all", "users"]:
        users = list(
            search_users(
                user=user,
                query=query,
                date_from=date_from,
                date_to=date_to,
            )
        )

        results["users"] = users
        results["counts"]["users"] = len(users)

    if search_type in ["all", "departments"]:
        departments = list(
            search_departments(
                user=user,
                query=query,
                date_from=date_from,
                date_to=date_to,
            )
        )

        results["departments"] = departments
        results["counts"]["departments"] = len(departments)

    if search_type in ["all", "documents"]:
        documents = list(
            search_documents(
                user=user,
                query=query,
                date_from=date_from,
                date_to=date_to,
            )
        )

        results["documents"] = documents
        results["counts"]["documents"] = len(documents)

    if search_type in ["all", "audit"]:
        audit_logs = list(
            search_audit_logs(
                user=user,
                query=query,
                date_from=date_from,
                date_to=date_to,
            )
        )

        results["audit_logs"] = audit_logs
        results["counts"]["audit_logs"] = len(audit_logs)

    results["counts"]["total"] = (
        results["counts"]["requests"]
        + results["counts"]["users"]
        + results["counts"]["departments"]
        + results["counts"]["documents"]
        + results["counts"]["audit_logs"]
    )

    return results


def get_scoped_delegations(user):
    if user.is_superuser:
        return ApprovalDelegation.objects.select_related(
            "organization",
            "delegator",
            "delegate_to",
        ).all()

    profile = get_profile(user)

    if not profile or not profile.organization:
        return ApprovalDelegation.objects.none()

    if profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.AUDITOR,
    ]:
        return ApprovalDelegation.objects.select_related(
            "organization",
            "delegator",
            "delegate_to",
        ).filter(
            organization=profile.organization,
        )

    return ApprovalDelegation.objects.select_related(
        "organization",
        "delegator",
        "delegate_to",
    ).filter(
        organization=profile.organization,
    ).filter(
        Q(delegator=user) | Q(delegate_to=user)
    )