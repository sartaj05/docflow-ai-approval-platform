from rest_framework.permissions import BasePermission

from apps.accounts.models import UserRole
from apps.approvals.models import ApprovalWorkflow, DocumentRequest
from apps.departments.models import Department


def get_profile(user):
    return getattr(user, "profile", None)


def get_user_organization(user):
    if user.is_superuser:
        return None

    profile = get_profile(user)
    if not profile or not profile.is_active or not profile.organization_id:
        return None

    if not profile.organization.is_active:
        return None

    return profile.organization


def has_active_workspace(user):
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return get_user_organization(user) is not None


class HasActiveWorkspace(BasePermission):
    message = "An active organization workspace is required."

    def has_permission(self, request, view):
        return has_active_workspace(request.user)


def scoped_requests(user):
    base = DocumentRequest.objects.select_related(
        "organization",
        "department",
        "created_by",
        "workflow",
    )
    if user.is_superuser:
        return base.all()

    organization = get_user_organization(user)
    profile = get_profile(user)
    if not organization or not profile:
        return base.none()

    base = base.filter(organization=organization)
    if profile.role == UserRole.ORG_ADMIN or profile.role == UserRole.AUDITOR:
        return base
    if profile.role == UserRole.DEPARTMENT_HEAD:
        return base.filter(department_id=profile.department_id) if profile.department_id else base.none()
    if profile.role == UserRole.STAFF:
        return base.filter(created_by=user)
    if profile.role == UserRole.APPROVER:
        return base.filter(approval_steps__assigned_to=user).distinct()
    return base.none()


def scoped_workflows(user):
    organization = get_user_organization(user)
    if not organization:
        return ApprovalWorkflow.objects.none()
    return ApprovalWorkflow.objects.filter(
        organization=organization,
        is_active=True,
    ).prefetch_related("steps")


def scoped_departments(user):
    organization = get_user_organization(user)
    if not organization:
        return Department.objects.none()
    return Department.objects.filter(organization=organization, is_active=True)


def can_create_request(user):
    if user.is_superuser:
        return False
    profile = get_profile(user)
    return bool(
        profile
        and profile.is_active
        and profile.role in {
            UserRole.ORG_ADMIN,
            UserRole.DEPARTMENT_HEAD,
            UserRole.STAFF,
        }
        and get_user_organization(user)
    )


def can_manage_request(user, document_request):
    return bool(
        document_request.created_by_id == user.id
        and document_request.status == "DRAFT"
    )
