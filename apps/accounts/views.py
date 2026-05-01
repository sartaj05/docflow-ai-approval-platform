from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from apps.accounts.forms import (
    OrganizationRegistrationForm,
    OrganizationUserCreateForm,
    OrganizationUserFilterForm,
    OrganizationUserPasswordResetForm,
    OrganizationUserUpdateForm,
    UserSignatureSettingsForm,
)
from apps.accounts.forms import (
    OrganizationUserCreateForm,
    OrganizationUserFilterForm,
    OrganizationUserPasswordResetForm,
    OrganizationUserUpdateForm,
)
from apps.accounts.models import User, UserRole
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.accounts.forms import (
    LoginForm,
    OrganizationRegistrationForm,
    OrganizationUserCreateForm,
    OrganizationUserFilterForm,
    OrganizationUserPasswordResetForm,
    OrganizationUserUpdateForm,
    UserSignatureSettingsForm,
)
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.forms import (
    OrganizationRegistrationForm,
    OrganizationUserCreateForm,
    OrganizationUserFilterForm,
    OrganizationUserPasswordResetForm,
    OrganizationUserUpdateForm,
)
from apps.accounts.models import User, UserRole
from apps.accounts.utils import get_dashboard_url_for_user
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
def get_user_profile(user):
    return getattr(user, "profile", None)


def get_user_organization(user):
    profile = get_user_profile(user)

    if not profile:
        return None

    return profile.organization


def is_org_admin(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return False

    profile = get_user_profile(user)

    if not profile:
        return False

    return profile.role == UserRole.ORG_ADMIN


def get_org_users_queryset(user):
    organization = get_user_organization(user)

    if not organization:
        return User.objects.none()

    return (
        User.objects.select_related(
            "profile",
            "profile__organization",
            "profile__department",
        )
        .filter(
            profile__organization=organization,
            is_superuser=False,
        )
        .order_by("full_name", "username")
    )


def apply_user_filters(queryset, request):
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    department = request.GET.get("department", "").strip()
    status = request.GET.get("status", "").strip()

    if q:
        queryset = queryset.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(full_name__icontains=q)
            | Q(profile__phone__icontains=q)
            | Q(profile__designation__icontains=q)
        )

    if role:
        queryset = queryset.filter(profile__role=role)

    if department:
        queryset = queryset.filter(profile__department_id=department)

    if status == "active":
        queryset = queryset.filter(is_active=True, profile__is_active=True)

    if status == "inactive":
        queryset = queryset.filter(
            Q(is_active=False) | Q(profile__is_active=False)
        )

    return queryset
def login_view(request):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_for_user(request.user))

    form = LoginForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            username_or_email = form.cleaned_data["username"].strip()
            password = form.cleaned_data["password"]

            user = authenticate(
                request,
                username=username_or_email,
                password=password,
            )

            if not user:
                user_obj = User.objects.filter(email__iexact=username_or_email).first()

                if user_obj:
                    user = authenticate(
                        request,
                        username=user_obj.username,
                        password=password,
                    )

            if user is not None:
                if not user.is_active:
                    messages.error(request, "Your account is inactive. Please contact admin.")
                    return redirect("accounts:login")

                profile = getattr(user, "profile", None)

                if profile and not profile.is_active:
                    messages.error(request, "Your profile is inactive. Please contact admin.")
                    return redirect("accounts:login")

                login(request, user)

                try:
                    create_audit_log(
                        request=request,
                        organization=profile.organization if profile else None,
                        action=AuditAction.LOGIN,
                        model_name="User",
                        object_id=user.pk,
                        message=f"User '{user.display_name}' logged in.",
                        extra_data={
                            "username": user.username,
                            "email": user.email,
                        },
                    )
                except Exception:
                    pass

                return redirect(get_dashboard_url_for_user(user))

            messages.error(request, "Invalid username/email or password.")

    return render(
        request,
        "accounts/login.html",
        {
            "page_title": "Login",
            "form": form,
        },
    )
