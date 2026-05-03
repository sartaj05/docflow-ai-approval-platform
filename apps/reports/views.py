import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from apps.reports.forms import CertificateInvalidateForm
from apps.accounts.models import UserRole
from apps.approvals.models import DocumentRequest, RequestStatus, RiskLevel
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.reports.forms import RequestShareLinkForm
from apps.reports.models import ApprovalCertificateSignature, RequestShareLink
from apps.reports.services.archive_builder import build_request_archive_zip
from apps.reports.services.pdf_generator import (
    generate_approval_certificate_pdf,
    generate_request_summary_pdf,
)
from apps.reports.services.signature_service import create_or_get_certificate_signature
import io

import qrcode
from django.urls import reverse
def can_manage_certificates(user):
    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.AUDITOR,
    ]


def get_scoped_certificates(user):
    queryset = ApprovalCertificateSignature.objects.select_related(
        "document_request",
        "document_request__organization",
        "document_request__department",
        "document_request__created_by",
        "signed_by",
        "invalidated_by",
    )

    if user.is_superuser:
        return queryset

    profile = getattr(user, "profile", None)

    if not profile or not profile.organization:
        return ApprovalCertificateSignature.objects.none()

    return queryset.filter(
        document_request__organization=profile.organization,
    )

def build_certificate_verification_url(request, certificate_signature):
    if certificate_signature.verification_url:
        return certificate_signature.verification_url

    return request.build_absolute_uri(
        reverse(
            "reports:verify_certificate",
            args=[certificate_signature.verification_code],
        )
    )


def ensure_certificate_verification_url(request, certificate_signature):
    verification_url = build_certificate_verification_url(
        request,
        certificate_signature,
    )

    if certificate_signature.verification_url != verification_url:
        certificate_signature.verification_url = verification_url
        certificate_signature.save(update_fields=["verification_url"])

    return verification_url
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.reports.models import ApprovalCertificateSignature


def user_can_manage_certificates(user):
    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.AUDITOR,
    ]


def get_certificate_queryset_for_user(user):
    queryset = ApprovalCertificateSignature.objects.select_related(
        "document_request",
        "document_request__organization",
        "document_request__department",
        "document_request__created_by",
        "signed_by",
        "invalidated_by",
    )

    if user.is_superuser:
        return queryset

    profile = getattr(user, "profile", None)

    if not profile or not profile.organization:
        return queryset.none()

    return queryset.filter(
        document_request__organization=profile.organization,
    )


def build_public_certificate_url(request, certificate_signature):
    if certificate_signature.verification_url:
        return certificate_signature.verification_url

    return request.build_absolute_uri(
        reverse(
            "reports:verify_certificate",
            args=[certificate_signature.verification_code],
        )
    )


def ensure_public_certificate_url(request, certificate_signature):
    public_url = build_public_certificate_url(
        request=request,
        certificate_signature=certificate_signature,
    )

    if certificate_signature.verification_url != public_url:
        certificate_signature.verification_url = public_url
        certificate_signature.save(update_fields=["verification_url"])

    return public_url


@login_required
def certificate_list(request):
    if not user_can_manage_certificates(request.user):
        messages.error(request, "You do not have permission to view certificates.")
        return redirect("dashboard:home")

    queryset = get_certificate_queryset_for_user(request.user)

    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    organization = request.GET.get("organization", "").strip()

    if search:
        queryset = queryset.filter(
            Q(verification_code__icontains=search)
            | Q(certificate_uuid__icontains=search)
            | Q(certificate_hash__icontains=search)
            | Q(document_request__title__icontains=search)
            | Q(document_request__id__icontains=search)
            | Q(document_request__organization__name__icontains=search)
            | Q(signed_by_name__icontains=search)
            | Q(signed_by_role__icontains=search)
        )

    if status == "valid":
        queryset = queryset.filter(is_valid=True)

    if status == "invalid":
        queryset = queryset.filter(is_valid=False)

    if organization and request.user.is_superuser:
        queryset = queryset.filter(
            document_request__organization_id=organization,
        )

    certificates = queryset.order_by("-signed_at", "-created_at")

    valid_count = queryset.filter(is_valid=True).count()
    invalid_count = queryset.filter(is_valid=False).count()
    total_count = queryset.count()

    for certificate in certificates[:100]:
        ensure_public_certificate_url(
            request=request,
            certificate_signature=certificate,
        )

    return render(
        request,
        "reports/certificate_list.html",
        {
            "page_title": "Certificates",
            "certificates": certificates,
            "search": search,
            "status": status,
            "organization": organization,
            "total_count": total_count,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
        },
    )


