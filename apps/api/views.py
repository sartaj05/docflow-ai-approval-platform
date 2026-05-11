from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace


class APIRootView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        return Response({
            "name": "DocFlow AI API",
            "version": "v1",
            "endpoints": {
                "requests": request.build_absolute_uri("requests/"),
                "workflows": request.build_absolute_uri("workflows/"),
                "departments": request.build_absolute_uri("departments/"),
                "approval_inbox": request.build_absolute_uri("inbox/"),
                "bulk_approval_action": request.build_absolute_uri("inbox/bulk-action/"),
                "notifications": request.build_absolute_uri("notifications/"),
                "reports": request.build_absolute_uri("reports/summary/"),
                "schema": request.build_absolute_uri("schema/"),
                "token": request.build_absolute_uri("auth/token/"),
            },
        })
