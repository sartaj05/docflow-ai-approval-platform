from django.urls import path

from apps.api.activity_views import RequestActivityView, RequestWatchView


urlpatterns = [
    path(
        "requests/<int:pk>/timeline/",
        RequestActivityView.as_view(),
        name="request-timeline",
    ),
    path(
        "requests/<int:pk>/watch/",
        RequestWatchView.as_view(),
        name="request-watch",
    ),
]
