from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from apps.approvals.services.activity_timeline import build_request_activity_timeline
from apps.accounts.models import UserRole
from apps.approvals.forms import (
    ApprovalDelegationForm,
    ApprovalPolicyForm,
    ApprovalRejectForm,
    ApprovalReminderForm,
    ApprovalStepActionForm,
    ApprovalWorkflowForm,
    ApprovalWorkflowStepForm,
    BulkApprovalActionForm,
    DocumentRequestFilterForm,
    DocumentRequestForm,
    RequestDiscussionCommentForm,
)
from apps.approvals.models import (
    ApprovalAction,
    ApprovalActionType,
    ApprovalDelegation,
    ApprovalPolicy,
    ApprovalPolicyEvaluation,
    ApprovalReminder,
    ApprovalStep,
    ApprovalStepStatus,
    ApprovalWorkflow,
    ApprovalWorkflowStep,
    DocumentRequest,
    RequestCategory,
    RequestDiscussionAttachment,
    RequestDiscussionComment,
    RequestPriority,
    RequestStatus,
    RiskLevel,
    RequestWatcher,
)
from apps.approvals.services.watcher_service import (
    ACTIVITY_APPROVAL,
    ACTIVITY_COMMENT,
    ACTIVITY_REMINDER,
    get_or_create_watcher,
    notify_request_watchers,
)
from apps.approvals.services.watcher_service import (
    ACTIVITY_APPROVAL,
    ACTIVITY_COMMENT,
    ACTIVITY_REMINDER,
    get_or_create_watcher,
    notify_request_watchers,
    toggle_request_watch,
    user_is_watching_request,
)
from apps.approvals.services.activity_timeline import build_request_activity_timeline
from apps.approvals.services.action_engine import (
    approve_current_step,
    can_user_act_on_step,
    comment_on_current_step,
    perform_bulk_step_action,
    reject_current_step,
)
from apps.approvals.services.discussion_service import (
    get_mention_users_for_request,
    notify_discussion_comment_created,
)
from apps.approvals.services.policy_engine import apply_policy_to_request
from apps.approvals.services.reminder_engine import (
    can_send_reminder_for_step,
    send_approval_reminder,
)
from apps.approvals.services.workflow_engine import generate_approval_steps_for_request
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.notifications.services.notification_service import notify_approval_assigned


# ==========================================================
# Common helpers
# ==========================================================

def get_user_profile(user):
    return getattr(user, "profile", None)


def get_user_organization(user):
    if user.is_superuser:
        return None

    profile = get_user_profile(user)

    if not profile:
        return None

    return profile.organization


def can_create_request(user):
    if user.is_superuser:
        return False

    profile = get_user_profile(user)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.DEPARTMENT_HEAD,
        UserRole.STAFF,
    ]


def can_manage_workflows(user):
    if user.is_superuser:
        return False

    profile = get_user_profile(user)

    if not profile:
        return False

    return profile.role == UserRole.ORG_ADMIN


def can_view_workflows(user):
    if user.is_superuser:
        return False

    profile = get_user_profile(user)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.DEPARTMENT_HEAD,
        UserRole.APPROVER,
        UserRole.AUDITOR,
    ]


def can_manage_delegations(user):
    if user.is_superuser:
        return False

    profile = get_user_profile(user)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.DEPARTMENT_HEAD,
        UserRole.APPROVER,
    ]


def can_manage_policies(user):
    if user.is_superuser:
        return False

    profile = get_user_profile(user)

    if not profile:
        return False

    return profile.role == UserRole.ORG_ADMIN


def can_view_policies(user):
    if user.is_superuser:
        return False

    profile = get_user_profile(user)

    if not profile:
        return False

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.AUDITOR,
    ]


# ==========================================================
# Scoped querysets
# ==========================================================

def get_scoped_requests(user):
    if user.is_superuser:
        return DocumentRequest.objects.select_related(
            "organization",
            "department",
            "created_by",
            "workflow",
        ).all()

    profile = get_user_profile(user)

    if not profile or not profile.organization:
        return DocumentRequest.objects.none()

    base_qs = DocumentRequest.objects.select_related(
        "organization",
        "department",
        "created_by",
        "workflow",
    ).filter(
        organization=profile.organization,
    )

    if profile.role == UserRole.ORG_ADMIN:
        return base_qs

    if profile.role == UserRole.DEPARTMENT_HEAD:
        if profile.department:
            return base_qs.filter(department=profile.department)

        return base_qs.none()

    if profile.role == UserRole.STAFF:
        return base_qs.filter(created_by=user)

    if profile.role == UserRole.APPROVER:
        return base_qs.filter(
            approval_steps__assigned_to=user,
        ).distinct()

    if profile.role == UserRole.AUDITOR:
        return base_qs

    return DocumentRequest.objects.none()


def get_scoped_workflows(user):
    profile = get_user_profile(user)

    if not profile or not profile.organization:
        return ApprovalWorkflow.objects.none()

    return ApprovalWorkflow.objects.filter(
        organization=profile.organization,
    )


def get_scoped_delegations(user):
    if user.is_superuser:
        return ApprovalDelegation.objects.select_related(
            "organization",
            "delegator",
            "delegate_to",
            "created_by",
        ).all()

    profile = get_user_profile(user)

    if not profile or not profile.organization:
        return ApprovalDelegation.objects.none()

    base_qs = ApprovalDelegation.objects.select_related(
        "organization",
        "delegator",
        "delegate_to",
        "created_by",
    ).filter(
        organization=profile.organization,
    )

    if profile.role == UserRole.ORG_ADMIN:
        return base_qs

    return base_qs.filter(
        Q(delegator=user) | Q(delegate_to=user)
    )


def get_scoped_policies(user):
    profile = get_user_profile(user)

    if not profile or not profile.organization:
        return ApprovalPolicy.objects.none()

    return ApprovalPolicy.objects.select_related(
        "organization",
        "assign_workflow",
        "fixed_approver",
        "created_by",
    ).filter(
        organization=profile.organization,
    )


# ==========================================================
# Filters
# ==========================================================

