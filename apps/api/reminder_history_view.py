from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import DefaultPagePagination
from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.approvals.models import ApprovalReminder


class ApprovalReminderHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        reminders = ApprovalReminder.objects.filter(
            request__in=scoped_requests(request.user)
        ).select_related("request", "step", "sent_to", "sent_by")
        request_id = request.query_params.get("request_id", "").strip()
        if request_id:
            if not request_id.isdigit():
                return Response({"detail": "request_id must be an integer."}, status=400)
            reminders = reminders.filter(request_id=int(request_id))
        paginator = DefaultPagePagination()
        page = paginator.paginate_queryset(reminders.order_by("-created_at"), request, view=self)
        return paginator.get_paginated_response([{
            "id": item.pk,
            "request_id": item.request_id,
            "request_number": item.request.request_number,
            "step_id": item.step_id,
            "step_order": item.step.step_order,
            "sent_to": item.sent_to.display_name if item.sent_to_id else None,
            "sent_by": item.sent_by.display_name if item.sent_by_id else None,
            "message": item.message,
            "created_at": item.created_at.isoformat(),
        } for item in page])
