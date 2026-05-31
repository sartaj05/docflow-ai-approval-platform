from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import DefaultPagePagination
from apps.api.permissions import HasActiveWorkspace
from apps.notifications.models import NotificationDeliveryLog, NotificationDeliveryStatus


class NotificationDeliveryHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        deliveries = NotificationDeliveryLog.objects.filter(
            recipient=request.user
        ).order_by("-created_at")
        status_filter = request.query_params.get("status", "").strip().upper()
        if status_filter:
            allowed = {value for value, _ in NotificationDeliveryStatus.choices}
            if status_filter not in allowed:
                return Response({"detail": "Invalid status filter.", "allowed": sorted(allowed)}, status=400)
            deliveries = deliveries.filter(status=status_filter)
        paginator = DefaultPagePagination()
        page = paginator.paginate_queryset(deliveries, request, view=self)
        return paginator.get_paginated_response([{
            "id": item.pk,
            "channel": item.channel,
            "status": item.status,
            "notification_type": item.notification_type,
            "subject": item.subject,
            "recipient_email": item.recipient_email,
            "retry_count": item.retry_count,
            "max_retries": item.max_retries,
            "error": item.error_message[:300],
            "created_at": item.created_at.isoformat(),
            "last_attempt_at": item.last_attempt_at.isoformat() if item.last_attempt_at else None,
            "sent_at": item.sent_at.isoformat() if item.sent_at else None,
        } for item in page])
