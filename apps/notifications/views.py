from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.notifications.models import (
    NotificationDeliveryChannel,
    NotificationDeliveryLog,
    NotificationDeliveryStatus,
)
from apps.notifications.tasks import retry_notification_delivery_task
from apps.notifications.models import NotificationDigestLog
from apps.notifications.services.digest_service import (
    get_user_digest_data,
    send_user_digest,
)
from apps.notifications.models import Notification
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.notifications.forms import NotificationPreferenceForm
from apps.notifications.services.preference_service import get_notification_preferences
def can_view_delivery_monitor(user):
    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.AUDITOR,
    ]
@login_required
def notification_list(request):
    notifications = (
        Notification.objects.select_related(
            "recipient",
            "actor",
            "organization",
        )
        .filter(recipient=request.user)
        .order_by("-created_at")
    )

    status = request.GET.get("status", "").strip()

    if status == "unread":
        notifications = notifications.filter(is_read=False)
    elif status == "read":
        notifications = notifications.filter(is_read=True)

    total_count = notifications.count()
    unread_count = notifications.filter(is_read=False).count()
    read_count = notifications.filter(is_read=True).count()

    return render(
        request,
        "notifications/notification_list.html",
        {
            "page_title": "Notifications",
            "notifications": notifications[:300],
            "status": status,
            "total_count": total_count,
            "unread_count": unread_count,
            "read_count": read_count,
        },
    )


@login_required
def notification_mark_read(request, pk):
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user,
    )

    notification.mark_as_read()

    next_url = notification.target_url or "notifications:list"

    if notification.target_url:
        return redirect(notification.target_url)

    return redirect(next_url)


@login_required
def notification_mark_all_read(request):
    if request.method != "POST":
        return redirect("notifications:list")

    Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(
        is_read=True,
        read_at=timezone.now(),
    )

    messages.success(request, "All notifications marked as read.")
    return redirect("notifications:list")


@login_required
def notification_preferences(request):
    preferences = get_notification_preferences(request.user)

    form = NotificationPreferenceForm(
        request.POST or None,
        instance=preferences,
    )

    if request.method == "POST":
        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Notification preferences updated successfully.",
            )
            return redirect("notifications:preferences")

    return render(
        request,
        "notifications/preferences.html",
        {
            "page_title": "Notification Preferences",
            "form": form,
            "preferences": preferences,
        },
    )
    
    
@login_required
def digest_preview(request):
    digest_type = request.GET.get(
        "type",
        NotificationDigestLog.DigestType.DAILY,
    )

    if digest_type not in [
        NotificationDigestLog.DigestType.DAILY,
        NotificationDigestLog.DigestType.WEEKLY,
    ]:
        digest_type = NotificationDigestLog.DigestType.DAILY

    data = get_user_digest_data(
        user=request.user,
        digest_type=digest_type,
    )

    digest_logs = (
        NotificationDigestLog.objects.filter(user=request.user)
        .order_by("-sent_at")[:10]
    )

    return render(
        request,
        "notifications/digest_preview.html",
        {
            "page_title": "Notification Digest",
            "digest_type": digest_type,
            "digest_data": data,
            "digest_logs": digest_logs,
        },
    )


@login_required
def send_test_digest(request):
    if request.method != "POST":
        return redirect("notifications:digest_preview")

    digest_type = request.POST.get(
        "digest_type",
        NotificationDigestLog.DigestType.DAILY,
    )

    if digest_type not in [
        NotificationDigestLog.DigestType.DAILY,
        NotificationDigestLog.DigestType.WEEKLY,
    ]:
        digest_type = NotificationDigestLog.DigestType.DAILY

    digest_log = send_user_digest(
        user=request.user,
        digest_type=digest_type,
        force=True,
    )

    if digest_log and digest_log.success:
        messages.success(
            request,
            "Test digest email sent successfully.",
        )
    elif digest_log:
        messages.error(
            request,
            f"Digest email failed: {digest_log.error_message}",
        )
    else:
        messages.warning(
            request,
            "Digest was skipped. Please check your email address and preferences.",
        )

    return redirect("notifications:digest_preview")


