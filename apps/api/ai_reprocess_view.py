from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.document_common import can_correct_document_text, get_visible_attachment
from apps.api.permissions import HasActiveWorkspace
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.documents.services.ai_reprocessor import rerun_ai_for_attachment


class AttachmentAIReprocessAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request, attachment_pk):
        attachment = get_visible_attachment(request.user, attachment_pk)
        if not attachment:
            return Response({"detail": "Not found."}, status=404)
        if not can_correct_document_text(request.user, attachment):
            return Response({"detail": "You do not have permission to reprocess this document."}, status=403)
        result = rerun_ai_for_attachment(
            attachment=attachment,
            request=request,
            processed_by=request.user,
        )
        history = result.get("history")
        create_audit_log(
            request=request,
            organization=attachment.request.organization,
            action=AuditAction.UPDATED,
            model_name="DocumentAttachment",
            object_id=attachment.pk,
            message=f"AI reprocessing {'completed' if result.get('success') else 'failed'} through the API.",
            extra_data={
                "request_id": attachment.request_id,
                "history_id": history.pk if history else None,
                "success": result.get("success", False),
            },
        )
        attachment.refresh_from_db()
        return Response({
            "success": bool(result.get("success")),
            "history_id": history.pk if history else None,
            "ai_summary": attachment.ai_summary,
            "ai_category": attachment.ai_category,
            "risk_level": attachment.risk_level,
            "detail": result.get("error", "") if not result.get("success") else "AI processing completed.",
        })
