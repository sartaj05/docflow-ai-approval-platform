from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User, UserRole
from apps.api.delegation_list_view import can_manage_delegations
from apps.api.permissions import HasActiveWorkspace, get_user_organization


class DelegationCandidatesAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        if not can_manage_delegations(request.user):
            return Response({"detail": "You do not have access to the delegation directory."}, status=403)
        organization = get_user_organization(request.user)
        users = User.objects.filter(
            is_active=True,
            profile__organization=organization,
            profile__is_active=True,
            profile__role__in=[UserRole.ORG_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.APPROVER],
        ).select_related("profile").order_by("full_name", "username")
        return Response([{
            "id": user.pk,
            "username": user.get_username(),
            "name": user.display_name,
            "role": user.profile.role,
            "department": user.profile.department.name if user.profile.department_id else None,
        } for user in users])
