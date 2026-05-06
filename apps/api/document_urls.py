from django.urls import path

from apps.api.document_views import AttachmentDownloadView, RequestAttachmentListView


urlpatterns = [
    path(
        "requests/<int:request_pk>/attachments/",
        RequestAttachmentListView.as_view(),
        name="request-attachments",
    ),
    path(
        "attachments/<int:attachment_pk>/download/",
        AttachmentDownloadView.as_view(),
        name="attachment-download",
    ),
]