def apply_request_filters(queryset, request):
    search_query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()
    priority = request.GET.get("priority", "").strip()
    department = request.GET.get("department", "").strip()
    risk_level = request.GET.get("risk_level", "").strip()

    if search_query:
        request_id_query = Q()

        if search_query.upper().startswith("REQ-"):
            try:
                request_id = int(search_query.upper().replace("REQ-", ""))
                request_id_query = Q(id=request_id)
            except ValueError:
                request_id_query = Q()

        queryset = queryset.filter(
            request_id_query
            | Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(ai_summary__icontains=search_query)
            | Q(ai_extracted_data__icontains=search_query)
            | Q(created_by__username__icontains=search_query)
            | Q(created_by__email__icontains=search_query)
            | Q(created_by__full_name__icontains=search_query)
        )

    if status:
        queryset = queryset.filter(status=status)

    if category:
        queryset = queryset.filter(category=category)

    if priority:
        queryset = queryset.filter(priority=priority)

    if department:
        queryset = queryset.filter(department_id=department)

    if risk_level:
        queryset = queryset.filter(risk_level=risk_level)

    return queryset


# ==========================================================
# Approval requests
# ==========================================================

@login_required
def request_list(request):
    queryset = get_scoped_requests(request.user)
    queryset = apply_request_filters(queryset, request)

    organization = get_user_organization(request.user)

    filter_form = DocumentRequestFilterForm(
        request.GET or None,
        organization=organization,
        status_choices=RequestStatus.choices,
        category_choices=RequestCategory.choices,
        priority_choices=RequestPriority.choices,
        risk_choices=RiskLevel.choices,
    )

    total_requests = queryset.count()
    draft_count = queryset.filter(status=RequestStatus.DRAFT).count()
    submitted_count = queryset.filter(status=RequestStatus.SUBMITTED).count()
    in_review_count = queryset.filter(status=RequestStatus.IN_REVIEW).count()
    approved_count = queryset.filter(status=RequestStatus.APPROVED).count()
    rejected_count = queryset.filter(status=RequestStatus.REJECTED).count()

    return render(
        request,
        "approvals/request_list.html",
        {
            "page_title": "Approval Requests",
            "requests": queryset,
            "filter_form": filter_form,
            "total_requests": total_requests,
            "draft_count": draft_count,
            "submitted_count": submitted_count,
            "in_review_count": in_review_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "can_create": can_create_request(request.user),
        },
    )


@login_required
def request_create(request):
    if not can_create_request(request.user):
        messages.error(request, "You do not have permission to create approval requests.")
        return redirect("approvals:request_list")

    organization = get_user_organization(request.user)

    if not organization:
        messages.error(request, "Organization not found.")
        return redirect("dashboard:home")

    form = DocumentRequestForm(
        request.POST or None,
        organization=organization,
    )

    if request.method == "POST":
        if form.is_valid():
            document_request = form.save(commit=False)
            document_request.organization = organization
            document_request.created_by = request.user
            document_request.status = RequestStatus.DRAFT
            document_request.save()

            policy_result = apply_policy_to_request(document_request)
            document_request.refresh_from_db()

            create_audit_log(
                request=request,
                organization=organization,
                action=AuditAction.CREATED,
                model_name="DocumentRequest",
                object_id=document_request.pk,
                message=f"Approval request {document_request.request_number} created as draft.",
                extra_data={
                    "title": document_request.title,
                    "category": document_request.category,
                    "priority": document_request.priority,
                    "workflow": document_request.workflow.name if document_request.workflow else "",
                    "department": document_request.department.name if document_request.department else "",
                    "policy_matched": policy_result["matched"],
                    "policy_name": policy_result["policy"].name if policy_result["policy"] else "",
                    "policy_amount": str(policy_result["amount"]) if policy_result["amount"] is not None else "",
                },
            )

            messages.success(request, "Approval request created as draft.")
            return redirect("approvals:request_detail", pk=document_request.pk)

    return render(
        request,
        "approvals/request_form.html",
        {
            "page_title": "Create Approval Request",
            "form": form,
            "form_title": "Create Approval Request",
            "submit_label": "Save as Draft",
        },
    )
@login_required
def request_detail(request, pk):
    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=pk,
    )

    attachments = (
        document_request.attachments.select_related("uploaded_by")
        .order_by("-created_at")
    )

    approval_steps = (
        document_request.approval_steps.select_related("assigned_to")
        .order_by("step_order")
    )

    approval_actions = (
        document_request.approval_actions.select_related(
            "action_by",
            "step",
        )
        .order_by("-created_at")
    )

    discussion_comments = (
        document_request.discussion_comments.select_related(
            "author",
            "deleted_by",
            "parent",
            "parent__author",
        )
        .prefetch_related(
            "attachments",
            "mentioned_users",
            "replies",
            "replies__attachments",
            "replies__mentioned_users",
        )
        .filter(parent__isnull=True)
        .order_by("created_at")
    )

    discussion_form = RequestDiscussionCommentForm()

    try:
        activity_timeline = build_request_activity_timeline(
            document_request=document_request,
            limit=120,
        )
    except NameError:
        activity_timeline = []

    certificate_signature = getattr(
        document_request,
        "certificate_signature",
        None,
    )

    profile = get_user_profile(request.user)

    can_manage_certificate = (
        request.user.is_superuser
        or (
            profile
            and profile.role in [
                UserRole.ORG_ADMIN,
                UserRole.AUDITOR,
            ]
        )
    )

    current_user_step = (
        approval_steps.filter(
            assigned_to=request.user,
            is_current=True,
            status=ApprovalStepStatus.PENDING,
        )
        .first()
    )

    can_take_action = False

    if current_user_step:
        can_take_action = can_user_act_on_step(request.user, current_user_step)

    can_edit = (
        document_request.created_by_id == request.user.id
        and document_request.status == RequestStatus.DRAFT
    )

    can_submit = (
        document_request.created_by_id == request.user.id
        and document_request.status == RequestStatus.DRAFT
    )

    can_cancel = (
        document_request.created_by_id == request.user.id
        and document_request.can_be_cancelled
    )

    can_upload_documents = (
        document_request.created_by_id == request.user.id
        and document_request.status == RequestStatus.DRAFT
    )

    is_watching_request = user_is_watching_request(
        document_request=document_request,
        user=request.user,
    )

    active_watchers = (
        document_request.watchers.select_related("user")
        .filter(is_active=True)
        .order_by("-created_at")
    )

    watcher_count = active_watchers.count()

    return render(
        request,
        "approvals/request_detail.html",
        {
            "page_title": document_request.request_number,
            "document_request": document_request,
            "attachments": attachments,
            "approval_steps": approval_steps,
            "approval_actions": approval_actions,
            "discussion_comments": discussion_comments,
            "discussion_form": discussion_form,
            "activity_timeline": activity_timeline,
            "certificate_signature": certificate_signature,
            "can_manage_certificate": can_manage_certificate,
            "current_user_step": current_user_step,
            "can_take_action": can_take_action,
            "can_edit": can_edit,
            "can_submit": can_submit,
            "can_cancel": can_cancel,
            "can_upload_documents": can_upload_documents,
            "is_watching_request": is_watching_request,
            "active_watchers": active_watchers,
            "watcher_count": watcher_count,
        },
    )
    
