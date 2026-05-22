from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.approvals.models import RequestStatus
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.reports.services.pdf_generator import generate_approval_certificate_pdf
from apps.reports.services.signature_service import (
    build_verification_url,
    create_or_get_certificate_signature,
)


class RequestCertificateDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        if document_request.status != RequestStatus.APPROVED:
            return Response({"detail": "Certificates are available after approval."}, status=409)
        signature, created = create_or_get_certificate_signature(document_request, request=request)
        if not signature.verification_url:
            signature.verification_url = build_verification_url(request, signature)
            signature.save(update_fields=["verification_url"])
        pdf = generate_approval_certificate_pdf(
            document_request=document_request,
            request=request,
            certificate_signature=signature,
            verification_url=signature.verification_url,
        )
        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.PRINTED,
            model_name="ApprovalCertificateSignature",
            object_id=signature.pk,
            message=f"Approval certificate downloaded through the API for {document_request.request_number}.",
            extra_data={"verification_code": signature.verification_code, "created": created},
        )
        response = HttpResponse(pdf.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{document_request.request_number}_certificate.pdf"'
        return response
