from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "action",
        "model_name",
        "object_id",
        "organization",
        "user",
        "ip_address",
        "created_at",
    ]

    search_fields = [
        "message",
        "model_name",
        "object_id",
        "organization__name",
        "user__username",
        "user__email",
        "user__full_name",
        "ip_address",
        "user_agent",
    ]

    list_filter = [
        "action",
        "model_name",
        "organization",
        "created_at",
    ]

    readonly_fields = [
        "organization",
        "user",
        "action",
        "model_name",
        "object_id",
        "message",
        "ip_address",
        "user_agent",
        "extra_data",
        "created_at",
    ]

    date_hierarchy = "created_at"