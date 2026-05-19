from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.api.delegation_list_view import serialize_delegation
from apps.api.permissions import HasActiveWorkspace, get_user_organization
from apps.approvals.models import ApprovalDelegation
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log


class DelegationDeactivateAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request, pk):
        profile = getattr(request.user, "profile", None)
        organization = get_user_organization(request.user)
        query = ApprovalDelegation.objects.select_related("delegator", "delegate_to").filter(pk=pk)
        if not request.user.is_superuser:
            query = query.filter(organization=organization)
        item = query.first()
        if not item:
            return Response({"detail": "Not found."}, status=404)
        is_admin = bool(profile and profile.role == UserRole.ORG_ADMIN)
        if not request.user.is_superuser and not is_admin and item.delegator_id != request.user.pk:
            return Response({"detail": "Only the delegator or organization admin can deactivate this delegation."}, status=403)
        if not item.is_active:
            return Response({"detail": "Delegation is already inactive."}, status=409)
        item.is_active = False
        item.save(update_fields=["is_active", "updated_at"])
        create_audit_log(
            request=request,
            organization=item.organization,
            action=AuditAction.UPDATED,
            model_name="ApprovalDelegation",
            object_id=item.pk,
            message="Approval delegation deactivated through the API.",
            extra_data={"is_active": False},
        )
        return Response(serialize_delegation(item))
