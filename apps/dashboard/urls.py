from django.urls import path

from apps.dashboard import views


app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),

    path(
        "super-admin/",
        views.super_admin_dashboard,
        name="super_admin",
    ),

    path(
        "organization-admin/",
        views.organization_admin_dashboard,
        name="organization_admin",
    ),

    path(
        "department-head/",
        views.department_head_dashboard,
        name="department_head",
    ),

    path(
        "staff/",
        views.staff_dashboard,
        name="staff",
    ),

    path(
        "approver/",
        views.approver_dashboard,
        name="approver",
    ),

    path(
        "auditor/",
        views.auditor_dashboard,
        name="auditor",
    ),

    path(
        "my-activity/",
        views.my_activity_dashboard,
        name="my_activity",
    ),
    path(
        "system-health/",
        views.system_health_dashboard,
        name="system_health",
    ),
    path(
        "backup-export/",
        views.backup_export_dashboard,
        name="backup_export",
    ),

    path(
        "backup-export/action/",
        views.backup_export_action,
        name="backup_export_action",
    ),
    path(
        "restore/",
        views.restore_dashboard,
        name="restore_dashboard",
    ),

    path(
        "restore/upload/",
        views.restore_upload,
        name="restore_upload",
    ),

    path(
        "restore/<int:pk>/",
        views.restore_detail,
        name="restore_detail",
    ),

    path(
        "restore/<int:pk>/dry-run/",
        views.restore_dry_run,
        name="restore_dry_run",
    ),

    path(
        "restore/<int:pk>/confirm/",
        views.restore_confirm,
        name="restore_confirm",
    ),

    path(
        "restore/<int:pk>/restore-media/",
        views.restore_media_execute,
        name="restore_media_execute",
    ),
    path(
        "maintenance/",
        views.maintenance_mode_dashboard,
        name="maintenance_mode",
    ),

    path(
        "maintenance/public/",
        views.maintenance_public,
        name="maintenance_public",
    ),
    path(
        "deployment-readiness/",
        views.deployment_readiness_dashboard,
        name="deployment_readiness",
    ),
]