from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.api.permissions import HasActiveWorkspace, get_user_organization
from apps.approvals.models import ApprovalDelegation


def can_manage_delegations(user):
    profile = getattr(user, "profile", None)
    return bool(profile and profile.is_active and profile.role in {
        UserRole.ORG_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.APPROVER,
    })


def serialize_delegation(item):
    return {
        "id": item.pk,
        "delegator": {"id": item.delegator_id, "name": item.delegator.display_name},
        "delegate_to": {"id": item.delegate_to_id, "name": item.delegate_to.display_name},
        "reason": item.reason,
        "start_date": item.start_date.isoformat(),
        "end_date": item.end_date.isoformat(),
        "is_active": item.is_active,
        "is_currently_active": item.is_currently_active,
    }


class DelegationListAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        if not can_manage_delegations(request.user):
            return Response({"detail": "You do not have access to delegations."}, status=403)
        organization = get_user_organization(request.user)
        if not organization:
            return Response([])
        delegations = ApprovalDelegation.objects.filter(
            organization=organization,
        ).select_related("delegator", "delegate_to").order_by("-start_date", "-created_at")
        return Response([serialize_delegation(item) for item in delegations])
