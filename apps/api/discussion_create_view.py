from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.discussion_common import DiscussionCommentInputSerializer, create_comment, serialize_comment
from apps.api.permissions import HasActiveWorkspace, scoped_requests


class RequestDiscussionCreateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request, pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        serializer = DiscussionCommentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = create_comment(
            request=request,
            document_request=document_request,
            message=serializer.validated_data["message"],
        )
        return Response(serialize_comment(comment), status=201)
