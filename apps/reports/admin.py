from django.contrib import admin

from apps.reports.models import RequestShareLink
from django.contrib import admin

from apps.reports.models import (
    ApprovalCertificateSignature,
    RequestShareLink,
)
from apps.reports.models import ApprovalCertificateSignature, RequestShareLink
@admin.register(RequestShareLink)
class RequestShareLinkAdmin(admin.ModelAdmin):
    list_display = [
        "document_request",
        "title",
        "allow_summary_view",
        "allow_archive_download",
        "is_active",
        "expires_at",
        "access_count",
        "created_by",
        "created_at",
    ]

    search_fields = [
        "document_request__title",
        "document_request__organization__name",
        "token",
        "title",
        "created_by__username",
        "created_by__email",
        "created_by__full_name",
    ]

    list_filter = [
        "allow_summary_view",
        "allow_archive_download",
        "is_active",
        "expires_at",
        "created_at",
    ]

    readonly_fields = [
        "token",
        "access_count",
        "last_accessed_at",
        "revoked_at",
        "created_at",
    ]

    autocomplete_fields = [
        "document_request",
        "created_by",
        "revoked_by",
    ]
    
@admin.register(ApprovalCertificateSignature)
class ApprovalCertificateSignatureAdmin(admin.ModelAdmin):
    list_display = [
        "document_request",
        "verification_code",
        "signed_by",
        "organization_name",
        "is_valid",
        "signed_at",
    ]

    search_fields = [
        "document_request__title",
        "document_request__organization__name",
        "document_request__created_by__username",
        "verification_code",
        "certificate_hash",
        "signed_by_name",
        "signed_by_role",
        "organization_name",
    ]

    list_filter = [
        "is_valid",
        "signed_at",
        "created_at",
    ]

    readonly_fields = [
        "certificate_uuid",
        "certificate_hash",
        "verification_code",
        "verification_url",
        "signed_at",
        "created_at",
    ]

    autocomplete_fields = [
        "document_request",
        "signed_by",
        "invalidated_by",
    ]

    fieldsets = (
        (
            "Certificate",
            {
                "fields": (
                    "document_request",
                    "certificate_uuid",
                    "verification_code",
                    "verification_url",
                    "certificate_hash",
                    "is_valid",
                )
            },
        ),
        (
            "Signer Snapshot",
            {
                "fields": (
                    "signed_by",
                    "signed_by_name",
                    "signed_by_role",
                    "signed_at",
                )
            },
        ),
        (
            "Organization Snapshot",
            {
                "fields": (
                    "organization_name",
                )
            },
        ),
        (
            "Request Metadata",
            {
                "fields": (
                    "ip_address",
                    "user_agent",
                )
            },
        ),
        (
            "Invalidation",
            {
                "fields": (
                    "invalidated_by",
                    "invalidated_at",
                    "invalidation_reason",
                )
            },
        ),
        (
            "System",
            {
                "fields": (
                    "created_at",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return False