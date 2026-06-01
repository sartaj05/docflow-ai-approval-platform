from django.urls import path

from apps.api.version_list_view import AttachmentVersionListAPIView


urlpatterns = [
    path("attachments/<int:attachment_pk>/versions/", AttachmentVersionListAPIView.as_view(), name="api-attachment-versions"),
]

from apps.api.version_compare_view import AttachmentVersionCompareAPIView
urlpatterns.append(path('attachments/<int:attachment_pk>/versions/<int:version_pk>/compare/', AttachmentVersionCompareAPIView.as_view(), name='api-attachment-version-compare'))

from apps.api.version_download_view import AttachmentVersionDownloadAPIView
urlpatterns.append(path('attachments/<int:attachment_pk>/versions/<int:version_pk>/download/', AttachmentVersionDownloadAPIView.as_view(), name='api-attachment-version-download'))

from apps.api.version_restore_view import AttachmentVersionRestoreAPIView
urlpatterns.append(path('attachments/<int:attachment_pk>/versions/<int:version_pk>/restore/', AttachmentVersionRestoreAPIView.as_view(), name='api-attachment-version-restore'))

from apps.api.manual_correction_view import AttachmentManualCorrectionAPIView
urlpatterns.append(path('attachments/<int:attachment_pk>/manual-correction/', AttachmentManualCorrectionAPIView.as_view(), name='api-attachment-manual-correction'))

from apps.api.ai_reprocess_view import AttachmentAIReprocessAPIView
urlpatterns.append(path('attachments/<int:attachment_pk>/reprocess-ai/', AttachmentAIReprocessAPIView.as_view(), name='api-attachment-ai-reprocess'))

from apps.api.ai_history_list_view import AttachmentAIHistoryListAPIView
urlpatterns.append(path('attachments/<int:attachment_pk>/ai-history/', AttachmentAIHistoryListAPIView.as_view(), name='api-attachment-ai-history'))

from apps.api.ai_history_detail_view import AttachmentAIHistoryDetailAPIView
urlpatterns.append(path('attachments/<int:attachment_pk>/ai-history/<int:history_pk>/', AttachmentAIHistoryDetailAPIView.as_view(), name='api-attachment-ai-history-detail'))

from apps.api.share_link_list_view import RequestShareLinkListAPIView
urlpatterns.append(path('requests/<int:pk>/share-links/', RequestShareLinkListAPIView.as_view(), name='api-request-share-links'))

from apps.api.share_link_create_view import RequestShareLinkCreateAPIView
urlpatterns.append(path('requests/<int:pk>/share-links/create/', RequestShareLinkCreateAPIView.as_view(), name='api-request-share-link-create'))

from apps.api.share_link_revoke_view import RequestShareLinkRevokeAPIView
urlpatterns.append(path('requests/<int:pk>/share-links/<int:link_pk>/revoke/', RequestShareLinkRevokeAPIView.as_view(), name='api-request-share-link-revoke'))

from apps.api.public_share_summary_view import PublicShareSummaryAPIView
urlpatterns.append(path('share/<str:token>/summary/', PublicShareSummaryAPIView.as_view(), name='api-public-share-summary'))

from apps.api.public_share_archive_view import PublicShareArchiveAPIView
urlpatterns.append(path('share/<str:token>/archive/', PublicShareArchiveAPIView.as_view(), name='api-public-share-archive'))

from apps.api.report_department_csv_view import DepartmentReportCSVAPIView
urlpatterns.append(path('reports/departments.csv', DepartmentReportCSVAPIView.as_view(), name='api-department-report-csv'))

from apps.api.report_risk_csv_view import RiskReportCSVAPIView
urlpatterns.append(path('reports/risks.csv', RiskReportCSVAPIView.as_view(), name='api-risk-report-csv'))

from apps.api.request_approval_actions_view import RequestApprovalActionsAPIView
urlpatterns.append(path('requests/<int:pk>/approval-actions/', RequestApprovalActionsAPIView.as_view(), name='api-request-approval-actions'))

from apps.api.notification_deliveries_view import NotificationDeliveryHistoryAPIView
urlpatterns.append(path('notifications/deliveries/', NotificationDeliveryHistoryAPIView.as_view(), name='api-notification-deliveries'))

from apps.api.notification_retry_view import NotificationDeliveryRetryAPIView
urlpatterns.append(path('notifications/deliveries/<int:delivery_pk>/retry/', NotificationDeliveryRetryAPIView.as_view(), name='api-notification-delivery-retry'))

from apps.api.reminder_history_view import ApprovalReminderHistoryAPIView
urlpatterns.append(path('reminders/', ApprovalReminderHistoryAPIView.as_view(), name='api-reminder-history'))
