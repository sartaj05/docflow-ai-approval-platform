from django.contrib import admin

from apps.approvals.models import (
    ApprovalAction,
    ApprovalDelegation,
    ApprovalPolicy,
    ApprovalPolicyEvaluation,
    ApprovalReminder,
    ApprovalStep,
    ApprovalWorkflow,
    ApprovalWorkflowStep,
    DocumentRequest,
    RequestDiscussionAttachment,
    RequestDiscussionComment,
)
from apps.approvals.models import RequestWatcher

class ApprovalWorkflowStepInline(admin.TabularInline):
    model = ApprovalWorkflowStep
    extra = 1

    fields = [
        "step_order",
        "role_required",
        "approver_user",
        "department_based",
        "sla_hours",
        "reminder_before_hours",
        "is_final_step",
    ]

    autocomplete_fields = [
        "approver_user",
    ]


@admin.register(ApprovalWorkflow)
class ApprovalWorkflowAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "organization",
        "category",
        "is_active",
        "step_count",
        "created_at",
    ]

    search_fields = [
        "name",
        "description",
        "organization__name",
    ]

    list_filter = [
        "category",
        "is_active",
        "organization",
        "created_at",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    autocomplete_fields = [
        "organization",
        "created_by",
    ]

    inlines = [
        ApprovalWorkflowStepInline,
    ]


@admin.register(ApprovalWorkflowStep)
class ApprovalWorkflowStepAdmin(admin.ModelAdmin):
    list_display = [
        "workflow",
        "step_order",
        "role_required",
        "approver_user",
        "department_based",
        "sla_hours",
        "reminder_before_hours",
        "is_final_step",
    ]

    search_fields = [
        "workflow__name",
        "approver_user__username",
        "approver_user__email",
        "approver_user__full_name",
    ]

    list_filter = [
        "role_required",
        "department_based",
        "is_final_step",
        "sla_hours",
        "reminder_before_hours",
    ]

    autocomplete_fields = [
        "workflow",
        "approver_user",
    ]


@admin.register(DocumentRequest)
class DocumentRequestAdmin(admin.ModelAdmin):
    list_display = [
        "request_number",
        "title",
        "organization",
        "department",
        "workflow",
        "created_by",
        "category",
        "priority",
        "status",
        "risk_level",
        "created_at",
    ]

    search_fields = [
        "title",
        "description",
        "organization__name",
        "department__name",
        "workflow__name",
        "created_by__username",
        "created_by__email",
        "created_by__full_name",
    ]

    list_filter = [
        "status",
        "priority",
        "category",
        "risk_level",
        "organization",
        "department",
        "workflow",
        "created_at",
    ]

    readonly_fields = [
        "submitted_at",
        "approved_at",
        "rejected_at",
        "created_at",
        "updated_at",
    ]

    autocomplete_fields = [
        "organization",
        "department",
        "workflow",
        "created_by",
    ]

    fieldsets = (
        (
            "Request Information",
            {
                "fields": (
                    "organization",
                    "department",
                    "workflow",
                    "created_by",
                    "title",
                    "category",
                    "priority",
                    "description",
                    "status",
                    "current_step",
                )
            },
        ),
        (
            "AI Information",
            {
                "fields": (
                    "ai_summary",
                    "ai_category",
                    "ai_extracted_data",
                    "risk_level",
                    "risk_notes",
                )
            },
        ),
        (
            "Important Dates",
            {
                "fields": (
                    "submitted_at",
                    "approved_at",
                    "rejected_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(ApprovalStep)
class ApprovalStepAdmin(admin.ModelAdmin):
    list_display = [
        "request",
        "step_order",
        "assigned_to",
        "role_required",
        "status",
        "is_current",
        "due_at",
        "is_overdue",
        "escalation_count",
        "approved_at",
        "rejected_at",
    ]

    search_fields = [
        "request__title",
        "request__organization__name",
        "assigned_to__username",
        "assigned_to__email",
        "assigned_to__full_name",
    ]

    list_filter = [
        "status",
        "role_required",
        "is_current",
        "is_overdue",
        "due_at",
        "escalated_at",
        "created_at",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    autocomplete_fields = [
        "request",
        "workflow_step",
        "assigned_to",
    ]

    fieldsets = (
        (
            "Approval Step",
            {
                "fields": (
                    "request",
                    "workflow_step",
                    "step_order",
                    "assigned_to",
                    "role_required",
                    "status",
                    "is_current",
                    "comments",
                )
            },
        ),
        (
            "SLA / Escalation",
            {
                "fields": (
                    "due_at",
                    "reminder_sent_at",
                    "is_overdue",
                    "escalated_at",
                    "escalation_count",
                )
            },
        ),
        (
            "Decision Dates",
            {
                "fields": (
                    "approved_at",
                    "rejected_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(ApprovalAction)
class ApprovalActionAdmin(admin.ModelAdmin):
    list_display = [
        "request",
        "step",
        "action_by",
        "action_type",
        "old_status",
        "new_status",
        "created_at",
    ]

    search_fields = [
        "request__title",
        "request__organization__name",
        "action_by__username",
        "action_by__email",
        "action_by__full_name",
        "comment",
    ]

    list_filter = [
        "action_type",
        "old_status",
        "new_status",
        "created_at",
    ]

    readonly_fields = [
        "created_at",
    ]

    autocomplete_fields = [
        "request",
        "step",
        "action_by",
    ]


@admin.register(ApprovalDelegation)
class ApprovalDelegationAdmin(admin.ModelAdmin):
    list_display = [
        "organization",
        "delegator",
        "delegate_to",
        "start_date",
        "end_date",
        "is_active",
        "created_by",
        "created_at",
    ]

    search_fields = [
        "organization__name",
        "delegator__username",
        "delegator__email",
        "delegator__full_name",
        "delegate_to__username",
        "delegate_to__email",
        "delegate_to__full_name",
        "reason",
    ]

    list_filter = [
        "organization",
        "is_active",
        "start_date",
        "end_date",
        "created_at",
    ]

    autocomplete_fields = [
        "organization",
        "delegator",
        "delegate_to",
        "created_by",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]


@admin.register(ApprovalReminder)
class ApprovalReminderAdmin(admin.ModelAdmin):
    list_display = [
        "request",
        "step",
        "sent_to",
        "sent_by",
        "created_at",
    ]

    search_fields = [
        "request__title",
        "request__organization__name",
        "sent_to__username",
        "sent_to__email",
        "sent_to__full_name",
        "sent_by__username",
        "sent_by__email",
        "sent_by__full_name",
        "message",
    ]

    list_filter = [
        "request__organization",
        "created_at",
    ]

    readonly_fields = [
        "created_at",
    ]

    autocomplete_fields = [
        "request",
        "step",
        "sent_to",
        "sent_by",
    ]


@admin.register(ApprovalPolicy)
class ApprovalPolicyAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "organization",
        "category",
        "min_amount",
        "max_amount",
        "risk_level",
        "priority",
        "assign_workflow",
        "set_priority",
        "fixed_approver",
        "priority_order",
        "is_active",
    ]

    search_fields = [
        "name",
        "description",
        "organization__name",
        "assign_workflow__name",
        "fixed_approver__username",
        "fixed_approver__email",
        "fixed_approver__full_name",
    ]

    list_filter = [
        "organization",
        "category",
        "risk_level",
        "priority",
        "set_priority",
        "is_active",
        "created_at",
    ]

    autocomplete_fields = [
        "organization",
        "assign_workflow",
        "fixed_approver",
        "created_by",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]


@admin.register(ApprovalPolicyEvaluation)
class ApprovalPolicyEvaluationAdmin(admin.ModelAdmin):
    list_display = [
        "request",
        "policy",
        "matched",
        "extracted_amount",
        "old_priority",
        "new_priority",
        "old_workflow",
        "new_workflow",
        "fixed_approver",
        "evaluated_at",
    ]

    search_fields = [
        "request__title",
        "request__organization__name",
        "policy__name",
        "notes",
    ]

    list_filter = [
        "matched",
        "evaluated_at",
        "policy",
    ]

    readonly_fields = [
        "evaluated_at",
    ]

    autocomplete_fields = [
        "request",
        "policy",
        "old_workflow",
        "new_workflow",
        "fixed_approver",
    ]


class RequestDiscussionAttachmentInline(admin.TabularInline):
    model = RequestDiscussionAttachment
    extra = 0

    fields = [
        "file",
        "original_filename",
        "file_size",
        "uploaded_by",
        "created_at",
    ]

    readonly_fields = [
        "original_filename",
        "file_size",
        "uploaded_by",
        "created_at",
    ]


@admin.register(RequestDiscussionComment)
class RequestDiscussionCommentAdmin(admin.ModelAdmin):
    list_display = [
        "request",
        "author",
        "parent",
        "is_internal",
        "is_deleted",
        "created_at",
    ]

    search_fields = [
        "request__title",
        "request__organization__name",
        "author__username",
        "author__email",
        "author__full_name",
        "message",
    ]

    list_filter = [
        "request__organization",
        "is_internal",
        "is_deleted",
        "created_at",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "deleted_at",
    ]

    autocomplete_fields = [
        "request",
        "parent",
        "author",
        "mentioned_users",
        "deleted_by",
    ]

    inlines = [
        RequestDiscussionAttachmentInline,
    ]


@admin.register(RequestDiscussionAttachment)
class RequestDiscussionAttachmentAdmin(admin.ModelAdmin):
    list_display = [
        "original_filename",
        "comment",
        "uploaded_by",
        "file_size",
        "created_at",
    ]

    search_fields = [
        "original_filename",
        "comment__message",
        "comment__request__title",
        "comment__request__organization__name",
        "uploaded_by__username",
        "uploaded_by__email",
        "uploaded_by__full_name",
    ]

    list_filter = [
        "comment__request__organization",
        "created_at",
    ]

    readonly_fields = [
        "original_filename",
        "file_size",
        "created_at",
    ]

    autocomplete_fields = [
        "comment",
        "uploaded_by",
    ]
    
    
@admin.register(RequestWatcher)
class RequestWatcherAdmin(admin.ModelAdmin):
    list_display = [
        "request",
        "user",
        "is_active",
        "receive_comment_notifications",
        "receive_document_notifications",
        "receive_approval_notifications",
        "receive_ai_notifications",
        "receive_certificate_notifications",
        "receive_reminder_notifications",
        "created_at",
    ]

    search_fields = [
        "request__title",
        "request__organization__name",
        "user__username",
        "user__email",
        "user__full_name",
    ]

    list_filter = [
        "is_active",
        "receive_comment_notifications",
        "receive_document_notifications",
        "receive_approval_notifications",
        "receive_ai_notifications",
        "receive_certificate_notifications",
        "receive_reminder_notifications",
        "created_at",
    ]

    autocomplete_fields = [
        "request",
        "user",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]