from django.urls import include, path

from apps.api.request_views import (
    DepartmentListView,
    RequestDetailView,
    RequestCancelView,
    RequestListView,
    RequestSubmitView,
    WorkflowListView,
)
from apps.api.views import APIRootView
from apps.api.schema import OpenAPISchemaView


app_name = "api"

urlpatterns = [
    path("", APIRootView.as_view(), name="root"),
    path("schema/", OpenAPISchemaView.as_view(), name="schema"),
    path("requests/", RequestListView.as_view(), name="request-list"),
    path("requests/<int:pk>/", RequestDetailView.as_view(), name="request-detail"),
    path("requests/<int:pk>/cancel/", RequestCancelView.as_view(), name="request-cancel"),
    path("requests/<int:pk>/submit/", RequestSubmitView.as_view(), name="request-submit"),
    path("workflows/", WorkflowListView.as_view(), name="workflow-list"),
    path("departments/", DepartmentListView.as_view(), name="department-list"),
    path("", include("apps.api.approval_urls")),
    path("", include("apps.api.activity_urls")),
    path("", include("apps.api.document_urls")),
    path("", include("apps.api.notification_urls")),
    path("", include("apps.api.auth_urls")),
    path("", include("apps.api.bulk_urls")),
]
