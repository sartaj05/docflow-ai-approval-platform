from django.urls import reverse


def build_absolute_share_summary_url(request, share_link):
    path = reverse(
        "reports:public_request_summary",
        kwargs={
            "token": share_link.token,
        },
    )

    return request.build_absolute_uri(path)


def build_absolute_share_archive_url(request, share_link):
    path = reverse(
        "reports:public_request_archive",
        kwargs={
            "token": share_link.token,
        },
    )

    return request.build_absolute_uri(path)