@login_required
def certificate_detail(request, pk):
    if not user_can_manage_certificates(request.user):
        messages.error(request, "You do not have permission to view certificate details.")
        return redirect("dashboard:home")

    certificate_signature = get_object_or_404(
        get_certificate_queryset_for_user(request.user),
        pk=pk,
    )

    public_url = ensure_public_certificate_url(
        request=request,
        certificate_signature=certificate_signature,
    )

    document_request = certificate_signature.document_request

    approval_steps = document_request.approval_steps.select_related(
        "assigned_to",
    ).order_by("step_order")

    return render(
        request,
        "reports/certificate_detail.html",
        {
            "page_title": "Certificate Detail",
            "certificate_signature": certificate_signature,
            "document_request": document_request,
            "approval_steps": approval_steps,
            "public_url": public_url,
        },
    )


@login_required
def certificate_invalidate(request, pk):
    if not user_can_manage_certificates(request.user):
        messages.error(request, "You do not have permission to invalidate certificates.")
        return redirect("dashboard:home")

    certificate_signature = get_object_or_404(
        get_certificate_queryset_for_user(request.user),
        pk=pk,
    )

    if request.method != "POST":
        return redirect("reports:certificate_detail", pk=certificate_signature.pk)

    if not certificate_signature.is_valid:
        messages.warning(request, "This certificate is already invalidated.")
        return redirect("reports:certificate_detail", pk=certificate_signature.pk)

    reason = request.POST.get("reason", "").strip()

    if not reason:
        messages.error(request, "Invalidation reason is required.")
        return redirect("reports:certificate_detail", pk=certificate_signature.pk)

    certificate_signature.is_valid = False
    certificate_signature.invalidated_at = timezone.now()
    certificate_signature.invalidated_by = request.user
    certificate_signature.invalidation_reason = reason
    certificate_signature.save(
        update_fields=[
            "is_valid",
            "invalidated_at",
            "invalidated_by",
            "invalidation_reason",
        ]
    )

    create_audit_log(
        request=request,
        organization=certificate_signature.document_request.organization,
        action=AuditAction.UPDATED,
        model_name="ApprovalCertificateSignature",
        object_id=certificate_signature.pk,
        message=f"Certificate {certificate_signature.verification_code} invalidated.",
        extra_data={
            "verification_code": certificate_signature.verification_code,
            "request_number": certificate_signature.document_request.request_number,
            "reason": reason,
        },
    )

    messages.success(request, "Certificate invalidated successfully.")
    return redirect("reports:certificate_detail", pk=certificate_signature.pk)
# ==========================================================
# Share link helpers
# ==========================================================

def user_can_manage_share_links(user, document_request):
    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    if not profile:
        return False

    if profile.organization_id != document_request.organization_id:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.DEPARTMENT_HEAD,
        UserRole.AUDITOR,
    ] or document_request.created_by_id == user.id


def get_valid_public_share_link(token):
    share_link = get_object_or_404(
        RequestShareLink.objects.select_related(
            "document_request",
            "document_request__organization",
            "document_request__department",
            "document_request__created_by",
            "document_request__workflow",
            "created_by",
        ),
        token=token,
    )

    if not share_link.is_valid:
        return None, share_link

    if share_link.document_request.status != RequestStatus.APPROVED:
        return None, share_link

    return share_link, share_link


# ==========================================================
# Report permission helpers
# ==========================================================

def get_profile(user):
    return getattr(user, "profile", None)


def get_user_organization(user):
    if user.is_superuser:
        return None

    profile = get_profile(user)

    if not profile:
        return None

    return profile.organization


def can_view_reports(user):
    if user.is_superuser:
        return True

    profile = get_profile(user)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.DEPARTMENT_HEAD,
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

    queryset = DocumentRequest.objects.select_related(
        "organization",
        "department",
        "created_by",
        "workflow",
    ).filter(
        organization=profile.organization,
    )

    if profile.role == UserRole.ORG_ADMIN:
        return queryset

    if profile.role == UserRole.DEPARTMENT_HEAD:
        if profile.department:
            return queryset.filter(department=profile.department)

        return DocumentRequest.objects.none()

    if profile.role == UserRole.AUDITOR:
        return queryset

    return DocumentRequest.objects.none()


def get_request_for_report(user, pk):
    return get_object_or_404(
        get_scoped_requests(user),
        pk=pk,
    )


