from django.urls import path

from apps.api.request_views import RequestListView
from apps.api.views import APIRootView


app_name = "api"

urlpatterns = [
    path("", APIRootView.as_view(), name="root"),
    path("requests/", RequestListView.as_view(), name="request-list"),
]
