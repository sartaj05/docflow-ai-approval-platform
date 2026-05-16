from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.discussion_common import serialize_comment
from apps.api.permissions import HasActiveWorkspace, scoped_requests


class RequestDiscussionListView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        comments = document_request.discussion_comments.filter(parent__isnull=True).select_related("author").prefetch_related("mentioned_users", "attachments")
        return Response([serialize_comment(item) for item in comments])
