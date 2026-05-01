from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives, get_connection
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.organizations.forms import (
    OrganizationApprovalNumberingForm,
    OrganizationCertificateSettingsForm,
    OrganizationFileSettingsForm,
    OrganizationProfileSettingsForm,
    OrganizationSMTPSettingsForm,
)


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


@login_required
def organization_settings(request):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can manage organization settings.")
        return redirect("dashboard:home")

    organization = get_user_organization(request.user)

    if not organization:
        messages.error(request, "Organization not found.")
        return redirect("dashboard:home")

    profile_form = OrganizationProfileSettingsForm(instance=organization)
    certificate_form = OrganizationCertificateSettingsForm(instance=organization)
    numbering_form = OrganizationApprovalNumberingForm(instance=organization)
    file_form = OrganizationFileSettingsForm(instance=organization)
    smtp_form = OrganizationSMTPSettingsForm(instance=organization)

    return render(
        request,
        "organizations/settings.html",
        {
            "page_title": "Organization Settings",
            "organization": organization,
            "profile_form": profile_form,
            "certificate_form": certificate_form,
            "numbering_form": numbering_form,
            "file_form": file_form,
            "smtp_form": smtp_form,
            "request_number_preview": organization.build_request_number(1),
        },
    )


@login_required
def organization_profile_update(request):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can update organization profile.")
        return redirect("dashboard:home")

    organization = get_user_organization(request.user)

    if not organization:
        messages.error(request, "Organization not found.")
        return redirect("dashboard:home")

    if request.method != "POST":
        return redirect("organizations:settings")

    form = OrganizationProfileSettingsForm(
        request.POST,
        request.FILES,
        instance=organization,
    )

    if form.is_valid():
        form.save()

        create_audit_log(
            request=request,
            organization=organization,
            action=AuditAction.UPDATED,
            model_name="Organization",
            object_id=organization.pk,
            message=f"Organization profile updated for '{organization.name}'.",
            extra_data={
                "name": organization.name,
                "email": organization.email,
                "phone": organization.phone,
                "address": organization.address,
                "has_logo": bool(organization.logo),
            },
        )

        messages.success(request, "Organization profile updated successfully.")
    else:
        messages.error(request, "Please correct errors in organization profile form.")

    return redirect("organizations:settings")


@login_required
def organization_certificate_update(request):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can update certificate branding.")
        return redirect("dashboard:home")

    organization = get_user_organization(request.user)

    if not organization:
        messages.error(request, "Organization not found.")
        return redirect("dashboard:home")

    if request.method != "POST":
        return redirect("organizations:settings")

    form = OrganizationCertificateSettingsForm(
        request.POST,
        request.FILES,
        instance=organization,
    )

    if form.is_valid():
        form.save()

        create_audit_log(
            request=request,
            organization=organization,
            action=AuditAction.UPDATED,
            model_name="Organization",
            object_id=organization.pk,
            message=f"Certificate branding settings updated for '{organization.name}'.",
            extra_data={
                "has_seal": bool(organization.seal_image),
                "certificate_header_text": organization.certificate_header_text,
                "certificate_footer_text": organization.certificate_footer_text,
                "certificate_signing_enabled": organization.certificate_signing_enabled,
            },
        )

        messages.success(request, "Certificate branding settings updated successfully.")
    else:
        messages.error(request, "Please correct errors in certificate branding form.")

    return redirect("organizations:settings")


@login_required
def organization_numbering_update(request):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can update numbering settings.")
        return redirect("dashboard:home")

    organization = get_user_organization(request.user)

    if not organization:
        messages.error(request, "Organization not found.")
        return redirect("dashboard:home")

    if request.method != "POST":
        return redirect("organizations:settings")

    form = OrganizationApprovalNumberingForm(
        request.POST,
        instance=organization,
    )

    if form.is_valid():
        form.save()

        create_audit_log(
            request=request,
            organization=organization,
            action=AuditAction.UPDATED,
            model_name="Organization",
            object_id=organization.pk,
            message=f"Approval numbering settings updated for '{organization.name}'.",
            extra_data={
                "approval_number_prefix": organization.approval_number_prefix,
                "approval_number_padding": organization.approval_number_padding,
                "approval_number_include_year": organization.approval_number_include_year,
                "preview": organization.build_request_number(1),
            },
        )

        messages.success(request, "Approval numbering settings updated successfully.")
    else:
        messages.error(request, "Please correct errors in numbering settings form.")

    return redirect("organizations:settings")


