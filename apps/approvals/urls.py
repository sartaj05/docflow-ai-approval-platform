from django.urls import path

from apps.approvals import views


app_name = "approvals"

urlpatterns = [
    # ==============================
    # Approval Requests
    # ==============================
    path("requests/", views.request_list, name="request_list"),
    path("requests/create/", views.request_create, name="request_create"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/edit/", views.request_update, name="request_update"),
    path("requests/<int:pk>/submit/", views.request_submit, name="request_submit"),
    path("requests/<int:pk>/cancel/", views.request_cancel, name="request_cancel"),
    path("requests/<int:pk>/delete/", views.request_delete, name="request_delete"),
    path(
        "requests/<int:pk>/watch/",
        views.request_watch_toggle,
        name="request_watch_toggle",
    ),

    path(
        "requests/<int:pk>/watchers/",
        views.request_watcher_list,
        name="request_watcher_list",
    ),
    # ==============================
    # Step 34: Request Discussion
    # ==============================
    path(
        "requests/<int:pk>/discussion/comment/",
        views.request_discussion_comment_create,
        name="request_discussion_comment_create",
    ),
    path(
        "requests/<int:pk>/discussion/comment/<int:comment_pk>/delete/",
        views.request_discussion_comment_delete,
        name="request_discussion_comment_delete",
    ),

    # ==============================
    # Approval Inbox / Actions
    # ==============================
    path("inbox/", views.approval_inbox, name="approval_inbox"),
    path(
        "inbox/bulk-action/",
        views.approval_bulk_action,
        name="approval_bulk_action",
    ),
    path(
        "approval-steps/<int:pk>/approve/",
        views.approval_step_approve,
        name="approval_step_approve",
    ),
    path(
        "approval-steps/<int:pk>/reject/",
        views.approval_step_reject,
        name="approval_step_reject",
    ),
    path(
        "approval-steps/<int:pk>/comment/",
        views.approval_step_comment,
        name="approval_step_comment",
    ),
    path(
        "steps/<int:pk>/reminder/",
        views.approval_step_reminder,
        name="approval_step_reminder",
    ),
    path(
        "reminders/",
        views.reminder_history,
        name="reminder_history",
    ),

    # ==============================
    # Workflows
    # ==============================
    path("workflows/", views.workflow_list, name="workflow_list"),
    path("workflows/create/", views.workflow_create, name="workflow_create"),
    path("workflows/<int:pk>/", views.workflow_detail, name="workflow_detail"),
    path("workflows/<int:pk>/edit/", views.workflow_update, name="workflow_update"),
    path("workflows/<int:pk>/delete/", views.workflow_delete, name="workflow_delete"),
    path(
        "workflows/<int:workflow_pk>/steps/create/",
        views.workflow_step_create,
        name="workflow_step_create",
    ),
    path(
        "workflow-steps/<int:pk>/edit/",
        views.workflow_step_update,
        name="workflow_step_update",
    ),
    path(
        "workflow-steps/<int:pk>/delete/",
        views.workflow_step_delete,
        name="workflow_step_delete",
    ),

    # ==============================
    # Delegations
    # ==============================
    path("delegations/", views.delegation_list, name="delegation_list"),
    path("delegations/create/", views.delegation_create, name="delegation_create"),
    path("delegations/<int:pk>/edit/", views.delegation_update, name="delegation_update"),
    path("delegations/<int:pk>/delete/", views.delegation_delete, name="delegation_delete"),
    path(
        "delegations/<int:pk>/toggle/",
        views.delegation_toggle_status,
        name="delegation_toggle_status",
    ),

    # ==============================
    # Approval Policies
    # ==============================
    path("policies/", views.policy_list, name="policy_list"),
    path("policies/create/", views.policy_create, name="policy_create"),
    path("policies/<int:pk>/edit/", views.policy_update, name="policy_update"),
    path("policies/<int:pk>/delete/", views.policy_delete, name="policy_delete"),
    path(
        "policies/<int:pk>/toggle/",
        views.policy_toggle_status,
        name="policy_toggle_status",
    ),
    path(
        "policies/evaluations/",
        views.policy_evaluation_history,
        name="policy_evaluation_history",
    ),
]