from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.approvals.models import (
    ApprovalStep,
    ApprovalStepStatus,
    RequestStatus,
)
from apps.approvals.services.policy_engine import get_latest_fixed_approver_from_policy
from apps.approvals.services.delegation_engine import resolve_delegated_approver
def find_assigned_approver(document_request, workflow_step):
    """
    Approver assignment priority:

    1. Fixed approver selected in workflow step
    2. Department-based head
    3. Any active user in same organization with required role
    4. Organization admin fallback

    Delegation logic:
    - If selected approver has active delegation today,
      assignment moves to delegate_to user.
    """

    organization = document_request.organization

    if workflow_step.approver_user:
        approver_profile = getattr(workflow_step.approver_user, "profile", None)

        if (
            approver_profile
            and approver_profile.organization_id == organization.id
            and workflow_step.approver_user.is_active
            and approver_profile.is_active
        ):
            return resolve_delegated_approver(
                user=workflow_step.approver_user,
                organization=organization,
            )

    if workflow_step.department_based and document_request.department:
        department_head = document_request.department.head

        if department_head and department_head.is_active:
            head_profile = getattr(department_head, "profile", None)

            if (
                head_profile
                and head_profile.organization_id == organization.id
                and head_profile.is_active
            ):
                return resolve_delegated_approver(
                    user=department_head,
                    organization=organization,
                )

    role_user_profile = (
        organization.user_profiles.select_related("user")
        .filter(
            role=workflow_step.role_required,
            is_active=True,
            user__is_active=True,
        )
        .order_by("user__full_name", "user__username")
        .first()
    )

    if role_user_profile:
        return resolve_delegated_approver(
            user=role_user_profile.user,
            organization=organization,
        )

    org_admin_profile = (
        organization.user_profiles.select_related("user")
        .filter(
            role=UserRole.ORG_ADMIN,
            is_active=True,
            user__is_active=True,
        )
        .order_by("user__full_name", "user__username")
        .first()
    )

    if org_admin_profile:
        return resolve_delegated_approver(
            user=org_admin_profile.user,
            organization=organization,
        )

    return None

@transaction.atomic
def generate_approval_steps_for_request(document_request):
    """
    Generates ApprovalStep rows from selected ApprovalWorkflow.

    Rules:
    - Request must have workflow
    - Existing generated steps are deleted before regeneration
    - First step becomes current
    - Request moves to IN_REVIEW when steps exist
    - Each generated step gets due_at from workflow step SLA hours
    - Policy fixed approver can override first step approver
    """

    workflow = document_request.workflow

    if not workflow:
        raise ValueError("Approval workflow is required before submission.")

    workflow_steps = workflow.steps.order_by("step_order")

    if not workflow_steps.exists():
        raise ValueError("Selected workflow does not have approval steps.")

    document_request.approval_steps.all().delete()

    generated_steps = []
    now = timezone.now()
    policy_fixed_approver = get_latest_fixed_approver_from_policy(document_request)

    for index, workflow_step in enumerate(workflow_steps):
        assigned_user = find_assigned_approver(document_request, workflow_step)

        if policy_fixed_approver and index == 0:
            assigned_user = policy_fixed_approver

        is_first_step = index == 0

        approval_step = ApprovalStep.objects.create(
            request=document_request,
            workflow_step=workflow_step,
            step_order=workflow_step.step_order,
            assigned_to=assigned_user,
            role_required=workflow_step.role_required,
            status=ApprovalStepStatus.PENDING,
            is_current=is_first_step,
            due_at=now + timezone.timedelta(hours=workflow_step.sla_hours),
        )

        generated_steps.append(approval_step)

    first_step = generated_steps[0]

    document_request.status = RequestStatus.IN_REVIEW
    document_request.current_step = first_step.step_order
    document_request.save(
        update_fields=[
            "status",
            "current_step",
            "updated_at",
        ]
    )

    return generated_steps