def super_admin_login(request):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_for_user(request.user))

    form = LoginForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            username_or_email = form.cleaned_data["username"].strip()
            password = form.cleaned_data["password"]

            user = authenticate(
                request,
                username=username_or_email,
                password=password,
            )

            if not user:
                user_obj = User.objects.filter(email__iexact=username_or_email).first()

                if user_obj:
                    user = authenticate(
                        request,
                        username=user_obj.username,
                        password=password,
                    )

            if user is not None:
                if not user.is_active:
                    messages.error(request, "Your account is inactive.")
                    return redirect("accounts:super_admin_login")

                if not user.is_superuser:
                    messages.error(request, "Only Super Admin can login from this page.")
                    return redirect("accounts:super_admin_login")

                login(request, user)

                try:
                    create_audit_log(
                        request=request,
                        organization=None,
                        action=AuditAction.LOGIN,
                        model_name="User",
                        object_id=user.pk,
                        message=f"Super Admin '{user.display_name}' logged in.",
                        extra_data={
                            "username": user.username,
                            "email": user.email,
                            "login_type": "super_admin",
                        },
                    )
                except Exception:
                    pass

                return redirect("dashboard:super_admin")

            messages.error(request, "Invalid username/email or password.")

    return render(
        request,
        "accounts/super_admin_login.html",
        {
            "page_title": "Super Admin Login",
            "form": form,
        },
    )
@login_required
def logout_view(request):
    user = request.user
    profile = getattr(user, "profile", None)

    try:
        create_audit_log(
            request=request,
            organization=profile.organization if profile else None,
            action=AuditAction.LOGOUT,
            model_name="User",
            object_id=user.pk,
            message=f"User '{user.display_name}' logged out.",
            extra_data={
                "username": user.username,
                "email": user.email,
            },
        )
    except Exception:
        pass

    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("accounts:login")


@login_required
def profile_view(request):
    profile = getattr(request.user, "profile", None)

    signature_form = None

    if profile:
        signature_form = UserSignatureSettingsForm(instance=profile)

    return render(
        request,
        "accounts/profile.html",
        {
            "page_title": "Profile",
            "user_obj": request.user,
            "profile": profile,
            "signature_form": signature_form,
        },
    )

@login_required
def profile_signature_update(request):
    profile = getattr(request.user, "profile", None)

    if not profile:
        messages.error(request, "User profile not found.")
        return redirect("accounts:profile")

    if request.method != "POST":
        return redirect("accounts:profile")

    form = UserSignatureSettingsForm(
        request.POST,
        request.FILES,
        instance=profile,
    )

    if form.is_valid():
        form.save()

        create_audit_log(
            request=request,
            organization=profile.organization,
            action=AuditAction.UPDATED,
            model_name="UserProfile",
            object_id=profile.pk,
            message=f"Signature settings updated for '{request.user.display_name}'.",
            extra_data={
                "has_signature_image": bool(profile.signature_image),
                "signature_title": profile.signature_title,
                "signature_enabled": profile.signature_enabled,
            },
        )

        messages.success(request, "Signature settings updated successfully.")
    else:
        messages.error(request, "Please correct errors in signature settings form.")

    return redirect("accounts:profile")
def register_organization(request):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_for_user(request.user))

    form = OrganizationRegistrationForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if form.is_valid():
            organization, user = form.save()

            messages.success(
                request,
                "Organization registered successfully. Please login with your admin account.",
            )
            return redirect("accounts:login")

    return render(
        request,
        "accounts/register_organization.html",
        {
            "page_title": "Register Organization",
            "form": form,
        },
    )