@login_required
def request_watch_toggle(request, pk):
    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=pk,
    )

    if request.method != "POST":
        return redirect("approvals:request_detail", pk=document_request.pk)

    watcher, is_now_watching = toggle_request_watch(
        document_request=document_request,
        user=request.user,
    )

    if is_now_watching:
        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.UPDATED,
            model_name="RequestWatcher",
            object_id=watcher.pk,
            message=f"{request.user.display_name} started watching {document_request.request_number}.",
            extra_data={
                "request_id": document_request.pk,
                "request_number": document_request.request_number,
                "watcher_user": request.user.username,
            },
        )

        messages.success(
            request,
            "You are now watching this request. You will receive notifications for timeline activity.",
        )
    else:
        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.UPDATED,
            model_name="RequestWatcher",
            object_id=watcher.pk,
            message=f"{request.user.display_name} stopped watching {document_request.request_number}.",
            extra_data={
                "request_id": document_request.pk,
                "request_number": document_request.request_number,
                "watcher_user": request.user.username,
            },
        )

        messages.success(
            request,
            "You stopped watching this request.",
        )

    return redirect("approvals:request_detail", pk=document_request.pk)


@login_required
def request_watcher_list(request, pk):
    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=pk,
    )

    watchers = (
        document_request.watchers.select_related("user", "user__profile")
        .filter(is_active=True)
        .order_by("-created_at")
    )

    return render(
        request,
        "approvals/request_watcher_list.html",
        {
            "page_title": f"Watchers - {document_request.request_number}",
            "document_request": document_request,
            "watchers": watchers,
        },
    )
