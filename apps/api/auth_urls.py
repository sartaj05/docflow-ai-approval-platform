from django.urls import path

from apps.api.auth_views import APITokenView


urlpatterns = [
    path("auth/token/", APITokenView.as_view(), name="token"),
]
