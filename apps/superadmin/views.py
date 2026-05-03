from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import super_admin_only
from apps.accounts.models import User
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.organizations.models import Organization


@super_admin_only
def organization_list(request):
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    organizations = Organization.objects.all().order_by("-created_at")

    if search:
        organizations = organizations.filter(
            Q(name__icontains=search)
            | Q(slug__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
        )

    if status == "active":
        organizations = organizations.filter(is_active=True)
    elif status == "inactive":
        organizations = organizations.filter(is_active=False)

    return render(
        request,
        "superadmin/organization_list.html",
        {
            "page_title": "Manage Organizations",
            "organizations": organizations,
            "search": search,
            "status": status,
        },
    )


@super_admin_only
def organization_detail(request, pk):
    organization = get_object_or_404(Organization, pk=pk)

    users = (
        User.objects.select_related(
            "profile",
            "profile__organization",
            "profile__department",
        )
        .filter(profile__organization=organization)
        .order_by("profile__role", "full_name", "username")
    )

    departments = (
        organization.departments.select_related("head")
        .order_by("name")
    )

    return render(
        request,
        "superadmin/organization_detail.html",
        {
            "page_title": organization.name,
            "organization": organization,
            "users": users,
            "departments": departments,
        },
    )


@super_admin_only
def organization_toggle_status(request, pk):
    organization = get_object_or_404(Organization, pk=pk)

    if request.method != "POST":
        return redirect("superadmin:organization_detail", pk=organization.pk)

    old_status = organization.is_active

    organization.is_active = not organization.is_active
    organization.save(update_fields=["is_active", "updated_at"])

    status_label = "activated" if organization.is_active else "deactivated"

    create_audit_log(
        request=request,
        user=request.user,
        organization=organization,
        action=AuditAction.STATUS_CHANGED,
        model_name="Organization",
        object_id=organization.pk,
        message=f"Organization '{organization.name}' was {status_label} by Super Admin.",
        extra_data={
            "old_is_active": old_status,
            "new_is_active": organization.is_active,
            "organization_name": organization.name,
        },
    )

    messages.success(
        request,
        f"{organization.name} has been {status_label}.",
    )

    return redirect("superadmin:organization_detail", pk=organization.pk)


@super_admin_only
def user_list(request):
    search = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()

    users = (
        User.objects.select_related(
            "profile",
            "profile__organization",
            "profile__department",
        )
        .all()
        .order_by("-created_at")
    )

    if search:
        users = users.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(full_name__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(profile__organization__name__icontains=search)
            | Q(profile__department__name__icontains=search)
        )

    if role == "SUPER_ADMIN":
        users = users.filter(is_superuser=True)
    elif role:
        users = users.filter(profile__role=role)

    if status == "active":
        users = users.filter(is_active=True)
    elif status == "inactive":
        users = users.filter(is_active=False)

    return render(
        request,
        "superadmin/user_list.html",
        {
            "page_title": "Manage Users",
            "users": users.distinct(),
            "search": search,
            "role": role,
            "status": status,
        },
    )


@super_admin_only
def user_toggle_status(request, pk):
    user_obj = get_object_or_404(
        User.objects.select_related(
            "profile",
            "profile__organization",
        ),
        pk=pk,
    )

    if request.method != "POST":
        return redirect("superadmin:users")

    if user_obj == request.user:
        messages.error(request, "You cannot deactivate your own Super Admin account.")
        return redirect("superadmin:users")

    old_status = user_obj.is_active

    user_obj.is_active = not user_obj.is_active
    user_obj.save(update_fields=["is_active", "updated_at"])

    status_label = "activated" if user_obj.is_active else "deactivated"

    organization = None

    if hasattr(user_obj, "profile") and user_obj.profile:
        organization = user_obj.profile.organization

    create_audit_log(
        request=request,
        user=request.user,
        organization=organization,
        action=AuditAction.STATUS_CHANGED,
        model_name="User",
        object_id=user_obj.pk,
        message=f"User '{user_obj.display_name}' was {status_label} by Super Admin.",
        extra_data={
            "target_user": user_obj.display_name,
            "target_username": user_obj.username,
            "target_email": user_obj.email,
            "old_is_active": old_status,
            "new_is_active": user_obj.is_active,
        },
    )

    messages.success(
        request,
        f"{user_obj.display_name} has been {status_label}.",
    )

    return redirect("superadmin:users")