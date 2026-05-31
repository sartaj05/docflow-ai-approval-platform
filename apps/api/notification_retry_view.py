from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.notifications.models import NotificationDeliveryLog
from apps.notifications.services.delivery_service import retry_delivery


class NotificationDeliveryRetryAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request, delivery_pk):
        delivery = NotificationDeliveryLog.objects.select_related(
            "organization", "notification"
        ).filter(pk=delivery_pk, recipient=request.user).first()
        if not delivery:
            return Response({"detail": "Not found."}, status=404)
        if not delivery.can_retry:
            return Response({"detail": "This delivery cannot be retried."}, status=409)
        result = retry_delivery(delivery)
        create_audit_log(
            request=request,
            organization=delivery.organization,
            action=AuditAction.UPDATED,
            model_name="NotificationDeliveryLog",
            object_id=delivery.pk,
            message="Notification delivery retried by its recipient through the API.",
            extra_data={"status": result.status, "retry_count": result.retry_count},
        )
        return Response({
            "id": result.pk,
            "status": result.status,
            "retry_count": result.retry_count,
            "can_retry": result.can_retry,
        })
