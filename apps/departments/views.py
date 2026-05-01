from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.departments.forms import DepartmentForm
from apps.departments.models import Department


def get_user_organization(request):
    if request.user.is_superuser:
        return None

    profile = getattr(request.user, "profile", None)

    if not profile or not profile.organization:
        return None

    return profile.organization


def can_manage_departments(user):
    if user.is_superuser:
        return False

    profile = getattr(user, "profile", None)

    if not profile:
        return False

    return profile.role == UserRole.ORG_ADMIN


def can_view_departments(user):
    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.DEPARTMENT_HEAD,
        UserRole.AUDITOR,
        UserRole.APPROVER,
    ]


@login_required
def department_list(request):
    if not can_view_departments(request.user):
        messages.error(request, "You do not have permission to view departments.")
        return redirect("dashboard:home")

    organization = get_user_organization(request)

    if request.user.is_superuser:
        departments = (
            Department.objects.select_related("organization", "head")
            .all()
            .order_by("organization__name", "name")
        )
    else:
        departments = (
            Department.objects.filter(organization=organization)
            .select_related("organization", "head")
            .order_by("name")
        )

    total_departments = departments.count()
    active_departments = departments.filter(is_active=True).count()
    inactive_departments = departments.filter(is_active=False).count()

    return render(
        request,
        "departments/department_list.html",
        {
            "page_title": "Departments",
            "departments": departments,
            "total_departments": total_departments,
            "active_departments": active_departments,
            "inactive_departments": inactive_departments,
            "can_manage": can_manage_departments(request.user),
        },
    )


@login_required
@transaction.atomic
def department_create(request):
    if not can_manage_departments(request.user):
        messages.error(request, "Only organization admins can create departments.")
        return redirect("departments:list")

    organization = get_user_organization(request)

    if not organization:
        messages.error(request, "Organization not found.")
        return redirect("dashboard:home")

    form = DepartmentForm(
        request.POST or None,
        organization=organization,
    )

    if request.method == "POST":
        if form.is_valid():
            department = form.save(commit=False)
            department.organization = organization
            department.created_by = request.user
            department.save()

            selected_profile = form.cleaned_data.get("head")

            if selected_profile:
                selected_profile.role = UserRole.DEPARTMENT_HEAD
                selected_profile.department = department
                selected_profile.save()

            create_audit_log(
                request=request,
                organization=organization,
                action=AuditAction.CREATED,
                model_name="Department",
                object_id=department.pk,
                message=f"Department '{department.name}' created.",
                extra_data={
                    "department_name": department.name,
                    "head": department.head.display_name if department.head else "",
                    "is_active": department.is_active,
                },
            )

            messages.success(request, "Department created successfully.")
            return redirect("departments:list")

    return render(
        request,
        "departments/department_form.html",
        {
            "page_title": "Create Department",
            "form": form,
            "form_title": "Create Department",
            "submit_label": "Create Department",
        },
    )


@login_required
def department_detail(request, pk):
    if not can_view_departments(request.user):
        messages.error(request, "You do not have permission to view this department.")
        return redirect("dashboard:home")

    organization = get_user_organization(request)

    if request.user.is_superuser:
        department = get_object_or_404(
            Department.objects.select_related("organization", "head"),
            pk=pk,
        )
    else:
        department = get_object_or_404(
            Department.objects.select_related("organization", "head"),
            pk=pk,
            organization=organization,
        )

    users = (
        department.user_profiles.select_related("user")
        .filter(is_active=True, user__is_active=True)
        .order_by("user__full_name", "user__username")
    )

    return render(
        request,
        "departments/department_detail.html",
        {
            "page_title": department.name,
            "department": department,
            "users": users,
            "can_manage": can_manage_departments(request.user),
        },
    )


@login_required
@transaction.atomic
def department_update(request, pk):
    if not can_manage_departments(request.user):
        messages.error(request, "Only organization admins can update departments.")
        return redirect("departments:list")

    organization = get_user_organization(request)

    if not organization:
        messages.error(request, "Organization not found.")
        return redirect("dashboard:home")

    department = get_object_or_404(
        Department,
        pk=pk,
        organization=organization,
    )

    old_head = department.head

    form = DepartmentForm(
        request.POST or None,
        instance=department,
        organization=organization,
    )

    if request.method == "POST":
        if form.is_valid():
            department = form.save()

            selected_profile = form.cleaned_data.get("head")

            if selected_profile:
                selected_profile.role = UserRole.DEPARTMENT_HEAD
                selected_profile.department = department
                selected_profile.save()

            if old_head and selected_profile and old_head != selected_profile.user:
                old_profile = getattr(old_head, "profile", None)

                if old_profile and old_profile.department_id == department.id:
                    old_profile.department = None

                    if old_profile.role == UserRole.DEPARTMENT_HEAD:
                        old_profile.role = UserRole.STAFF

                    old_profile.save()

            if old_head and not selected_profile:
                old_profile = getattr(old_head, "profile", None)

                if old_profile and old_profile.department_id == department.id:
                    old_profile.department = None

                    if old_profile.role == UserRole.DEPARTMENT_HEAD:
                        old_profile.role = UserRole.STAFF

                    old_profile.save()

            create_audit_log(
                request=request,
                organization=organization,
                action=AuditAction.UPDATED,
                model_name="Department",
                object_id=department.pk,
                message=f"Department '{department.name}' updated.",
                extra_data={
                    "department_name": department.name,
                    "old_head": old_head.display_name if old_head else "",
                    "new_head": department.head.display_name if department.head else "",
                    "is_active": department.is_active,
                },
            )

            messages.success(request, "Department updated successfully.")
            return redirect("departments:detail", pk=department.pk)

    return render(
        request,
        "departments/department_form.html",
        {
            "page_title": "Edit Department",
            "form": form,
            "form_title": "Edit Department",
            "submit_label": "Update Department",
            "department": department,
        },
    )


@login_required
@transaction.atomic
def department_delete(request, pk):
    if not can_manage_departments(request.user):
        messages.error(request, "Only organization admins can delete departments.")
        return redirect("departments:list")

    organization = get_user_organization(request)

    if not organization:
        messages.error(request, "Organization not found.")
        return redirect("dashboard:home")

    department = get_object_or_404(
        Department,
        pk=pk,
        organization=organization,
    )

    if request.method == "POST":
        department_name = department.name
        department_id = department.pk

        create_audit_log(
            request=request,
            organization=organization,
            action=AuditAction.DELETED,
            model_name="Department",
            object_id=department_id,
            message=f"Department '{department_name}' deleted.",
            extra_data={
                "department_name": department_name,
            },
        )

        department.user_profiles.update(department=None)
        department.delete()

        messages.success(
            request,
            f"Department '{department_name}' deleted successfully.",
        )
        return redirect("departments:list")

    return render(
        request,
        "departments/department_confirm_delete.html",
        {
            "page_title": "Delete Department",
            "department": department,
        },
    )


@login_required
def department_users(request, pk):
    if not can_view_departments(request.user):
        messages.error(request, "You do not have permission to view department users.")
        return redirect("dashboard:home")

    organization = get_user_organization(request)

    if request.user.is_superuser:
        department = get_object_or_404(Department, pk=pk)
    else:
        department = get_object_or_404(
            Department,
            pk=pk,
            organization=organization,
        )

    users = (
        department.user_profiles.select_related("user")
        .filter(user__is_active=True)
        .order_by("role", "user__full_name", "user__username")
    )

    return render(
        request,
        "departments/department_users.html",
        {
            "page_title": f"{department.name} Users",
            "department": department,
            "users": users,
        },
    )