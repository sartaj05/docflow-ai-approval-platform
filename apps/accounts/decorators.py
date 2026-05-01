from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from apps.accounts.models import UserRole


def role_required(allowed_roles=None):
    allowed_roles = allowed_roles or []

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = getattr(request.user, "profile", None)

            if not profile:
                messages.error(request, "User profile not found.")
                return redirect("accounts:login")

            if profile.role not in allowed_roles:
                messages.error(request, "You do not have permission to access this page.")
                return redirect("dashboard:home")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def super_admin_only(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "Only Super Admin can access this page.")
            return redirect("dashboard:home")

        return view_func(request, *args, **kwargs)

    return wrapper


def organization_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)

        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        if not profile or not profile.organization:
            messages.error(request, "Organization profile not found.")
            return redirect("dashboard:home")

        return view_func(request, *args, **kwargs)

    return wrapper


org_admin_required = role_required([UserRole.ORG_ADMIN])
department_head_required = role_required([UserRole.DEPARTMENT_HEAD])
staff_required = role_required([UserRole.STAFF])
approver_required = role_required([UserRole.APPROVER])
auditor_required = role_required([UserRole.AUDITOR])