from django.urls import path

from apps.api.request_views import (
    DepartmentListView,
    RequestDetailView,
    RequestCancelView,
    RequestListView,
    WorkflowListView,
)
from apps.api.views import APIRootView


app_name = "api"

urlpatterns = [
    path("", APIRootView.as_view(), name="root"),
    path("requests/", RequestListView.as_view(), name="request-list"),
    path("requests/<int:pk>/", RequestDetailView.as_view(), name="request-detail"),
    path("requests/<int:pk>/cancel/", RequestCancelView.as_view(), name="request-cancel"),
    path("workflows/", WorkflowListView.as_view(), name="workflow-list"),
    path("departments/", DepartmentListView.as_view(), name="department-list"),
]
