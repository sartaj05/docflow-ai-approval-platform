from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.approvals.models import ApprovalStep, ApprovalStepStatus
from apps.approvals.services.reminder_engine import (
    can_send_reminder_for_step,
    send_approval_reminder,
)
from apps.approvals.services.watcher_service import (
    ACTIVITY_REMINDER,
    notify_request_watchers,
)
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log


class ReminderInputSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class ApprovalReminderSendAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request, step_pk):
        step = ApprovalStep.objects.select_related(
            "request", "assigned_to"
        ).filter(
            pk=step_pk,
            request__in=scoped_requests(request.user),
            status=ApprovalStepStatus.PENDING,
            is_current=True,
        ).first()
        if not step:
            return Response({"detail": "Not found."}, status=404)
        if not can_send_reminder_for_step(request.user, step):
            return Response({"detail": "You cannot send a reminder for this step."}, status=403)
        serializer = ReminderInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reminder = send_approval_reminder(
            approval_step=step,
            sent_by=request.user,
            message=serializer.validated_data.get("message", "").strip(),
        )
        notify_request_watchers(
            document_request=step.request,
            actor=request.user,
            activity_type=ACTIVITY_REMINDER,
            title=f"Reminder sent for {step.request.request_number}",
            message=f"{request.user.display_name} sent an approval reminder for {step.request.request_number}.",
            object_type="ApprovalReminder",
            object_id=reminder.pk,
        )
        create_audit_log(
            request=request,
            organization=step.request.organization,
            action=AuditAction.UPDATED,
            model_name="ApprovalReminder",
            object_id=reminder.pk,
            message=f"Reminder sent for {step.request.request_number} through the API.",
            extra_data={"request_id": step.request_id, "step_id": step.pk},
        )
        return Response({
            "id": reminder.pk,
            "request_id": reminder.request_id,
            "step_id": reminder.step_id,
            "sent_to": reminder.sent_to.display_name if reminder.sent_to_id else None,
            "created_at": reminder.created_at.isoformat(),
        }, status=201)
