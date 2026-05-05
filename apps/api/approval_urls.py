from django.urls import path

from apps.api.approval_views import (
    ApproveStepView,
    ApprovalInboxView,
    CommentOnStepView,
    RejectStepView,
)


urlpatterns = [
    path("inbox/", ApprovalInboxView.as_view(), name="approval-inbox"),
    path(
        "approval-steps/<int:step_pk>/approve/",
        ApproveStepView.as_view(),
        name="approval-step-approve",
    ),
    path(
        "approval-steps/<int:step_pk>/reject/",
        RejectStepView.as_view(),
        name="approval-step-reject",
    ),
    path(
        "approval-steps/<int:step_pk>/comment/",
        CommentOnStepView.as_view(),
        name="approval-step-comment",
    ),
]
