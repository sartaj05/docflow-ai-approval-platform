from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.approvals.models import RequestStatus
from apps.reports.services.signature_service import create_or_get_certificate_signature


class RequestCertificateMetadataAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        if document_request.status != RequestStatus.APPROVED:
            return Response({"detail": "Certificates are available after approval."}, status=409)
        signature, _ = create_or_get_certificate_signature(document_request, request=request)
        return Response({
            "id": signature.pk,
            "request_id": document_request.pk,
            "request_number": document_request.request_number,
            "verification_code": signature.verification_code,
            "certificate_hash": signature.certificate_hash,
            "verification_url": signature.verification_url,
            "signed_by": signature.signed_by_name,
            "signed_by_role": signature.signed_by_role,
            "organization_name": signature.organization_name,
            "signed_at": signature.signed_at.isoformat(),
            "is_valid": signature.is_valid,
        })
