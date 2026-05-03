from django.urls import path

from apps.search_app import views


app_name = "search_app"

urlpatterns = [
    path("", views.global_search, name="global_search"),
]