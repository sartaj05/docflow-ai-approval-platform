from django.urls import path

from apps.reports import views


app_name = "reports"

urlpatterns = [
    path(
        "",
        views.reports_dashboard,
        name="dashboard",
    ),

    path(
        "requests/<int:pk>/print/",
        views.printable_request_summary,
        name="printable_request_summary",
    ),

    path(
        "requests/<int:pk>/summary-pdf/",
        views.request_summary_pdf,
        name="request_summary_pdf",
    ),

    path(
        "requests/<int:pk>/certificate-pdf/",
        views.approval_certificate_pdf,
        name="approval_certificate_pdf",
    ),

    path(
        "verify/<int:pk>/",
        views.verify_request,
        name="verify_request",
    ),

    path(
        "requests/<int:pk>/archive.zip",
        views.request_archive_zip,
        name="request_archive_zip",
    ),

    path(
        "requests/<int:pk>/share-links/",
        views.request_share_links,
        name="request_share_links",
    ),

    path(
        "requests/<int:pk>/share-links/create/",
        views.request_share_link_create,
        name="request_share_link_create",
    ),

    path(
        "requests/<int:pk>/share-links/<int:link_pk>/revoke/",
        views.request_share_link_revoke,
        name="request_share_link_revoke",
    ),

    path(
        "public/share/<str:token>/",
        views.public_request_summary,
        name="public_request_summary",
    ),

    path(
        "public/share/<str:token>/archive.zip",
        views.public_request_archive,
        name="public_request_archive",
    ),

    path(
        "requests/<int:pk>/certificate-preview/",
        views.approval_certificate_preview,
        name="approval_certificate_preview",
    ),
    path(
        "certificates/",
        views.certificate_list,
        name="certificate_list",
    ),

    path(
        "certificates/<int:pk>/",
        views.certificate_detail,
        name="certificate_detail",
    ),

    path(
        "certificates/<int:pk>/invalidate/",
        views.certificate_invalidate,
        name="certificate_invalidate",
    ),

    path(
        "certificates/verify/<str:verification_code>/",
        views.verify_certificate,
        name="verify_certificate",
    ),

    path(
        "certificates/verify/<str:verification_code>/qr.png",
        views.certificate_qr_png,
        name="certificate_qr_png",
    ),
]