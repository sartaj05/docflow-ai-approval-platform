from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import DefaultPagePagination
from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.approvals.models import ApprovalAction, ApprovalActionType


class RequestApprovalActionsAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        actions = document_request.approval_actions.select_related(
            "action_by", "step"
        ).order_by("-created_at")
        action_type = request.query_params.get("action_type", "").strip().upper()
        if action_type:
            allowed = {value for value, _ in ApprovalActionType.choices}
            if action_type not in allowed:
                return Response({"detail": "Invalid action_type filter.", "allowed": sorted(allowed)}, status=400)
            actions = actions.filter(action_type=action_type)
        paginator = DefaultPagePagination()
        page = paginator.paginate_queryset(actions, request, view=self)
        return paginator.get_paginated_response([{
            "id": item.pk,
            "action_type": item.action_type,
            "step_id": item.step_id,
            "step_order": item.step.step_order if item.step_id else None,
            "actor": item.action_by.display_name if item.action_by_id else None,
            "comment": item.comment,
            "old_status": item.old_status,
            "new_status": item.new_status,
            "created_at": item.created_at.isoformat(),
        } for item in page])