@login_required
def organization_file_settings_update(request):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can update file settings.")
        return redirect("dashboard:home")

    organization = get_user_organization(request.user)

    if not organization:
        messages.error(request, "Organization not found.")
        return redirect("dashboard:home")

    if request.method != "POST":
        return redirect("organizations:settings")

    form = OrganizationFileSettingsForm(
        request.POST,
        instance=organization,
    )

    if form.is_valid():
        form.save()

        create_audit_log(
            request=request,
            organization=organization,
            action=AuditAction.UPDATED,
            model_name="Organization",
            object_id=organization.pk,
            message=f"File upload settings updated for '{organization.name}'.",
            extra_data={
                "allowed_file_extensions": organization.allowed_file_extensions,
                "max_upload_size_mb": organization.max_upload_size_mb,
            },
        )

        messages.success(request, "File upload settings updated successfully.")
    else:
        messages.error(request, "Please correct errors in file settings form.")

    return redirect("organizations:settings")


@login_required
def organization_smtp_update(request):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can update SMTP settings.")
        return redirect("dashboard:home")

    organization = get_user_organization(request.user)

    if not organization:
        messages.error(request, "Organization not found.")
        return redirect("dashboard:home")

    if request.method != "POST":
        return redirect("organizations:settings")

    form = OrganizationSMTPSettingsForm(
        request.POST,
        instance=organization,
    )

    if form.is_valid():
        form.save()

        create_audit_log(
            request=request,
            organization=organization,
            action=AuditAction.UPDATED,
            model_name="Organization",
            object_id=organization.pk,
            message=f"SMTP settings updated for '{organization.name}'.",
            extra_data={
                "use_custom_smtp": organization.use_custom_smtp,
                "smtp_host": organization.smtp_host,
                "smtp_port": organization.smtp_port,
                "smtp_username": organization.smtp_username,
                "smtp_from_email": organization.smtp_from_email,
                "smtp_from_name": organization.smtp_from_name,
                "smtp_use_tls": organization.smtp_use_tls,
                "smtp_use_ssl": organization.smtp_use_ssl,
            },
        )

        messages.success(request, "SMTP settings updated successfully.")
    else:
        messages.error(request, "Please correct errors in SMTP settings form.")

    return redirect("organizations:settings")


@login_required
def organization_smtp_test(request):
    if not is_org_admin(request.user):
        messages.error(request, "Only organization admins can test SMTP settings.")
        return redirect("dashboard:home")

    organization = get_user_organization(request.user)

    if not organization:
        messages.error(request, "Organization not found.")
        return redirect("dashboard:home")

    if request.method != "POST":
        return redirect("organizations:settings")

    if not organization.use_custom_smtp:
        messages.error(request, "Custom SMTP is disabled.")
        return redirect("organizations:settings")

    try:
        connection = get_connection(
            host=organization.smtp_host,
            port=organization.smtp_port,
            username=organization.smtp_username,
            password=organization.smtp_password,
            use_tls=organization.smtp_use_tls,
            use_ssl=organization.smtp_use_ssl,
            timeout=15,
        )

        subject = "DocFlow AI SMTP Test"
        to_email = request.user.email
        from_email = organization.smtp_from_email

        html_body = render_to_string(
            "organizations/emails/smtp_test_email.html",
            {
                "organization": organization,
                "user": request.user,
            },
        )

        text_body = strip_tags(html_body)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=f"{organization.smtp_from_name} <{from_email}>",
            to=[to_email],
            connection=connection,
        )

        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)

        create_audit_log(
            request=request,
            organization=organization,
            action=AuditAction.UPDATED,
            model_name="Organization",
            object_id=organization.pk,
            message=f"SMTP test email sent for '{organization.name}'.",
            extra_data={
                "to": to_email,
                "smtp_host": organization.smtp_host,
            },
        )

        messages.success(request, f"SMTP test email sent to {to_email}.")

    except Exception as exc:
        create_audit_log(
            request=request,
            organization=organization,
            action=AuditAction.UPDATED,
            model_name="Organization",
            object_id=organization.pk,
            message=f"SMTP test failed for '{organization.name}'.",
            extra_data={
                "error": str(exc),
                "smtp_host": organization.smtp_host,
            },
        )

        messages.error(request, f"SMTP test failed: {exc}")

    return redirect("organizations:settings")