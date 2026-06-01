from django.urls import path

from apps.api.ai_history_detail_view import AttachmentAIHistoryDetailAPIView
from apps.api.ai_history_list_view import AttachmentAIHistoryListAPIView
from apps.api.ai_reprocess_view import AttachmentAIReprocessAPIView
from apps.api.manual_correction_view import AttachmentManualCorrectionAPIView
from apps.api.notification_deliveries_view import NotificationDeliveryHistoryAPIView
from apps.api.notification_retry_view import NotificationDeliveryRetryAPIView
from apps.api.public_share_archive_view import PublicShareArchiveAPIView
from apps.api.public_share_summary_view import PublicShareSummaryAPIView
from apps.api.reminder_history_view import ApprovalReminderHistoryAPIView
from apps.api.reminder_send_view import ApprovalReminderSendAPIView
from apps.api.report_department_csv_view import DepartmentReportCSVAPIView
from apps.api.report_risk_csv_view import RiskReportCSVAPIView
from apps.api.request_approval_actions_view import RequestApprovalActionsAPIView
from apps.api.share_link_create_view import RequestShareLinkCreateAPIView
from apps.api.share_link_list_view import RequestShareLinkListAPIView
from apps.api.share_link_revoke_view import RequestShareLinkRevokeAPIView
from apps.api.version_compare_view import AttachmentVersionCompareAPIView
from apps.api.version_download_view import AttachmentVersionDownloadAPIView
from apps.api.version_list_view import AttachmentVersionListAPIView
from apps.api.version_restore_view import AttachmentVersionRestoreAPIView


urlpatterns = [
    path("attachments/<int:attachment_pk>/versions/", AttachmentVersionListAPIView.as_view(), name="api-attachment-versions"),
    path("attachments/<int:attachment_pk>/versions/<int:version_pk>/compare/", AttachmentVersionCompareAPIView.as_view(), name="api-attachment-version-compare"),
    path("attachments/<int:attachment_pk>/versions/<int:version_pk>/download/", AttachmentVersionDownloadAPIView.as_view(), name="api-attachment-version-download"),
    path("attachments/<int:attachment_pk>/versions/<int:version_pk>/restore/", AttachmentVersionRestoreAPIView.as_view(), name="api-attachment-version-restore"),
    path("attachments/<int:attachment_pk>/manual-correction/", AttachmentManualCorrectionAPIView.as_view(), name="api-attachment-manual-correction"),
    path("attachments/<int:attachment_pk>/reprocess-ai/", AttachmentAIReprocessAPIView.as_view(), name="api-attachment-ai-reprocess"),
    path("attachments/<int:attachment_pk>/ai-history/", AttachmentAIHistoryListAPIView.as_view(), name="api-attachment-ai-history"),
    path("attachments/<int:attachment_pk>/ai-history/<int:history_pk>/", AttachmentAIHistoryDetailAPIView.as_view(), name="api-attachment-ai-history-detail"),
    path("requests/<int:pk>/share-links/", RequestShareLinkListAPIView.as_view(), name="api-request-share-links"),
    path("requests/<int:pk>/share-links/create/", RequestShareLinkCreateAPIView.as_view(), name="api-request-share-link-create"),
    path("requests/<int:pk>/share-links/<int:link_pk>/revoke/", RequestShareLinkRevokeAPIView.as_view(), name="api-request-share-link-revoke"),
    path("share/<str:token>/summary/", PublicShareSummaryAPIView.as_view(), name="api-public-share-summary"),
    path("share/<str:token>/archive/", PublicShareArchiveAPIView.as_view(), name="api-public-share-archive"),
    path("reports/departments.csv", DepartmentReportCSVAPIView.as_view(), name="api-department-report-csv"),
    path("reports/risks.csv", RiskReportCSVAPIView.as_view(), name="api-risk-report-csv"),
    path("requests/<int:pk>/approval-actions/", RequestApprovalActionsAPIView.as_view(), name="api-request-approval-actions"),
    path("notifications/deliveries/", NotificationDeliveryHistoryAPIView.as_view(), name="api-notification-deliveries"),
    path("notifications/deliveries/<int:delivery_pk>/retry/", NotificationDeliveryRetryAPIView.as_view(), name="api-notification-delivery-retry"),
    path("reminders/", ApprovalReminderHistoryAPIView.as_view(), name="api-reminder-history"),
    path("approval-steps/<int:step_pk>/reminders/", ApprovalReminderSendAPIView.as_view(), name="api-send-approval-reminder"),
]
