from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import DefaultPagePagination
from apps.api.permissions import HasActiveWorkspace
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.services.preference_service import get_notification_preferences


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "target_url",
            "object_type",
            "object_id",
            "is_read",
            "read_at",
            "actor_name",
            "created_at",
        ]

    def get_actor_name(self, obj):
        return obj.actor.display_name if obj.actor_id else None


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "in_app_enabled",
            "email_enabled",
            "watched_request_in_app",
            "watched_request_email",
            "comments_in_app",
            "comments_email",
            "approvals_in_app",
            "approvals_email",
            "documents_in_app",
            "documents_email",
            "ai_in_app",
            "ai_email",
            "reminders_in_app",
            "reminders_email",
            "certificates_in_app",
            "certificates_email",
            "daily_summary_email",
        ]


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        notifications = Notification.objects.select_related("actor").filter(
            recipient=request.user,
        )
        status_filter = request.query_params.get("status", "all").strip().lower()
        if status_filter == "unread":
            notifications = notifications.filter(is_read=False)
        elif status_filter == "read":
            notifications = notifications.filter(is_read=True)
        elif status_filter != "all":
            return Response(
                {"detail": "status must be all, read, or unread."},
                status=400,
            )

        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
        paginator = DefaultPagePagination()
        page = paginator.paginate_queryset(notifications, request, view=self)
        data = NotificationSerializer(page, many=True).data
        return Response({
            "count": notifications.count(),
            "unread_count": unread_count,
            "results": data,
        })


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request, notification_pk):
        notification = Notification.objects.filter(
            pk=notification_pk,
            recipient=request.user,
        ).first()
        if not notification:
            return Response({"detail": "Not found."}, status=404)
        notification.mark_as_read()
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request):
        updated = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        return Response({"marked_read": updated})


class NotificationPreferencesView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        preferences = get_notification_preferences(request.user)
        return Response(NotificationPreferenceSerializer(preferences).data)

    def patch(self, request):
        preferences = get_notification_preferences(request.user)
        serializer = NotificationPreferenceSerializer(
            preferences,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
