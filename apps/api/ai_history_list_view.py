from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.document_common import (
    can_view_version_history,
    get_visible_attachment,
)
from apps.api.pagination import DefaultPagePagination
from apps.api.permissions import HasActiveWorkspace


def serialize_ai_run(item):
    return {
        "id": item.pk,
        "version_id": item.version_id,
        "success": item.success,
        "source_text_type": item.source_text_type,
        "source_text_length": len(item.source_text or ""),
        "ai_summary": item.ai_summary,
        "ai_category": item.ai_category,
        "risk_level": item.risk_level,
        "processing_time_ms": item.processing_time_ms,
        "processed_by": item.processed_by.display_name if item.processed_by_id else None,
        "created_at": item.created_at.isoformat(),
    }


class AttachmentAIHistoryListAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, attachment_pk):
        attachment = get_visible_attachment(request.user, attachment_pk)
        if not attachment:
            return Response({"detail": "Not found."}, status=404)
        if not can_view_version_history(request.user, attachment):
            return Response({"detail": "You do not have access to AI processing history."}, status=403)
        history = attachment.ai_processing_history.select_related(
            "processed_by", "version"
        ).order_by("-created_at")
        paginator = DefaultPagePagination()
        page = paginator.paginate_queryset(history, request, view=self)
        return paginator.get_paginated_response([serialize_ai_run(item) for item in page])
