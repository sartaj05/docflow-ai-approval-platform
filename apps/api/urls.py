from django.urls import path

from apps.api.views import APIRootView


app_name = "api"

urlpatterns = [
    path("", APIRootView.as_view(), name="root"),
]
