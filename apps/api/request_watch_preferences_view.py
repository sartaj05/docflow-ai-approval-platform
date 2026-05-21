from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.approvals.models import RequestWatcher
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log


class WatchPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestWatcher
        fields = [
            "receive_comment_notifications",
            "receive_document_notifications",
            "receive_approval_notifications",
            "receive_ai_notifications",
            "receive_certificate_notifications",
            "receive_reminder_notifications",
        ]


class RequestWatchPreferencesAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get_watcher(self, user, pk):
        document_request = scoped_requests(user).filter(pk=pk).first()
        if not document_request:
            return None, None
        watcher = RequestWatcher.objects.filter(request=document_request, user=user).first()
        return document_request, watcher

    def get(self, request, pk):
        document_request, watcher = self.get_watcher(request.user, pk)
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        if not watcher or not watcher.is_active:
            return Response({"detail": "You are not watching this request."}, status=409)
        return Response(WatchPreferencesSerializer(watcher).data)

    def patch(self, request, pk):
        document_request, watcher = self.get_watcher(request.user, pk)
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        if not watcher or not watcher.is_active:
            return Response({"detail": "Start watching this request before changing preferences."}, status=409)
        serializer = WatchPreferencesSerializer(watcher, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.UPDATED,
            model_name="RequestWatcher",
            object_id=watcher.pk,
            message=f"Watch notification preferences updated for {document_request.request_number} through the API.",
            extra_data={"fields": list(serializer.validated_data)},
        )
        return Response(serializer.data)
