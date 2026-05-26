from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.ai_history_list_view import serialize_ai_run
from apps.api.document_common import (
    can_view_version_history,
    get_visible_attachment,
)
from apps.api.permissions import HasActiveWorkspace
from apps.documents.models import DocumentAIProcessingHistory


class AttachmentAIHistoryDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, attachment_pk, history_pk):
        attachment = get_visible_attachment(request.user, attachment_pk)
        if not attachment:
            return Response({"detail": "Not found."}, status=404)
        if not can_view_version_history(request.user, attachment):
            return Response({"detail": "You do not have access to AI processing history."}, status=403)
        item = DocumentAIProcessingHistory.objects.filter(
            pk=history_pk, attachment=attachment
        ).select_related("processed_by", "version").first()
        if not item:
            return Response({"detail": "AI run not found."}, status=404)
        return Response({
            **serialize_ai_run(item),
            "ai_extracted_data": item.ai_extracted_data or {},
            "risk_notes": item.risk_notes,
        })
