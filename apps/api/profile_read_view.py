from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace


class CurrentProfileView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        user = request.user
        profile = getattr(user, "profile", None)
        return Response({
            "id": user.pk,
            "username": user.get_username(),
            "email": user.email,
            "full_name": user.full_name,
            "organization": profile.organization.name if profile and profile.organization_id else None,
            "department": profile.department.name if profile and profile.department_id else None,
            "role": profile.role if profile else None,
            "phone": profile.phone if profile else "",
            "designation": profile.designation if profile else "",
        })