# ==========================================================
# Reports dashboard
# ==========================================================

@login_required
def reports_dashboard(request):
    if not can_view_reports(request.user):
        messages.error(request, "You do not have permission to view reports.")
        return redirect("dashboard:home")

    queryset = get_scoped_requests(request.user)

    total_requests = queryset.count()
    approved_requests = queryset.filter(status=RequestStatus.APPROVED).count()
    rejected_requests = queryset.filter(status=RequestStatus.REJECTED).count()
    pending_requests = queryset.filter(
        status__in=[
            RequestStatus.SUBMITTED,
            RequestStatus.IN_REVIEW,
        ]
    ).count()

    high_risk = queryset.filter(risk_level=RiskLevel.HIGH).count()
    medium_risk = queryset.filter(risk_level=RiskLevel.MEDIUM).count()
    low_risk = queryset.filter(risk_level=RiskLevel.LOW).count()

    department_rows = (
        queryset.values("department__name")
        .annotate(
            total=Count("id"),
            approved=Count("id", filter=Q(status=RequestStatus.APPROVED)),
            rejected=Count("id", filter=Q(status=RequestStatus.REJECTED)),
        )
        .order_by("-total")[:10]
    )

    recent_requests = queryset.order_by("-created_at")[:10]

    return render(
        request,
        "reports/dashboard.html",
        {
            "page_title": "Reports",
            "total_requests": total_requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "pending_requests": pending_requests,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "department_rows": department_rows,
            "recent_requests": recent_requests,
        },
    )


# ==========================================================
# Printable summary / PDFs
# ==========================================================

@login_required
def printable_request_summary(request, pk):
    document_request = get_request_for_report(request.user, pk)

    create_audit_log(
        request=request,
        organization=document_request.organization,
        action=AuditAction.PRINTED,
        model_name="DocumentRequest",
        object_id=document_request.pk,
        message=f"Printable summary opened for {document_request.request_number}.",
        extra_data={
            "request_number": document_request.request_number,
        },
    )

    return render(
        request,
        "reports/printable_request_summary.html",
        {
            "page_title": f"{document_request.request_number} Summary",
            "document_request": document_request,
            "attachments": document_request.attachments.select_related(
                "uploaded_by"
            ).order_by("created_at"),
            "approval_steps": document_request.approval_steps.select_related(
                "assigned_to"
            ).order_by("step_order"),
            "approval_actions": document_request.approval_actions.select_related(
                "action_by",
                "step",
            ).order_by("created_at"),
        },
    )


@login_required
def request_summary_pdf(request, pk):
    document_request = get_request_for_report(request.user, pk)

    pdf_buffer = generate_request_summary_pdf(
        document_request=document_request,
        request=request,
    )

    create_audit_log(
        request=request,
        organization=document_request.organization,
        action=AuditAction.PRINTED,
        model_name="DocumentRequest",
        object_id=document_request.pk,
        message=f"Request summary PDF downloaded for {document_request.request_number}.",
        extra_data={
            "request_number": document_request.request_number,
        },
    )

    response = HttpResponse(
        pdf_buffer.getvalue(),
        content_type="application/pdf",
    )

    filename = f"{document_request.request_number}_summary.pdf"

    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response

@login_required
def approval_certificate_pdf(request, pk):
    document_request = get_request_for_report(request.user, pk)

    if document_request.status != RequestStatus.APPROVED:
        messages.error(
            request,
            "Approval certificate can be downloaded only after request approval.",
        )
        return redirect("approvals:request_detail", pk=document_request.pk)

    certificate_signature, signature_created = create_or_get_certificate_signature(
        document_request=document_request,
        request=request,
    )

    verification_url = ensure_certificate_verification_url(
        request=request,
        certificate_signature=certificate_signature,
    )

    pdf_buffer = generate_approval_certificate_pdf(
        document_request=document_request,
        request=request,
        certificate_signature=certificate_signature,
        verification_url=verification_url,
    )

    create_audit_log(
        request=request,
        organization=document_request.organization,
        action=AuditAction.PRINTED,
        model_name="ApprovalCertificateSignature",
        object_id=certificate_signature.pk,
        message=f"Approval certificate PDF downloaded for {document_request.request_number}.",
        extra_data={
            "request_number": document_request.request_number,
            "status": document_request.status,
            "verification_code": certificate_signature.verification_code,
            "certificate_hash": certificate_signature.certificate_hash,
            "verification_url": verification_url,
            "signature_created": signature_created,
        },
    )

    response = HttpResponse(
        pdf_buffer.getvalue(),
        content_type="application/pdf",
    )

    filename = f"{document_request.request_number}_certificate.pdf"

    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response

