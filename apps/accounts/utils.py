from apps.accounts.models import UserRole


def get_dashboard_url_for_user(user):
    if not user.is_authenticated:
        return "/accounts/login/"

    if user.is_superuser:
        return "/dashboard/super-admin/"

    profile = getattr(user, "profile", None)

    if not profile:
        return "/dashboard/"

    role_dashboard_map = {
        UserRole.SUPER_ADMIN: "/dashboard/super-admin/",
        UserRole.ORG_ADMIN: "/dashboard/organization-admin/",
        UserRole.DEPARTMENT_HEAD: "/dashboard/department-head/",
        UserRole.STAFF: "/dashboard/staff/",
        UserRole.APPROVER: "/dashboard/approver/",
        UserRole.AUDITOR: "/dashboard/auditor/",
    }

    return role_dashboard_map.get(profile.role, "/dashboard/")