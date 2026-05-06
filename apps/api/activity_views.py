from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.approvals.models import RequestWatcher
from apps.approvals.services.activity_timeline import build_request_activity_timeline
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log


class WatchRequestInputSerializer(serializers.Serializer):
    watching = serializers.BooleanField()


def get_request_or_not_found(user, pk):
    document_request = scoped_requests(user).filter(pk=pk).first()
    return document_request


class RequestActivityView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, pk):
        document_request = get_request_or_not_found(request.user, pk)
        if not document_request:
            return Response({"detail": "Not found."}, status=404)

        items = build_request_activity_timeline(document_request, limit=120)
        return Response([
            {
                "timestamp": item.timestamp.isoformat(),
                "activity_type": item.activity_type,
                "title": item.title,
                "description": item.description,
                "actor": (
                    item.actor.display_name
                    if item.actor and hasattr(item.actor, "display_name")
                    else None
                ),
                "badge": item.badge,
                "meta": item.meta or {},
            }
            for item in items
        ])


class RequestWatchView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request, pk):
        document_request = get_request_or_not_found(request.user, pk)
        if not document_request:
            return Response({"detail": "Not found."}, status=404)

        serializer = WatchRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        watching = serializer.validated_data["watching"]
        watcher = RequestWatcher.objects.filter(
            request=document_request,
            user=request.user,
        ).first()
        changed = False
        if watching and not watcher:
            watcher = RequestWatcher.objects.create(
                request=document_request,
                user=request.user,
                is_active=True,
            )
            changed = True
        elif watcher and watcher.is_active != watching:
            watcher.is_active = watching
            watcher.save(update_fields=["is_active", "updated_at"])
            changed = True

        if changed:
            verb = "started watching" if watching else "stopped watching"
            create_audit_log(
                request=request,
                organization=document_request.organization,
                action=AuditAction.UPDATED,
                model_name="RequestWatcher",
                object_id=watcher.pk,
                message=f"{request.user.display_name} {verb} {document_request.request_number} through the API.",
                extra_data={
                    "request_id": document_request.pk,
                    "watching": watching,
                },
            )

        return Response({
            "request_id": document_request.pk,
            "watching": bool(watcher and watcher.is_active),
            "active_watcher_count": document_request.watchers.filter(is_active=True).count(),
        })
