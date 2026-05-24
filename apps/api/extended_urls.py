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
