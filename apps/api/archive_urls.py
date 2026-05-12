from django.urls import path

from apps.api.archive_views import RequestArchiveDownloadView


urlpatterns = [
    path(
        "requests/<int:pk>/archive/",
        RequestArchiveDownloadView.as_view(),
        name="request-archive",
    ),
]
