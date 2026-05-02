from django.urls import path

from apps.audit import views

app_name = "audit"

urlpatterns = [
    path("logs/", views.audit_log_list, name="audit_log_list"),
    path("logs/<int:pk>/", views.audit_log_detail, name="audit_log_detail"),
]