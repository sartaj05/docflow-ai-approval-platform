from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace, scoped_requests


class RequestWatchersAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        watchers = document_request.watchers.filter(is_active=True).select_related("user", "user__profile")
        return Response([{
            "user_id": item.user_id,
            "name": item.user.display_name,
            "username": item.user.get_username(),
            "role": item.user.profile.role if getattr(item.user, "profile", None) else None,
            "since": item.created_at.isoformat(),
        } for item in watchers])