# ==========================================================
# Request verification
# ==========================================================

def verify_request(request, pk):
    document_request = get_object_or_404(
        DocumentRequest.objects.select_related(
            "organization",
            "department",
            "created_by",
            "workflow",
        ),
        pk=pk,
    )

    return render(
        request,
        "reports/verify_request.html",
        {
            "page_title": "Verify Approval Request",
            "document_request": document_request,
            "approval_steps": document_request.approval_steps.select_related(
                "assigned_to"
            ).order_by("step_order"),
        },
    )

def verify_certificate(request, verification_code):
    certificate_signature = get_object_or_404(
        ApprovalCertificateSignature.objects.select_related(
            "document_request",
            "document_request__organization",
            "document_request__department",
            "document_request__created_by",
            "document_request__workflow",
            "signed_by",
            "invalidated_by",
        ),
        verification_code=verification_code,
    )

    verification_url = ensure_certificate_verification_url(
        request=request,
        certificate_signature=certificate_signature,
    )

    document_request = certificate_signature.document_request

    approval_steps = document_request.approval_steps.select_related(
        "assigned_to",
    ).order_by("step_order")

    return render(
        request,
        "reports/verify_certificate.html",
        {
            "page_title": "Verify Certificate",
            "certificate_signature": certificate_signature,
            "document_request": document_request,
            "approval_steps": approval_steps,
            "verification_url": verification_url,
        },
    )
def certificate_qr_png(request, verification_code):
    certificate_signature = get_object_or_404(
        ApprovalCertificateSignature,
        verification_code=verification_code,
    )

    verification_url = ensure_certificate_verification_url(
        request=request,
        certificate_signature=certificate_signature,
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=3,
    )

    qr.add_data(verification_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    return HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )
# ==========================================================
# Final archive ZIP
# ==========================================================

@login_required
def request_archive_zip(request, pk):
    document_request = get_object_or_404(
        DocumentRequest.objects.select_related(
            "organization",
            "department",
            "created_by",
            "workflow",
        ),
        pk=pk,
    )

    if not request.user.is_superuser:
        profile = getattr(request.user, "profile", None)

        if not profile or profile.organization_id != document_request.organization_id:
            messages.error(
                request,
                "You do not have permission to download this archive.",
            )
            return redirect("dashboard:home")

    if document_request.status != RequestStatus.APPROVED:
        messages.error(
            request,
            "Final archive can be downloaded only after approval.",
        )
        return redirect(
            "approvals:request_detail",
            pk=document_request.pk,
        )

    archive_buffer = build_request_archive_zip(document_request)

    filename = f"{document_request.request_number}_final_archive.zip".replace("/", "-")

    create_audit_log(
        request=request,
        organization=document_request.organization,
        action=AuditAction.UPDATED,
        model_name="DocumentRequest",
        object_id=document_request.pk,
        message=f"Final archive downloaded for {document_request.request_number}.",
        extra_data={
            "request_number": document_request.request_number,
            "filename": filename,
            "status": document_request.status,
        },
    )

    response = HttpResponse(
        archive_buffer.getvalue(),
        content_type="application/zip",
    )

    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response


# ==========================================================
# Secure share links
# ==========================================================

@login_required
def request_share_links(request, pk):
    document_request = get_object_or_404(
        DocumentRequest.objects.select_related(
            "organization",
            "department",
            "created_by",
            "workflow",
        ),
        pk=pk,
    )

    if not user_can_manage_share_links(request.user, document_request):
        messages.error(request, "You do not have permission to manage share links.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    share_links = document_request.share_links.select_related(
        "created_by",
        "revoked_by",
    ).order_by("-created_at")

    return render(
        request,
        "reports/share_link_list.html",
        {
            "page_title": "Secure Share Links",
            "document_request": document_request,
            "share_links": share_links,
        },
    )


