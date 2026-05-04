from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.api.serializers import RequestListSerializer


class RequestListView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        requests = scoped_requests(request.user)
        serializer = RequestListSerializer(requests, many=True)
        return Response(serializer.data)
