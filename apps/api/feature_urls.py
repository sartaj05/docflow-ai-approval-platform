from django.urls import path

from apps.api.profile_read_view import CurrentProfileView


urlpatterns = [
    path("profile/", CurrentProfileView.as_view(), name="current-profile"),
]
