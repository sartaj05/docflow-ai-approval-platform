from apps.notifications.models import Notification


def notification_counts(request):
    if not request.user.is_authenticated:
        return {
            "unread_notifications_count": 0,
        }

    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).count()

    return {
        "unread_notifications_count": unread_count,
    }