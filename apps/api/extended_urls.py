from django.urls import path

from apps.api.version_list_view import AttachmentVersionListAPIView


urlpatterns = [
    path("attachments/<int:attachment_pk>/versions/", AttachmentVersionListAPIView.as_view(), name="api-attachment-versions"),
]
