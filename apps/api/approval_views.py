from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.api.permissions import HasActiveWorkspace, get_user_organization
from apps.approvals.models import (
    ApprovalStep,
    ApprovalStepStatus,
)
from apps.approvals.services.action_engine import (
    approve_current_step,
    can_user_act_on_step,
    comment_on_current_step,
    reject_current_step,
)
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log


class StepActionInputSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, max_length=5000)


class ApprovalInboxItemSerializer(serializers.ModelSerializer):
    request_id = serializers.IntegerField(read_only=True)
    request_number = serializers.CharField(source="request.request_number", read_only=True)
    request_title = serializers.CharField(source="request.title", read_only=True)
    request_status = serializers.CharField(source="request.status", read_only=True)
    due_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = ApprovalStep
        fields = [
            "id",
            "request_id",
            "request_number",
            "request_title",
            "request_status",
            "step_order",
            "role_required",
            "status",
            "due_at",
            "is_overdue",
            "created_at",
        ]


class ApprovalInboxView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        organization = get_user_organization(request.user)
        if not organization or getattr(request.user, "profile", None).role not in {
            UserRole.APPROVER,
            UserRole.DEPARTMENT_HEAD,
            UserRole.ORG_ADMIN,
        }:
            return Response({"detail": "You do not have access to the approval inbox."}, status=403)

        steps = ApprovalStep.objects.select_related("request").filter(
            request__organization=organization,
            assigned_to=request.user,
            is_current=True,
            status=ApprovalStepStatus.PENDING,
        )
        return Response(ApprovalInboxItemSerializer(steps, many=True).data)


class ApprovalStepActionView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]
    action_type = ""

    def post(self, request, step_pk):
        step = (
            ApprovalStep.objects.select_related("request", "assigned_to")
            .filter(
                pk=step_pk,
                assigned_to=request.user,
                request__organization=get_user_organization(request.user),
                is_current=True,
                status=ApprovalStepStatus.PENDING,
            )
            .first()
        )
        if not step or not can_user_act_on_step(request.user, step):
            return Response({"detail": "Approval step not found or not assigned to you."}, status=404)

        serializer = StepActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.validated_data.get("comment", "").strip()

        try:
            if self.action_type == "approve":
                result = approve_current_step(step, request.user, comment=comment)
                audit_action = AuditAction.APPROVED
                message = f"Approval step {step.step_order} approved through the API."
            elif self.action_type == "reject":
                result = reject_current_step(step, request.user, comment=comment)
                audit_action = AuditAction.REJECTED
                message = f"Approval step {step.step_order} rejected through the API."
            else:
                result = comment_on_current_step(step, request.user, comment=comment)
                audit_action = AuditAction.COMMENTED
                message = f"Approval step {step.step_order} commented on through the API."
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        create_audit_log(
            request=request,
            organization=step.request.organization,
            action=audit_action,
            model_name="ApprovalStep",
            object_id=step.pk,
            message=message,
            extra_data={"request_id": step.request_id, "comment": comment},
        )
        step.refresh_from_db()
        return Response({
            "step_id": step.pk,
            "request_id": step.request_id,
            "step_status": step.status,
            "request_status": step.request.status,
            "comment": comment,
            "is_final": result.get("is_final") if isinstance(result, dict) else None,
        })


class ApproveStepView(ApprovalStepActionView):
    action_type = "approve"


class RejectStepView(ApprovalStepActionView):
    action_type = "reject"


class CommentOnStepView(ApprovalStepActionView):
    action_type = "comment"
