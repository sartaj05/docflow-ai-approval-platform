from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path


def landing_page(request):
    return render(request, "landing.html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", landing_page, name="landing"),

    path("accounts/", include("apps.accounts.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("departments/", include("apps.departments.urls")),
    path("approvals/", include("apps.approvals.urls")),
    path("documents/", include("apps.documents.urls")),
    path("audit/", include("apps.audit.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("reports/", include("apps.reports.urls")),
    path("organizations/", include("apps.organizations.urls")),
    path("search/", include("apps.search_app.urls")),

    path("super-admin/", include("apps.superadmin.urls")),
    path("api/v1/", include("apps.api.urls")),
]
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
