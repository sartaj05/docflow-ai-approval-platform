import hashlib
import secrets

from django.urls import reverse

from apps.reports.models import ApprovalCertificateSignature


def generate_verification_code():
    return f"CERT-{secrets.token_hex(6).upper()}"


def build_certificate_hash(document_request, verification_code):
    raw = "|".join(
        [
            str(document_request.pk),
            document_request.request_number,
            document_request.title,
            str(document_request.organization_id),
            str(document_request.approved_at),
            verification_code,
        ]
    )

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_final_approver(document_request):
    final_step = (
        document_request.approval_steps
        .select_related("assigned_to", "assigned_to__profile")
        .filter(status="APPROVED")
        .order_by("-step_order")
        .first()
    )

    if final_step and final_step.assigned_to:
        return final_step.assigned_to

    return None


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


def build_verification_url(request, certificate_signature):
    path = reverse(
        "reports:verify_certificate",
        kwargs={
            "verification_code": certificate_signature.verification_code,
        },
    )

    return request.build_absolute_uri(path)


def create_or_get_certificate_signature(document_request, request=None):
    existing = getattr(document_request, "certificate_signature", None)

    if existing:
        return existing, False

    verification_code = generate_verification_code()
    signer = get_final_approver(document_request)

    signed_by_name = ""
    signed_by_role = ""

    if signer:
        signed_by_name = signer.display_name

        profile = getattr(signer, "profile", None)

        if profile:
            signed_by_role = profile.certificate_signature_title

    organization_name = ""

    if document_request.organization:
        organization_name = document_request.organization.name

    certificate_hash = build_certificate_hash(
        document_request=document_request,
        verification_code=verification_code,
    )

    certificate_signature = ApprovalCertificateSignature.objects.create(
        document_request=document_request,
        verification_code=verification_code,
        signed_by=signer,
        signed_by_name=signed_by_name,
        signed_by_role=signed_by_role,
        organization_name=organization_name,
        certificate_hash=certificate_hash,
        ip_address=get_client_ip(request) if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
    )

    if request:
        certificate_signature.verification_url = build_verification_url(
            request=request,
            certificate_signature=certificate_signature,
        )
        certificate_signature.save(
            update_fields=[
                "verification_url",
            ]
        )

    return certificate_signature, True