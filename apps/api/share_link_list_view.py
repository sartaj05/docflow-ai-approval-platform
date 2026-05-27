from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace
from apps.api.share_common import (
    can_manage_share_links,
    get_share_request,
    serialize_share_link,
)


class RequestShareLinkListAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, pk):
        document_request = get_share_request(request.user, pk)
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        if not can_manage_share_links(request.user, document_request):
            return Response({"detail": "You cannot manage share links for this request."}, status=403)
        links = document_request.share_links.order_by("-created_at")
        return Response([serialize_share_link(item, request) for item in links])