def sync_profile_from_form(user_obj, form, organization):
    """
    This assumes your accounts app already creates user.profile automatically.
    If profile does not exist, check your accounts signal/profile setup.
    """

    profile = getattr(user_obj, "profile", None)

    if not profile:
        raise ValueError(
            "User profile not found. Please ensure your accounts app creates profile automatically."
        )

    profile.organization = organization
    profile.role = form.cleaned_data["role"]
    profile.department = form.cleaned_data.get("department")
    profile.designation = form.cleaned_data.get("designation", "")
    profile.phone = form.cleaned_data.get("phone", "")
    profile.is_active = user_obj.is_active
    profile.save(
        update_fields=[
            "organization",
            "role",
            "department",
            "designation",
            "phone",
            "is_active",
            "updated_at",
        ]
    )

    return profile


@login_required
def organization_user_list(request):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can manage users.")
        return redirect("dashboard:home")

    organization = get_user_organization(request.user)

    queryset = get_org_users_queryset(request.user)
    queryset = apply_user_filters(queryset, request)

    filter_form = OrganizationUserFilterForm(
        request.GET or None,
        organization=organization,
    )

    total_users = queryset.count()
    active_users = queryset.filter(is_active=True, profile__is_active=True).count()
    inactive_users = queryset.filter(
        Q(is_active=False) | Q(profile__is_active=False)
    ).count()

    org_admin_count = queryset.filter(profile__role=UserRole.ORG_ADMIN).count()
    approver_count = queryset.filter(profile__role=UserRole.APPROVER).count()
    staff_count = queryset.filter(profile__role=UserRole.STAFF).count()

    return render(
        request,
        "accounts/users/user_list.html",
        {
            "page_title": "User Management",
            "users": queryset,
            "filter_form": filter_form,
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "org_admin_count": org_admin_count,
            "approver_count": approver_count,
            "staff_count": staff_count,
        },
    )


@login_required
def organization_user_create(request):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can create users.")
        return redirect("dashboard:home")

    organization = get_user_organization(request.user)

    if not organization:
        messages.error(request, "Organization not found.")
        return redirect("dashboard:home")

    form = OrganizationUserCreateForm(
        request.POST or None,
        organization=organization,
    )

    if request.method == "POST":
        if form.is_valid():
            user_obj = form.save(commit=False)
            user_obj.set_password(form.cleaned_data["password1"])
            user_obj.save()

            try:
                sync_profile_from_form(
                    user_obj=user_obj,
                    form=form,
                    organization=organization,
                )
            except ValueError as exc:
                user_obj.delete()
                messages.error(request, str(exc))
                return redirect("accounts:org_user_create")

            create_audit_log(
                request=request,
                organization=organization,
                action=AuditAction.CREATED,
                model_name="User",
                object_id=user_obj.pk,
                message=f"Organization user '{user_obj.display_name}' created.",
                extra_data={
                    "username": user_obj.username,
                    "email": user_obj.email,
                    "role": form.cleaned_data["role"],
                    "department": (
                        form.cleaned_data["department"].name
                        if form.cleaned_data.get("department")
                        else ""
                    ),
                },
            )

            messages.success(request, "User created successfully.")
            return redirect("accounts:org_user_detail", pk=user_obj.pk)

    return render(
        request,
        "accounts/users/user_form.html",
        {
            "page_title": "Create User",
            "form": form,
            "form_title": "Create Organization User",
            "submit_label": "Create User",
        },
    )


@login_required
def organization_user_detail(request, pk):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can view users.")
        return redirect("dashboard:home")

    user_obj = get_object_or_404(
        get_org_users_queryset(request.user),
        pk=pk,
    )

    return render(
        request,
        "accounts/users/user_detail.html",
        {
            "page_title": user_obj.display_name,
            "user_obj": user_obj,
            "profile": getattr(user_obj, "profile", None),
        },
    )


