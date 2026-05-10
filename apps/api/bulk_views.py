from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace, get_user_organization
from apps.approvals.models import ApprovalStep
from apps.approvals.services.action_engine import perform_bulk_step_action
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log


class BulkStepActionInputSerializer(serializers.Serializer):
    step_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=100,
    )
    action = serializers.ChoiceField(choices=["approve", "reject", "comment"])
    comment = serializers.CharField(required=False, allow_blank=True, max_length=5000)

    def validate_step_ids(self, values):
        if len(values) != len(set(values)):
            raise serializers.ValidationError("step_ids must not contain duplicates.")
        return values

    def validate(self, attrs):
        if attrs["action"] in {"reject", "comment"} and not attrs.get("comment", "").strip():
            raise serializers.ValidationError({
                "comment": "A non-empty comment is required for reject and comment actions.",
            })
        return attrs


class BulkApprovalActionView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request):
        serializer = BulkStepActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        step_ids = serializer.validated_data["step_ids"]
        action = serializer.validated_data["action"]
        comment = serializer.validated_data.get("comment", "").strip()
        organization = get_user_organization(request.user)

        available_ids = list(
            ApprovalStep.objects.filter(
                pk__in=step_ids,
                request__organization=organization,
                assigned_to=request.user,
                is_current=True,
                status="PENDING",
            ).values_list("pk", flat=True)
        )
        unavailable_ids = sorted(set(step_ids) - set(available_ids))
        summary = perform_bulk_step_action(
            user=request.user,
            step_ids=available_ids,
            action=action,
            comment=comment,
        )
        summary["requested"] = len(step_ids)
        if unavailable_ids:
            summary["failed"] += len(unavailable_ids)
            summary["errors"].extend(
                f"Step {step_id} is unavailable or not assigned to you."
                for step_id in unavailable_ids
            )

        action_map = {
            "approve": AuditAction.APPROVED,
            "reject": AuditAction.REJECTED,
            "comment": AuditAction.COMMENTED,
        }
        create_audit_log(
            request=request,
            organization=organization,
            action=action_map[action],
            model_name="ApprovalStepBulkAction",
            message=f"Bulk {action} action processed through the API.",
            extra_data={
                "requested": summary["requested"],
                "processed": summary["processed"],
                "failed": summary["failed"],
            },
        )
        return Response(summary)