@login_required
def delivery_dashboard(request):
    if not can_view_delivery_monitor(request.user):
        messages.error(request, "You do not have permission to view delivery monitoring.")
        return redirect("dashboard:home")

    profile = getattr(request.user, "profile", None)

    deliveries = NotificationDeliveryLog.objects.select_related(
        "recipient",
        "organization",
        "notification",
        "digest_log",
    )

    if not request.user.is_superuser:
        deliveries = deliveries.filter(
            Q(organization=profile.organization)
            | Q(recipient__profile__organization=profile.organization)
        )

    status_filter = request.GET.get("status", "").strip()
    channel_filter = request.GET.get("channel", "").strip()
    q = request.GET.get("q", "").strip()

    if status_filter:
        deliveries = deliveries.filter(status=status_filter)

    if channel_filter:
        deliveries = deliveries.filter(channel=channel_filter)

    if q:
        deliveries = deliveries.filter(
            Q(subject__icontains=q)
            | Q(message__icontains=q)
            | Q(recipient__username__icontains=q)
            | Q(recipient__email__icontains=q)
            | Q(recipient__full_name__icontains=q)
            | Q(recipient_email__icontains=q)
            | Q(error_message__icontains=q)
        )

    total_count = deliveries.count()
    sent_count = deliveries.filter(status=NotificationDeliveryStatus.SENT).count()
    failed_count = deliveries.filter(status=NotificationDeliveryStatus.FAILED).count()
    skipped_count = deliveries.filter(status=NotificationDeliveryStatus.SKIPPED).count()
    pending_count = deliveries.filter(status=NotificationDeliveryStatus.PENDING).count()

    recent_failures = deliveries.filter(
        status=NotificationDeliveryStatus.FAILED,
    ).order_by("-created_at")[:8]

    deliveries = deliveries.order_by("-created_at")[:100]

    return render(
        request,
        "notifications/delivery_dashboard.html",
        {
            "page_title": "Notification Delivery Monitor",
            "deliveries": deliveries,
            "recent_failures": recent_failures,
            "total_count": total_count,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "pending_count": pending_count,
            "status_filter": status_filter,
            "channel_filter": channel_filter,
            "search": q,
            "status_choices": NotificationDeliveryStatus.choices,
            "channel_choices": NotificationDeliveryChannel.choices,
        },
    )


@login_required
def delivery_detail(request, pk):
    if not can_view_delivery_monitor(request.user):
        messages.error(request, "You do not have permission to view delivery logs.")
        return redirect("dashboard:home")

    delivery_log = get_object_or_404(
        NotificationDeliveryLog.objects.select_related(
            "recipient",
            "recipient__profile",
            "organization",
            "notification",
            "digest_log",
        ),
        pk=pk,
    )

    if not request.user.is_superuser:
        profile = getattr(request.user, "profile", None)

        if (
            not profile
            or (
                delivery_log.organization_id != profile.organization_id
                and getattr(delivery_log.recipient.profile, "organization_id", None) != profile.organization_id
            )
        ):
            messages.error(request, "You do not have permission to view this delivery log.")
            return redirect("dashboard:home")

    return render(
        request,
        "notifications/delivery_detail.html",
        {
            "page_title": "Delivery Detail",
            "delivery_log": delivery_log,
        },
    )


@login_required
def delivery_retry(request, pk):
    if not can_view_delivery_monitor(request.user):
        messages.error(request, "You do not have permission to retry delivery.")
        return redirect("dashboard:home")

    delivery_log = get_object_or_404(
        NotificationDeliveryLog,
        pk=pk,
    )

    if request.method != "POST":
        return redirect("notifications:delivery_detail", pk=delivery_log.pk)

    if not delivery_log.can_retry:
        messages.error(request, "This delivery cannot be retried.")
        return redirect("notifications:delivery_detail", pk=delivery_log.pk)

    retry_notification_delivery_task.delay(delivery_log.pk)

    messages.success(request, "Delivery retry queued successfully.")
    return redirect("notifications:delivery_detail", pk=delivery_log.pk)