@login_required
def organization_user_update(request, pk):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can update users.")
        return redirect("dashboard:home")

    organization = get_user_organization(request.user)

    user_obj = get_object_or_404(
        get_org_users_queryset(request.user),
        pk=pk,
    )

    if user_obj == request.user:
        messages.error(request, "You cannot edit your own account from user management.")
        return redirect("accounts:org_user_detail", pk=user_obj.pk)

    form = OrganizationUserUpdateForm(
        request.POST or None,
        instance=user_obj,
        organization=organization,
        user_obj=user_obj,
    )

    if request.method == "POST":
        if form.is_valid():
            user_obj = form.save()

            sync_profile_from_form(
                user_obj=user_obj,
                form=form,
                organization=organization,
            )

            create_audit_log(
                request=request,
                organization=organization,
                action=AuditAction.UPDATED,
                model_name="User",
                object_id=user_obj.pk,
                message=f"Organization user '{user_obj.display_name}' updated.",
                extra_data={
                    "username": user_obj.username,
                    "email": user_obj.email,
                    "role": form.cleaned_data["role"],
                    "department": (
                        form.cleaned_data["department"].name
                        if form.cleaned_data.get("department")
                        else ""
                    ),
                    "is_active": user_obj.is_active,
                },
            )

            messages.success(request, "User updated successfully.")
            return redirect("accounts:org_user_detail", pk=user_obj.pk)

    return render(
        request,
        "accounts/users/user_form.html",
        {
            "page_title": "Edit User",
            "form": form,
            "form_title": "Edit Organization User",
            "submit_label": "Update User",
            "user_obj": user_obj,
        },
    )


@login_required
def organization_user_toggle_status(request, pk):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can activate/deactivate users.")
        return redirect("dashboard:home")

    user_obj = get_object_or_404(
        get_org_users_queryset(request.user),
        pk=pk,
    )

    if request.method != "POST":
        return redirect("accounts:org_user_detail", pk=user_obj.pk)

    if user_obj == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("accounts:org_user_detail", pk=user_obj.pk)

    user_obj.is_active = not user_obj.is_active
    user_obj.save(update_fields=["is_active"])

    profile = getattr(user_obj, "profile", None)

    if profile:
        profile.is_active = user_obj.is_active
        profile.save(update_fields=["is_active", "updated_at"])

    organization = get_user_organization(request.user)

    action_message = "activated" if user_obj.is_active else "deactivated"

    create_audit_log(
        request=request,
        organization=organization,
        action=AuditAction.STATUS_CHANGED,
        model_name="User",
        object_id=user_obj.pk,
        message=f"Organization user '{user_obj.display_name}' {action_message}.",
        extra_data={
            "username": user_obj.username,
            "email": user_obj.email,
            "is_active": user_obj.is_active,
        },
    )

    messages.success(request, f"User {action_message} successfully.")
    return redirect("accounts:org_user_detail", pk=user_obj.pk)


@login_required
def organization_user_reset_password(request, pk):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can reset passwords.")
        return redirect("dashboard:home")

    user_obj = get_object_or_404(
        get_org_users_queryset(request.user),
        pk=pk,
    )

    if user_obj == request.user:
        messages.error(request, "Use profile settings to change your own password.")
        return redirect("accounts:org_user_detail", pk=user_obj.pk)

    form = OrganizationUserPasswordResetForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            new_password = form.cleaned_data["new_password1"]
            user_obj.set_password(new_password)
            user_obj.save(update_fields=["password"])

            organization = get_user_organization(request.user)

            create_audit_log(
                request=request,
                organization=organization,
                action=AuditAction.UPDATED,
                model_name="User",
                object_id=user_obj.pk,
                message=f"Password reset for organization user '{user_obj.display_name}'.",
                extra_data={
                    "username": user_obj.username,
                    "email": user_obj.email,
                },
            )

            messages.success(request, "Password reset successfully.")
            return redirect("accounts:org_user_detail", pk=user_obj.pk)

    return render(
        request,
        "accounts/users/user_reset_password.html",
        {
            "page_title": "Reset Password",
            "form": form,
            "user_obj": user_obj,
        },
    )