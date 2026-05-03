from django.conf import settings
from django.shortcuts import render
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from apps.dashboard.models import MaintenanceMode


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Blocks public/app access when maintenance mode is enabled.

    Allows:
    - static/media files
    - maintenance public page
    - login/logout
    - admin path
    - super admin bypass if configured
    - staff bypass if configured
    - allowed IP bypass
    """

    def process_request(self, request):
        path = request.path

        ignored_prefixes = [
            settings.STATIC_URL,
            settings.MEDIA_URL,
            "/admin/",
            "/accounts/login/",
            "/accounts/logout/",
            "/dashboard/maintenance/public/",
        ]

        for prefix in ignored_prefixes:
            if prefix and path.startswith(prefix):
                return None

        try:
            maintenance = MaintenanceMode.get_config()
        except Exception:
            return None

        if not maintenance.is_enabled:
            return None

        if self.is_allowed_ip(request, maintenance):
            return None

        if request.user.is_authenticated:
            if maintenance.restore_safe_lock:
                if request.user.is_superuser and maintenance.allow_super_admin_bypass:
                    return None

                return render(
                    request,
                    "dashboard/maintenance_public.html",
                    {
                        "maintenance": maintenance,
                        "restore_safe_lock": True,
                    },
                    status=503,
                )

            if request.user.is_superuser and maintenance.allow_super_admin_bypass:
                return None

            if request.user.is_staff and maintenance.allow_staff_bypass:
                return None

        return render(
            request,
            "dashboard/maintenance_public.html",
            {
                "maintenance": maintenance,
                "restore_safe_lock": maintenance.restore_safe_lock,
            },
            status=503,
        )

    def is_allowed_ip(self, request, maintenance):
        allowed_ips = maintenance.allowed_ip_list

        if not allowed_ips:
            return False

        ip_address = self.get_client_ip(request)

        return ip_address in allowed_ips

    def get_client_ip(self, request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR", "")