from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.discussion_common import DiscussionCommentInputSerializer, create_comment, serialize_comment
from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.approvals.models import RequestDiscussionComment


class RequestDiscussionReplyView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, pk, comment_pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        parent = RequestDiscussionComment.objects.filter(
            pk=comment_pk, request=document_request, is_deleted=False
        ).first()
        if not parent:
            return Response({"detail": "Comment not found."}, status=404)
        replies = parent.replies.select_related("author").prefetch_related("mentioned_users", "attachments")
        return Response([serialize_comment(item) for item in replies])

    def post(self, request, pk, comment_pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        parent = RequestDiscussionComment.objects.filter(
            pk=comment_pk, request=document_request, is_deleted=False
        ).first()
        if not parent:
            return Response({"detail": "Comment not found."}, status=404)
        serializer = DiscussionCommentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = create_comment(
            request=request,
            document_request=document_request,
            message=serializer.validated_data["message"],
            parent=parent,
        )
        return Response(serialize_comment(comment), status=201)
