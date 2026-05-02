from django.urls import path

from apps.documents import views

app_name = "documents"

urlpatterns = [
    path(
        "requests/<int:request_pk>/upload/",
        views.attachment_upload,
        name="attachment_upload",
    ),
    path(
        "attachments/<int:pk>/",
        views.attachment_detail,
        name="attachment_detail",
    ),
    path(
        "attachments/<int:pk>/delete/",
        views.attachment_delete,
        name="attachment_delete",
    ),
    path(
        "attachments/<int:pk>/process-ai/",
        views.attachment_process_ai,
        name="attachment_process_ai",
    ),
    path(
        "attachments/<int:pk>/replace/",
        views.attachment_replace,
        name="attachment_replace",
    ),
    path(
        "attachments/<int:pk>/versions/",
        views.attachment_versions,
        name="attachment_versions",
    ),
    path(
        "attachments/<int:pk>/versions/<int:version_pk>/compare/",
        views.attachment_version_compare,
        name="attachment_version_compare",
    ),
    path(
        "attachments/<int:pk>/versions/<int:version_pk>/rollback/",
        views.attachment_rollback,
        name="attachment_rollback",
    ),
    path(
        "attachments/<int:pk>/manual-correction/",
        views.attachment_manual_correction,
        name="attachment_manual_correction",
    ),
    path(
        "attachments/<int:pk>/reprocess-ai/",
        views.attachment_reprocess_ai,
        name="attachment_reprocess_ai",
    ),
    path(
        "attachments/<int:pk>/ai-history/",
        views.attachment_ai_history,
        name="attachment_ai_history",
    ),
]