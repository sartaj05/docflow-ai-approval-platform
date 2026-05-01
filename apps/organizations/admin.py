from django.contrib import admin

from apps.organizations.models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "email",
        "phone",
        "is_active",
        "use_custom_smtp",
        "approval_number_prefix",
        "max_upload_size_mb",
        "created_at",
    ]

    search_fields = [
        "name",
        "slug",
        "email",
        "phone",
    ]

    list_filter = [
        "is_active",
        "use_custom_smtp",
        "created_at",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            "Organization Profile",
            {
                "fields": (
                    "name",
                    "slug",
                    "email",
                    "phone",
                    "address",
                    "logo",
                    "is_active",
                )
            },
        ),
        (
            "Approval Numbering",
            {
                "fields": (
                    "approval_number_prefix",
                    "approval_number_padding",
                    "approval_number_include_year",
                )
            },
        ),
        (
            "File Upload Settings",
            {
                "fields": (
                    "allowed_file_extensions",
                    "max_upload_size_mb",
                )
            },
        ),
        (
            "SMTP Override",
            {
                "fields": (
                    "use_custom_smtp",
                    "smtp_host",
                    "smtp_port",
                    "smtp_username",
                    "smtp_password",
                    "smtp_use_tls",
                    "smtp_use_ssl",
                    "smtp_from_email",
                    "smtp_from_name",
                )
            },
        ),
        (
            "System Dates",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )