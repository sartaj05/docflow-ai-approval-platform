from django.urls import path

from apps.api.bulk_views import BulkApprovalActionView


urlpatterns = [
    path("inbox/bulk-action/", BulkApprovalActionView.as_view(), name="bulk-approval-action"),
]