@login_required
def request_share_link_create(request, pk):
    document_request = get_object_or_404(
        DocumentRequest.objects.select_related(
            "organization",
            "department",
            "created_by",
            "workflow",
        ),
        pk=pk,
    )

    if not user_can_manage_share_links(request.user, document_request):
        messages.error(request, "You do not have permission to create share links.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    if document_request.status != RequestStatus.APPROVED:
        messages.error(request, "Share links can be created only for approved requests.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    form = RequestShareLinkForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            share_link = form.save(commit=False)
            share_link.document_request = document_request
            share_link.created_by = request.user
            share_link.save()

            create_audit_log(
                request=request,
                organization=document_request.organization,
                action=AuditAction.CREATED,
                model_name="RequestShareLink",
                object_id=share_link.pk,
                message=f"Secure share link created for {document_request.request_number}.",
                extra_data={
                    "request_number": document_request.request_number,
                    "expires_at": str(share_link.expires_at),
                    "allow_summary_view": share_link.allow_summary_view,
                    "allow_archive_download": share_link.allow_archive_download,
                },
            )

            messages.success(request, "Secure share link created successfully.")
            return redirect("reports:request_share_links", pk=document_request.pk)

    return render(
        request,
        "reports/share_link_form.html",
        {
            "page_title": "Create Share Link",
            "form": form,
            "document_request": document_request,
        },
    )


@login_required
def request_share_link_revoke(request, pk, link_pk):
    document_request = get_object_or_404(
        DocumentRequest.objects.select_related(
            "organization",
        ),
        pk=pk,
    )

    share_link = get_object_or_404(
        RequestShareLink,
        pk=link_pk,
        document_request=document_request,
    )

    if not user_can_manage_share_links(request.user, document_request):
        messages.error(request, "You do not have permission to revoke share links.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    if request.method == "POST":
        share_link.revoke(user=request.user)

        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.UPDATED,
            model_name="RequestShareLink",
            object_id=share_link.pk,
            message=f"Secure share link revoked for {document_request.request_number}.",
            extra_data={
                "request_number": document_request.request_number,
                "token": share_link.token,
            },
        )

        messages.success(request, "Share link revoked successfully.")

    return redirect("reports:request_share_links", pk=document_request.pk)


def public_request_summary(request, token):
    valid_link, share_link = get_valid_public_share_link(token)

    if not valid_link:
        return render(
            request,
            "reports/public_link_invalid.html",
            {
                "page_title": "Invalid Share Link",
                "share_link": share_link,
            },
            status=403,
        )

    if not valid_link.allow_summary_view:
        return render(
            request,
            "reports/public_link_invalid.html",
            {
                "page_title": "Summary Not Allowed",
                "share_link": share_link,
                "message": "This share link does not allow summary viewing.",
            },
            status=403,
        )

    valid_link.mark_accessed()

    document_request = valid_link.document_request

    attachments = document_request.attachments.select_related(
        "uploaded_by",
    ).order_by("created_at")

    approval_steps = document_request.approval_steps.select_related(
        "assigned_to",
    ).order_by("step_order")

    approval_actions = document_request.approval_actions.select_related(
        "action_by",
        "step",
    ).order_by("created_at")

    return render(
        request,
        "reports/public_request_summary.html",
        {
            "page_title": document_request.request_number,
            "share_link": valid_link,
            "document_request": document_request,
            "attachments": attachments,
            "approval_steps": approval_steps,
            "approval_actions": approval_actions,
        },
    )


def public_request_archive(request, token):
    valid_link, share_link = get_valid_public_share_link(token)

    if not valid_link:
        return render(
            request,
            "reports/public_link_invalid.html",
            {
                "page_title": "Invalid Share Link",
                "share_link": share_link,
            },
            status=403,
        )

    if not valid_link.allow_archive_download:
        return render(
            request,
            "reports/public_link_invalid.html",
            {
                "page_title": "Archive Download Not Allowed",
                "share_link": share_link,
                "message": "This share link does not allow archive download.",
            },
            status=403,
        )

    valid_link.mark_accessed()

    document_request = valid_link.document_request

    archive_buffer = build_request_archive_zip(document_request)

    filename = f"{document_request.request_number}_shared_archive.zip".replace("/", "-")

    response = HttpResponse(
        archive_buffer.getvalue(),
        content_type="application/zip",
    )

    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response

@login_required
def approval_certificate_preview(request, pk):
    document_request = get_request_for_report(request.user, pk)

    if document_request.status != RequestStatus.APPROVED:
        messages.error(
            request,
            "Approval certificate can be viewed only after request approval.",
        )
        return redirect("approvals:request_detail", pk=document_request.pk)

    certificate_signature, signature_created = create_or_get_certificate_signature(
        document_request=document_request,
        request=request,
    )

    return render(
        request,
        "reports/approval_certificate.html",
        {
            "page_title": "Approval Certificate",
            "document_request": document_request,
            "certificate_signature": certificate_signature,
        },
    )
    
    
    
