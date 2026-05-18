from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User, UserRole
from apps.api.delegation_list_view import can_manage_delegations, serialize_delegation
from apps.api.permissions import HasActiveWorkspace, get_user_organization
from apps.approvals.models import ApprovalDelegation
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log


DELEGATABLE_ROLES = {UserRole.ORG_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.APPROVER}


class DelegationCreateSerializer(serializers.Serializer):
    delegator_id = serializers.IntegerField()
    delegate_to_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        organization = self.context["organization"]
        eligible = User.objects.filter(
            is_active=True,
            profile__organization=organization,
            profile__is_active=True,
            profile__role__in=DELEGATABLE_ROLES,
        )
        delegator = eligible.filter(pk=attrs["delegator_id"]).first()
        delegate = eligible.filter(pk=attrs["delegate_to_id"]).first()
        if not delegator or not delegate:
            raise serializers.ValidationError("Both users must be active eligible users in this organization.")
        if delegator.pk == delegate.pk:
            raise serializers.ValidationError("A user cannot delegate approval to themselves.")
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "End date must be on or after the start date."})
        attrs["delegator"] = delegator
        attrs["delegate_to"] = delegate
        return attrs


class DelegationCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request):
        if not can_manage_delegations(request.user):
            return Response({"detail": "You do not have permission to create delegations."}, status=403)
        organization = get_user_organization(request.user)
        serializer = DelegationCreateSerializer(
            data=request.data, context={"organization": organization}
        )
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        item = ApprovalDelegation.objects.create(
            organization=organization,
            delegator=values["delegator"],
            delegate_to=values["delegate_to"],
            start_date=values["start_date"],
            end_date=values["end_date"],
            reason=values.get("reason", "").strip(),
            created_by=request.user,
        )
        create_audit_log(
            request=request,
            organization=organization,
            action=AuditAction.CREATED,
            model_name="ApprovalDelegation",
            object_id=item.pk,
            message="Approval delegation created through the API.",
            extra_data={"delegator_id": item.delegator_id, "delegate_to_id": item.delegate_to_id},
        )
        return Response(serialize_delegation(item), status=201)
