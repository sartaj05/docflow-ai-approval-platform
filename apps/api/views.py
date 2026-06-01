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
                "request_archive": request.build_absolute_uri("requests/{id}/archive/"),
                "schema": request.build_absolute_uri("schema/"),
                "token": request.build_absolute_uri("auth/token/"),
                "profile": request.build_absolute_uri("profile/"),
                "search": request.build_absolute_uri("search/"),
                "audit_logs": request.build_absolute_uri("audit-logs/"),
                "delegations": request.build_absolute_uri("delegations/"),
                "policies": request.build_absolute_uri("policies/"),
                "policy_evaluations": request.build_absolute_uri("policy-evaluations/"),
                "document_versions": request.build_absolute_uri("attachments/{id}/versions/"),
                "share_links": request.build_absolute_uri("requests/{id}/share-links/"),
                "public_shares": request.build_absolute_uri("share/{token}/summary/"),
                "notification_deliveries": request.build_absolute_uri("notifications/deliveries/"),
                "approval_reminders": request.build_absolute_uri("reminders/"),
            },
        })