@login_required
def request_update(request, pk):
    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=pk,
    )

    if document_request.created_by_id != request.user.id:
        messages.error(request, "Only request creator can edit this request.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    if document_request.status != RequestStatus.DRAFT:
        messages.error(request, "Only draft requests can be edited.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    organization = get_user_organization(request.user)

    form = DocumentRequestForm(
        request.POST or None,
        instance=document_request,
        organization=organization,
    )

    if request.method == "POST":
        if form.is_valid():
            document_request = form.save()
            policy_result = apply_policy_to_request(document_request)
            document_request.refresh_from_db()

            create_audit_log(
                request=request,
                organization=document_request.organization,
                action=AuditAction.UPDATED,
                model_name="DocumentRequest",
                object_id=document_request.pk,
                message=f"Approval request {document_request.request_number} updated.",
                extra_data={
                    "title": document_request.title,
                    "category": document_request.category,
                    "priority": document_request.priority,
                    "workflow": document_request.workflow.name if document_request.workflow else "",
                    "department": document_request.department.name if document_request.department else "",
                    "policy_matched": policy_result["matched"],
                    "policy_name": policy_result["policy"].name if policy_result["policy"] else "",
                    "policy_amount": str(policy_result["amount"]) if policy_result["amount"] is not None else "",
                },
            )

            messages.success(request, "Approval request updated successfully.")
            return redirect("approvals:request_detail", pk=document_request.pk)

    return render(
        request,
        "approvals/request_form.html",
        {
            "page_title": "Edit Approval Request",
            "form": form,
            "form_title": "Edit Approval Request",
            "submit_label": "Update Request",
            "document_request": document_request,
        },
    )

@login_required
def request_submit(request, pk):
    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=pk,
    )

    if request.method != "POST":
        return redirect("approvals:request_detail", pk=document_request.pk)

    if document_request.created_by_id != request.user.id:
        messages.error(request, "Only request creator can submit this request.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    if not document_request.can_be_submitted:
        messages.error(request, "Only draft requests can be submitted.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    policy_result = apply_policy_to_request(document_request)

    if policy_result["matched"]:
        messages.info(
            request,
            f"Approval policy applied: {policy_result['policy'].name}",
        )

    document_request.refresh_from_db()

    if not document_request.workflow:
        messages.error(request, "Please select an approval workflow before submission.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    if not document_request.workflow.steps.exists():
        messages.error(request, "Selected workflow does not have approval steps.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    document_request.status = RequestStatus.SUBMITTED
    document_request.submitted_at = timezone.now()
    document_request.save(
        update_fields=[
            "status",
            "submitted_at",
            "updated_at",
        ]
    )

    try:
        generate_approval_steps_for_request(document_request)

        current_step = document_request.approval_steps.filter(
            is_current=True,
            status=ApprovalStepStatus.PENDING,
        ).first()

        if current_step:
            notify_approval_assigned(
                approval_step=current_step,
                actor=request.user,
            )

    except ValueError as exc:
        document_request.status = RequestStatus.DRAFT
        document_request.submitted_at = None
        document_request.save(
            update_fields=[
                "status",
                "submitted_at",
                "updated_at",
            ]
        )

        messages.error(request, str(exc))
        return redirect("approvals:request_detail", pk=document_request.pk)

    ApprovalAction.objects.create(
        request=document_request,
        step=None,
        action_by=request.user,
        action_type=ApprovalActionType.SUBMITTED,
        comment="Request submitted for approval.",
        old_status=RequestStatus.DRAFT,
        new_status=RequestStatus.IN_REVIEW,
    )

    create_audit_log(
        request=request,
        organization=document_request.organization,
        action=AuditAction.SUBMITTED,
        model_name="DocumentRequest",
        object_id=document_request.pk,
        message=f"Approval request {document_request.request_number} submitted for approval.",
        extra_data={
            "workflow": document_request.workflow.name if document_request.workflow else "",
            "current_step": document_request.current_step,
            "policy_matched": policy_result["matched"],
            "policy_name": policy_result["policy"].name if policy_result["policy"] else "",
            "policy_amount": str(policy_result["amount"]) if policy_result["amount"] is not None else "",
        },
    )

    get_or_create_watcher(
        document_request=document_request,
        user=request.user,
    )

    notify_request_watchers(
        document_request=document_request,
        actor=request.user,
        activity_type=ACTIVITY_APPROVAL,
        title=f"{document_request.request_number} submitted",
        message=f"{request.user.display_name} submitted {document_request.request_number} for approval.",
        object_type="DocumentRequest",
        object_id=document_request.pk,
    )

    messages.success(request, "Approval request submitted and workflow steps generated.")
    return redirect("approvals:request_detail", pk=document_request.pk)

@login_required
def request_cancel(request, pk):
    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=pk,
    )

    if request.method != "POST":
        return redirect("approvals:request_detail", pk=document_request.pk)

    if document_request.created_by_id != request.user.id:
        messages.error(request, "Only request creator can cancel this request.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    if not document_request.can_be_cancelled:
        messages.error(request, "This request cannot be cancelled.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    document_request.status = RequestStatus.CANCELLED
    document_request.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    create_audit_log(
        request=request,
        organization=document_request.organization,
        action=AuditAction.CANCELLED,
        model_name="DocumentRequest",
        object_id=document_request.pk,
        message=f"Approval request {document_request.request_number} cancelled.",
        extra_data={
            "status": document_request.status,
        },
    )

    notify_request_watchers(
        document_request=document_request,
        actor=request.user,
        activity_type=ACTIVITY_APPROVAL,
        title=f"{document_request.request_number} cancelled",
        message=f"{request.user.display_name} cancelled {document_request.request_number}.",
        object_type="DocumentRequest",
        object_id=document_request.pk,
    )

    messages.success(request, "Approval request cancelled successfully.")
    return redirect("approvals:request_detail", pk=document_request.pk)

@login_required
def request_delete(request, pk):
    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=pk,
    )

    if document_request.created_by_id != request.user.id:
        messages.error(request, "Only request creator can delete this request.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    if document_request.status != RequestStatus.DRAFT:
        messages.error(request, "Only draft requests can be deleted.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    if request.method == "POST":
        request_number = document_request.request_number

        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.DELETED,
            model_name="DocumentRequest",
            object_id=document_request.pk,
            message=f"Draft approval request {document_request.request_number} deleted.",
            extra_data={
                "title": document_request.title,
            },
        )

        document_request.delete()

        messages.success(request, f"{request_number} deleted successfully.")
        return redirect("approvals:request_list")

    return render(
        request,
        "approvals/request_confirm_delete.html",
        {
            "page_title": "Delete Approval Request",
            "document_request": document_request,
        },
    )

@login_required
def request_discussion_comment_create(request, pk):
    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=pk,
    )

    if request.method != "POST":
        return redirect("approvals:request_detail", pk=document_request.pk)

    form = RequestDiscussionCommentForm(request.POST, request.FILES)

    if not form.is_valid():
        messages.error(request, "Please write a valid comment.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    parent_id = request.POST.get("parent_id")
    parent_comment = None

    if parent_id:
        parent_comment = get_object_or_404(
            RequestDiscussionComment,
            pk=parent_id,
            request=document_request,
            is_deleted=False,
        )

    comment = form.save(commit=False)
    comment.request = document_request
    comment.author = request.user
    comment.parent = parent_comment
    comment.is_internal = True
    comment.save()

    mentioned_users = get_mention_users_for_request(
        document_request=document_request,
        message=comment.message,
    )

    if mentioned_users.exists():
        comment.mentioned_users.set(mentioned_users)

    for uploaded_file in request.FILES.getlist("attachments"):
        RequestDiscussionAttachment.objects.create(
            comment=comment,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            uploaded_by=request.user,
        )

    notify_discussion_comment_created(
        comment=comment,
        request_user=request.user,
    )

    create_audit_log(
        request=request,
        organization=document_request.organization,
        action=AuditAction.COMMENTED,
        model_name="RequestDiscussionComment",
        object_id=comment.pk,
        message=f"Comment added on {document_request.request_number}.",
        extra_data={
            "request_id": document_request.pk,
            "request_number": document_request.request_number,
            "comment_id": comment.pk,
            "parent_id": parent_comment.pk if parent_comment else None,
            "mentioned_users": [
                user.username for user in mentioned_users
            ],
            "attachments": [
                attachment.original_filename
                for attachment in comment.attachments.all()
            ],
        },
    )

    messages.success(request, "Comment added successfully.")
    return redirect("approvals:request_detail", pk=document_request.pk)


@login_required
def request_discussion_comment_delete(request, pk, comment_pk):
    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=pk,
    )

    comment = get_object_or_404(
        RequestDiscussionComment,
        pk=comment_pk,
        request=document_request,
    )

    if request.method != "POST":
        return redirect("approvals:request_detail", pk=document_request.pk)

    profile = get_user_profile(request.user)

    can_delete = (
        request.user.is_superuser
        or comment.author_id == request.user.id
        or (
            profile
            and profile.role == UserRole.ORG_ADMIN
            and profile.organization_id == document_request.organization_id
        )
    )

    if not can_delete:
        messages.error(request, "You do not have permission to delete this comment.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    comment.soft_delete(user=request.user)

    create_audit_log(
        request=request,
        organization=document_request.organization,
        action=AuditAction.DELETED,
        model_name="RequestDiscussionComment",
        object_id=comment.pk,
        message=f"Comment deleted from {document_request.request_number}.",
        extra_data={
            "request_id": document_request.pk,
            "request_number": document_request.request_number,
            "comment_id": comment.pk,
        },
    )

    messages.success(request, "Comment deleted successfully.")
    return redirect("approvals:request_detail", pk=document_request.pk)
# ==========================================================
# Approval inbox and actions
# ==========================================================

@login_required
def approval_inbox(request):
    if request.user.is_superuser:
        messages.error(request, "Super Admin does not have an approval inbox.")
        return redirect("dashboard:home")

    status_filter = request.GET.get("status", "pending")
    priority_filter = request.GET.get("priority", "")
    q = request.GET.get("q", "").strip()

    base_steps = (
        ApprovalStep.objects.select_related(
            "request",
            "request__organization",
            "request__department",
            "request__created_by",
            "assigned_to",
        )
        .filter(
            assigned_to=request.user,
            is_current=True,
        )
    )

    if status_filter == "all":
        steps = base_steps
    elif status_filter == "overdue":
        steps = base_steps.filter(
            status=ApprovalStepStatus.PENDING,
            is_overdue=True,
        )
    else:
        steps = base_steps.filter(
            status=ApprovalStepStatus.PENDING,
        )

    if priority_filter:
        steps = steps.filter(
            request__priority=priority_filter,
        )

    if q:
        steps = steps.filter(
            Q(request__title__icontains=q)
            | Q(request__description__icontains=q)
            | Q(request__created_by__username__icontains=q)
            | Q(request__created_by__email__icontains=q)
            | Q(request__created_by__full_name__icontains=q)
            | Q(request__department__name__icontains=q)
        )

    steps = steps.order_by(
        "-request__priority",
        "request__created_at",
    )

    pending_count = base_steps.filter(status=ApprovalStepStatus.PENDING).count()
    overdue_count = base_steps.filter(status=ApprovalStepStatus.PENDING, is_overdue=True).count()
    urgent_count = base_steps.filter(status=ApprovalStepStatus.PENDING, request__priority=RequestPriority.URGENT).count()
    due_today_count = base_steps.filter(status=ApprovalStepStatus.PENDING, due_at__date=timezone.localdate()).count()

    bulk_form = BulkApprovalActionForm(
        steps_queryset=steps,
    )

    return render(
        request,
        "approvals/approval_inbox.html",
        {
            "page_title": "Approval Inbox",
            "steps": steps,
            "bulk_form": bulk_form,
            "pending_count": pending_count,
            "overdue_count": overdue_count,
            "urgent_count": urgent_count,
            "due_today_count": due_today_count,
            "status_filter": status_filter,
            "priority_filter": priority_filter,
            "search": q,
        },
    )

@login_required
def approval_step_approve(request, pk):
    approval_step = get_object_or_404(
        ApprovalStep.objects.select_related(
            "request",
            "request__organization",
            "assigned_to",
        ),
        pk=pk,
    )

    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=approval_step.request_id,
    )

    if request.method != "POST":
        return redirect("approvals:request_detail", pk=document_request.pk)

    form = ApprovalStepActionForm(request.POST)

    if form.is_valid():
        comment = form.cleaned_data.get("comment", "")

        try:
            result = approve_current_step(
                approval_step,
                request.user,
                comment,
            )

            get_or_create_watcher(
                document_request=document_request,
                user=request.user,
            )

            notify_request_watchers(
                document_request=document_request,
                actor=request.user,
                activity_type=ACTIVITY_APPROVAL,
                title=f"{document_request.request_number} approved at step {approval_step.step_order}",
                message=f"{request.user.display_name} approved step {approval_step.step_order} for {document_request.request_number}.",
                object_type="ApprovalStep",
                object_id=approval_step.pk,
            )

            create_audit_log(
                request=request,
                organization=document_request.organization,
                action=AuditAction.APPROVED,
                model_name="ApprovalStep",
                object_id=approval_step.pk,
                message=f"Approval step {approval_step.step_order} approved for {document_request.request_number}.",
                extra_data={
                    "request_id": document_request.pk,
                    "step_order": approval_step.step_order,
                    "comment": comment,
                },
            )

            if result["is_final"]:
                messages.success(
                    request,
                    "Step approved. Request has been finally approved.",
                )
            else:
                messages.success(
                    request,
                    "Step approved. Request moved to the next approver.",
                )

        except ValueError as exc:
            messages.error(request, str(exc))

    return redirect("approvals:request_detail", pk=document_request.pk)
@login_required
def approval_step_reject(request, pk):
    approval_step = get_object_or_404(
        ApprovalStep.objects.select_related(
            "request",
            "request__organization",
            "assigned_to",
        ),
        pk=pk,
    )

    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=approval_step.request_id,
    )

    if request.method != "POST":
        return redirect("approvals:request_detail", pk=document_request.pk)

    form = ApprovalRejectForm(request.POST)

    if form.is_valid():
        comment = form.cleaned_data["comment"]

        try:
            reject_current_step(
                approval_step,
                request.user,
                comment,
            )

            get_or_create_watcher(
                document_request=document_request,
                user=request.user,
            )

            notify_request_watchers(
                document_request=document_request,
                actor=request.user,
                activity_type=ACTIVITY_APPROVAL,
                title=f"{document_request.request_number} rejected",
                message=f"{request.user.display_name} rejected {document_request.request_number} at step {approval_step.step_order}.",
                object_type="ApprovalStep",
                object_id=approval_step.pk,
            )

            create_audit_log(
                request=request,
                organization=document_request.organization,
                action=AuditAction.REJECTED,
                model_name="ApprovalStep",
                object_id=approval_step.pk,
                message=f"Approval step {approval_step.step_order} rejected for {document_request.request_number}.",
                extra_data={
                    "request_id": document_request.pk,
                    "step_order": approval_step.step_order,
                    "comment": comment,
                },
            )

            messages.success(
                request,
                "Request rejected successfully.",
            )

        except ValueError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "Rejection reason is required.")

    return redirect("approvals:request_detail", pk=document_request.pk)

@login_required
def approval_step_comment(request, pk):
    approval_step = get_object_or_404(
        ApprovalStep.objects.select_related(
            "request",
            "request__organization",
            "assigned_to",
        ),
        pk=pk,
    )

    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=approval_step.request_id,
    )

    if request.method != "POST":
        return redirect("approvals:request_detail", pk=document_request.pk)

    form = ApprovalStepActionForm(request.POST)

    if form.is_valid():
        comment = form.cleaned_data.get("comment", "")

        try:
            comment_on_current_step(
                approval_step,
                request.user,
                comment,
            )

            get_or_create_watcher(
                document_request=document_request,
                user=request.user,
            )

            notify_request_watchers(
                document_request=document_request,
                actor=request.user,
                activity_type=ACTIVITY_COMMENT,
                title=f"Approval comment on {document_request.request_number}",
                message=f"{request.user.display_name} commented on approval step {approval_step.step_order}.",
                object_type="ApprovalStep",
                object_id=approval_step.pk,
            )

            create_audit_log(
                request=request,
                organization=document_request.organization,
                action=AuditAction.COMMENTED,
                model_name="ApprovalStep",
                object_id=approval_step.pk,
                message=f"Comment added on approval step {approval_step.step_order} for {document_request.request_number}.",
                extra_data={
                    "request_id": document_request.pk,
                    "step_order": approval_step.step_order,
                    "comment": comment,
                },
            )

            messages.success(request, "Comment added successfully.")

        except ValueError as exc:
            messages.error(request, str(exc))

    return redirect("approvals:request_detail", pk=document_request.pk)

@login_required
def approval_bulk_action(request):
    if request.user.is_superuser:
        messages.error(request, "Super Admin cannot perform approval inbox actions.")
        return redirect("dashboard:home")

    if request.method != "POST":
        return redirect("approvals:approval_inbox")

    available_steps = (
        ApprovalStep.objects.select_related(
            "request",
            "request__organization",
            "assigned_to",
            "workflow_step",
        )
        .filter(
            assigned_to=request.user,
            status=ApprovalStepStatus.PENDING,
            is_current=True,
        )
    )

    form = BulkApprovalActionForm(
        request.POST,
        steps_queryset=available_steps,
    )

    if not form.is_valid():
        messages.error(request, "Please select valid approval steps and action.")
        return redirect("approvals:approval_inbox")

    selected_step_ids = form.cleaned_data["selected_steps"]

    selected_steps = available_steps.filter(
        pk__in=selected_step_ids,
    )

    action = form.cleaned_data["action"]
    comment = form.cleaned_data.get("comment", "")

    success_count = 0
    error_count = 0

    for step in selected_steps:
        try:
            perform_bulk_step_action(
                step=step,
                user=request.user,
                action=action,
                comment=comment,
            )

            create_audit_log(
                request=request,
                organization=step.request.organization,
                action=AuditAction.UPDATED,
                model_name="ApprovalStep",
                object_id=step.pk,
                message=f"Bulk {action} performed on step {step.step_order} for {step.request.request_number}.",
                extra_data={
                    "request_id": step.request_id,
                    "step_order": step.step_order,
                    "action": action,
                    "comment": comment,
                },
            )

            success_count += 1

        except ValueError as exc:
            error_count += 1

    if success_count:
        messages.success(
            request,
            f"Bulk action completed for {success_count} approval step(s).",
        )

    if error_count:
        messages.warning(
            request,
            f"{error_count} approval step(s) could not be processed.",
        )

    return redirect("approvals:approval_inbox")

@login_required
def approval_step_reminder(request, pk):
    approval_step = get_object_or_404(
        ApprovalStep.objects.select_related(
            "request",
            "request__organization",
            "assigned_to",
        ),
        pk=pk,
    )

    document_request = get_object_or_404(
        get_scoped_requests(request.user),
        pk=approval_step.request_id,
    )

    if request.method != "POST":
        return redirect("approvals:request_detail", pk=document_request.pk)

    form = ApprovalReminderForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Invalid reminder message.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    if not can_send_reminder_for_step(approval_step, request.user):
        messages.error(request, "You cannot send reminder for this approval step.")
        return redirect("approvals:request_detail", pk=document_request.pk)

    reminder = send_approval_reminder(
        approval_step=approval_step,
        sent_by=request.user,
        message=form.cleaned_data.get("message", ""),
    )

    notify_request_watchers(
        document_request=document_request,
        actor=request.user,
        activity_type=ACTIVITY_REMINDER,
        title=f"Reminder sent for {document_request.request_number}",
        message=f"{request.user.display_name} sent an approval reminder for {document_request.request_number}.",
        object_type="ApprovalReminder",
        object_id=reminder.pk,
    )

    create_audit_log(
        request=request,
        organization=document_request.organization,
        action=AuditAction.UPDATED,
        model_name="ApprovalReminder",
        object_id=reminder.pk,
        message=f"Reminder sent for {document_request.request_number}.",
        extra_data={
            "request_id": document_request.pk,
            "step_id": approval_step.pk,
            "sent_to": reminder.sent_to.display_name if reminder.sent_to else "",
        },
    )

    messages.success(request, "Reminder sent successfully.")
    return redirect("approvals:request_detail", pk=document_request.pk)

@login_required
def reminder_history(request):
    if request.user.is_superuser:
        reminders = ApprovalReminder.objects.select_related(
            "request",
            "request__organization",
            "step",
            "sent_to",
            "sent_by",
        ).all()
    else:
        profile = get_user_profile(request.user)

        if not profile or not profile.organization:
            reminders = ApprovalReminder.objects.none()
        else:
            reminders = ApprovalReminder.objects.select_related(
                "request",
                "request__organization",
                "step",
                "sent_to",
                "sent_by",
            ).filter(
                request__organization=profile.organization,
            )

    reminders = reminders.order_by("-created_at")

    return render(
        request,
        "approvals/reminder_history.html",
        {
            "page_title": "Reminder History",
            "reminders": reminders,
        },
    )
    
# ==========================================================
# Workflows
# ==========================================================

@login_required
def workflow_list(request):
    if not can_view_workflows(request.user):
        messages.error(request, "You do not have permission to view workflows.")
        return redirect("dashboard:home")

    workflows = (
        get_scoped_workflows(request.user)
        .prefetch_related("steps")
        .order_by("name")
    )

    return render(
        request,
        "approvals/workflow_list.html",
        {
            "page_title": "Workflows",
            "workflows": workflows,
            "can_manage": can_manage_workflows(request.user),
        },
    )


@login_required
def workflow_create(request):
    if not can_manage_workflows(request.user):
        messages.error(request, "Only organization admins can create workflows.")
        return redirect("approvals:workflow_list")

    organization = get_user_organization(request.user)

    form = ApprovalWorkflowForm(
        request.POST or None,
        organization=organization,
    )

    if request.method == "POST":
        if form.is_valid():
            workflow = form.save(commit=False)
            workflow.organization = organization
            workflow.created_by = request.user
            workflow.save()

            messages.success(request, "Workflow created successfully. Now add steps.")
            return redirect("approvals:workflow_detail", pk=workflow.pk)

    return render(
        request,
        "approvals/workflow_form.html",
        {
            "page_title": "Create Workflow",
            "form": form,
            "form_title": "Create Workflow",
            "submit_label": "Create Workflow",
        },
    )


@login_required
def workflow_detail(request, pk):
    if not can_view_workflows(request.user):
        messages.error(request, "You do not have permission to view workflows.")
        return redirect("dashboard:home")

    workflow = get_object_or_404(
        get_scoped_workflows(request.user).prefetch_related("steps"),
        pk=pk,
    )

    steps = workflow.steps.select_related("approver_user").order_by("step_order")

    return render(
        request,
        "approvals/workflow_detail.html",
        {
            "page_title": workflow.name,
            "workflow": workflow,
            "steps": steps,
            "can_manage": can_manage_workflows(request.user),
        },
    )


@login_required
def workflow_update(request, pk):
    if not can_manage_workflows(request.user):
        messages.error(request, "Only organization admins can update workflows.")
        return redirect("approvals:workflow_list")

    workflow = get_object_or_404(
        get_scoped_workflows(request.user),
        pk=pk,
    )

    form = ApprovalWorkflowForm(
        request.POST or None,
        instance=workflow,
        organization=workflow.organization,
    )

    if request.method == "POST":
        if form.is_valid():
            form.save()

            messages.success(request, "Workflow updated successfully.")
            return redirect("approvals:workflow_detail", pk=workflow.pk)

    return render(
        request,
        "approvals/workflow_form.html",
        {
            "page_title": "Edit Workflow",
            "form": form,
            "form_title": "Edit Workflow",
            "submit_label": "Update Workflow",
            "workflow": workflow,
        },
    )


@login_required
def workflow_delete(request, pk):
    if not can_manage_workflows(request.user):
        messages.error(request, "Only organization admins can delete workflows.")
        return redirect("approvals:workflow_list")

    workflow = get_object_or_404(
        get_scoped_workflows(request.user),
        pk=pk,
    )

    if workflow.document_requests.exists():
        messages.error(
            request,
            "This workflow is already used by approval requests. Deactivate it instead of deleting.",
        )
        return redirect("approvals:workflow_detail", pk=workflow.pk)

    if request.method == "POST":
        workflow_name = workflow.name
        workflow.delete()

        messages.success(request, f"Workflow '{workflow_name}' deleted successfully.")
        return redirect("approvals:workflow_list")

    return render(
        request,
        "approvals/workflow_confirm_delete.html",
        {
            "page_title": "Delete Workflow",
            "workflow": workflow,
        },
    )


@login_required
def workflow_step_create(request, workflow_pk):
    if not can_manage_workflows(request.user):
        messages.error(request, "Only organization admins can manage workflow steps.")
        return redirect("approvals:workflow_list")

    workflow = get_object_or_404(
        get_scoped_workflows(request.user),
        pk=workflow_pk,
    )

    form = ApprovalWorkflowStepForm(
        request.POST or None,
        workflow=workflow,
        organization=workflow.organization,
    )

    if request.method == "POST":
        if form.is_valid():
            workflow_step = form.save(commit=False)
            workflow_step.workflow = workflow
            workflow_step.save()

            messages.success(request, "Workflow step added successfully.")
            return redirect("approvals:workflow_detail", pk=workflow.pk)

    return render(
        request,
        "approvals/workflow_step_form.html",
        {
            "page_title": "Add Workflow Step",
            "form": form,
            "workflow": workflow,
            "form_title": "Add Workflow Step",
            "submit_label": "Add Step",
        },
    )


@login_required
def workflow_step_update(request, pk):
    if not can_manage_workflows(request.user):
        messages.error(request, "Only organization admins can manage workflow steps.")
        return redirect("approvals:workflow_list")

    workflow_step = get_object_or_404(
        ApprovalWorkflowStep.objects.select_related("workflow", "workflow__organization"),
        pk=pk,
        workflow__organization=get_user_organization(request.user),
    )

    form = ApprovalWorkflowStepForm(
        request.POST or None,
        instance=workflow_step,
        workflow=workflow_step.workflow,
        organization=workflow_step.workflow.organization,
    )

    if request.method == "POST":
        if form.is_valid():
            form.save()

            messages.success(request, "Workflow step updated successfully.")
            return redirect("approvals:workflow_detail", pk=workflow_step.workflow.pk)

    return render(
        request,
        "approvals/workflow_step_form.html",
        {
            "page_title": "Edit Workflow Step",
            "form": form,
            "workflow": workflow_step.workflow,
            "workflow_step": workflow_step,
            "form_title": "Edit Workflow Step",
            "submit_label": "Update Step",
        },
    )


@login_required
def workflow_step_delete(request, pk):
    if not can_manage_workflows(request.user):
        messages.error(request, "Only organization admins can manage workflow steps.")
        return redirect("approvals:workflow_list")

    workflow_step = get_object_or_404(
        ApprovalWorkflowStep.objects.select_related("workflow", "workflow__organization"),
        pk=pk,
        workflow__organization=get_user_organization(request.user),
    )

    workflow = workflow_step.workflow

    if request.method == "POST":
        workflow_step.delete()

        messages.success(request, "Workflow step deleted successfully.")
        return redirect("approvals:workflow_detail", pk=workflow.pk)

    return render(
        request,
        "approvals/workflow_step_confirm_delete.html",
        {
            "page_title": "Delete Workflow Step",
            "workflow": workflow,
            "workflow_step": workflow_step,
        },
    )


# ==========================================================
# Delegations
# ==========================================================

@login_required
def delegation_list(request):
    if not can_manage_delegations(request.user):
        messages.error(request, "You do not have permission to manage delegations.")
        return redirect("dashboard:home")

    delegations = get_scoped_delegations(request.user).order_by("-created_at")

    return render(
        request,
        "approvals/delegation_list.html",
        {
            "page_title": "Approval Delegations",
            "delegations": delegations,
            "can_manage": can_manage_delegations(request.user),
        },
    )


@login_required
def delegation_create(request):
    if not can_manage_delegations(request.user):
        messages.error(request, "You do not have permission to create delegations.")
        return redirect("dashboard:home")

    organization = get_user_organization(request.user)

    form = ApprovalDelegationForm(
        request.POST or None,
        organization=organization,
        current_user=request.user,
    )

    if request.method == "POST":
        if form.is_valid():
            delegation = form.save(commit=False)
            delegation.organization = organization
            delegation.created_by = request.user
            delegation.save()

            create_audit_log(
                request=request,
                organization=organization,
                action=AuditAction.CREATED,
                model_name="ApprovalDelegation",
                object_id=delegation.pk,
                message=f"Approval delegation created from {delegation.delegator} to {delegation.delegate_to}.",
                extra_data={
                    "delegator": delegation.delegator.username,
                    "delegate_to": delegation.delegate_to.username,
                    "start_date": str(delegation.start_date),
                    "end_date": str(delegation.end_date),
                },
            )

            messages.success(request, "Delegation created successfully.")
            return redirect("approvals:delegation_list")

    return render(
        request,
        "approvals/delegation_form.html",
        {
            "page_title": "Create Delegation",
            "form": form,
            "form_title": "Create Delegation",
            "submit_label": "Create Delegation",
        },
    )


@login_required
def delegation_update(request, pk):
    delegation = get_object_or_404(
        get_scoped_delegations(request.user),
        pk=pk,
    )

    organization = delegation.organization

    form = ApprovalDelegationForm(
        request.POST or None,
        instance=delegation,
        organization=organization,
        current_user=request.user,
    )

    if request.method == "POST":
        if form.is_valid():
            form.save()

            create_audit_log(
                request=request,
                organization=organization,
                action=AuditAction.UPDATED,
                model_name="ApprovalDelegation",
                object_id=delegation.pk,
                message="Approval delegation updated.",
                extra_data={
                    "delegation_id": delegation.pk,
                },
            )

            messages.success(request, "Delegation updated successfully.")
            return redirect("approvals:delegation_list")

    return render(
        request,
        "approvals/delegation_form.html",
        {
            "page_title": "Edit Delegation",
            "form": form,
            "delegation": delegation,
            "form_title": "Edit Delegation",
            "submit_label": "Update Delegation",
        },
    )


@login_required
def delegation_delete(request, pk):
    delegation = get_object_or_404(
        get_scoped_delegations(request.user),
        pk=pk,
    )

    if request.method == "POST":
        create_audit_log(
            request=request,
            organization=delegation.organization,
            action=AuditAction.DELETED,
            model_name="ApprovalDelegation",
            object_id=delegation.pk,
            message="Approval delegation deleted.",
            extra_data={
                "delegation_id": delegation.pk,
            },
        )

        delegation.delete()

        messages.success(request, "Delegation deleted successfully.")
        return redirect("approvals:delegation_list")

    return render(
        request,
        "approvals/delegation_confirm_delete.html",
        {
            "page_title": "Delete Delegation",
            "delegation": delegation,
        },
    )


@login_required
def delegation_toggle_status(request, pk):
    delegation = get_object_or_404(
        get_scoped_delegations(request.user),
        pk=pk,
    )

    if request.method != "POST":
        return redirect("approvals:delegation_list")

    delegation.is_active = not delegation.is_active
    delegation.save(update_fields=["is_active", "updated_at"])

    messages.success(request, "Delegation status updated.")
    return redirect("approvals:delegation_list")


# ==========================================================
# Approval Policies
# ==========================================================

@login_required
def policy_list(request):
    if not can_view_policies(request.user):
        messages.error(request, "You do not have permission to view approval policies.")
        return redirect("dashboard:home")

    policies = get_scoped_policies(request.user).order_by("priority_order", "name")

    return render(
        request,
        "approvals/policy_list.html",
        {
            "page_title": "Approval Policies",
            "policies": policies,
            "can_manage": can_manage_policies(request.user),
        },
    )


@login_required
def policy_create(request):
    if not can_manage_policies(request.user):
        messages.error(request, "Only organization admins can create approval policies.")
        return redirect("approvals:policy_list")

    organization = get_user_organization(request.user)

    form = ApprovalPolicyForm(
        request.POST or None,
        organization=organization,
    )

    if request.method == "POST":
        if form.is_valid():
            policy = form.save(commit=False)
            policy.organization = organization
            policy.created_by = request.user
            policy.save()

            messages.success(request, "Approval policy created successfully.")
            return redirect("approvals:policy_list")

    return render(
        request,
        "approvals/policy_form.html",
        {
            "page_title": "Create Approval Policy",
            "form": form,
            "form_title": "Create Approval Policy",
            "submit_label": "Create Policy",
        },
    )


@login_required
def policy_update(request, pk):
    if not can_manage_policies(request.user):
        messages.error(request, "Only organization admins can update approval policies.")
        return redirect("approvals:policy_list")

    policy = get_object_or_404(
        get_scoped_policies(request.user),
        pk=pk,
    )

    form = ApprovalPolicyForm(
        request.POST or None,
        instance=policy,
        organization=policy.organization,
    )

    if request.method == "POST":
        if form.is_valid():
            form.save()

            messages.success(request, "Approval policy updated successfully.")
            return redirect("approvals:policy_list")

    return render(
        request,
        "approvals/policy_form.html",
        {
            "page_title": "Edit Approval Policy",
            "form": form,
            "policy": policy,
            "form_title": "Edit Approval Policy",
            "submit_label": "Update Policy",
        },
    )


@login_required
def policy_delete(request, pk):
    if not can_manage_policies(request.user):
        messages.error(request, "Only organization admins can delete approval policies.")
        return redirect("approvals:policy_list")

    policy = get_object_or_404(
        get_scoped_policies(request.user),
        pk=pk,
    )

    if request.method == "POST":
        policy_name = policy.name
        policy.delete()

        messages.success(request, f"Approval policy '{policy_name}' deleted successfully.")
        return redirect("approvals:policy_list")

    return render(
        request,
        "approvals/policy_confirm_delete.html",
        {
            "page_title": "Delete Approval Policy",
            "policy": policy,
        },
    )


@login_required
def policy_toggle_status(request, pk):
    if not can_manage_policies(request.user):
        messages.error(request, "Only organization admins can update approval policies.")
        return redirect("approvals:policy_list")

    policy = get_object_or_404(
        get_scoped_policies(request.user),
        pk=pk,
    )

    if request.method != "POST":
        return redirect("approvals:policy_list")

    policy.is_active = not policy.is_active
    policy.save(update_fields=["is_active", "updated_at"])

    messages.success(request, "Approval policy status updated.")
    return redirect("approvals:policy_list")


@login_required
def policy_evaluation_history(request):
    if not can_view_policies(request.user):
        messages.error(request, "You do not have permission to view policy evaluations.")
        return redirect("dashboard:home")

    profile = get_user_profile(request.user)

    if request.user.is_superuser:
        evaluations = ApprovalPolicyEvaluation.objects.select_related(
            "request",
            "policy",
            "old_workflow",
            "new_workflow",
            "fixed_approver",
        ).all()
    elif profile and profile.organization:
        evaluations = ApprovalPolicyEvaluation.objects.select_related(
            "request",
            "policy",
            "old_workflow",
            "new_workflow",
            "fixed_approver",
        ).filter(
            request__organization=profile.organization,
        )
    else:
        evaluations = ApprovalPolicyEvaluation.objects.none()

    evaluations = evaluations.order_by("-evaluated_at")

    return render(
        request,
        "approvals/policy_evaluation_history.html",
        {
            "page_title": "Policy Evaluation History",
            "evaluations": evaluations,
        },
    )