from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.approvals.models import (
    ApprovalPolicy,
    ApprovalPolicyEvaluation,
)


def extract_amount_from_request(document_request):
    """
    Reads amount from AI extracted data.

    Supported keys:
    - amount
    - total
    - invoice_amount
    - bill_amount
    - payment_amount
    """

    data = document_request.ai_extracted_data or {}

    possible_keys = [
        "amount",
        "total",
        "invoice_amount",
        "bill_amount",
        "payment_amount",
    ]

    for key in possible_keys:
        value = data.get(key)

        if value in [None, ""]:
            continue

        try:
            cleaned_value = str(value).replace(",", "").replace("Rs.", "").replace("₹", "").strip()
            return Decimal(cleaned_value)
        except (InvalidOperation, ValueError):
            continue

    return None


def get_matching_policy(document_request):
    organization = document_request.organization
    amount = extract_amount_from_request(document_request)

    policies = ApprovalPolicy.objects.select_related(
        "assign_workflow",
        "fixed_approver",
    ).filter(
        organization=organization,
        is_active=True,
    ).order_by(
        "priority_order",
        "name",
    )

    for policy in policies:
        if not policy.matches_category(document_request.category):
            continue

        if not policy.matches_priority(document_request.priority):
            continue

        if not policy.matches_risk(document_request.risk_level):
            continue

        if not policy.matches_amount(amount):
            continue

        return policy, amount

    return None, amount


@transaction.atomic
def apply_policy_to_request(document_request):
    """
    Applies first matching policy to a draft request.

    Actions:
    - Auto assign workflow
    - Auto set priority
    - Store fixed approver into evaluation record
    """

    old_priority = document_request.priority
    old_workflow = document_request.workflow

    policy, amount = get_matching_policy(document_request)

    if not policy:
        ApprovalPolicyEvaluation.objects.create(
            request=document_request,
            policy=None,
            matched=False,
            extracted_amount=amount,
            old_priority=old_priority,
            new_priority=document_request.priority,
            old_workflow=old_workflow,
            new_workflow=document_request.workflow,
            notes="No matching policy found.",
        )

        return {
            "matched": False,
            "policy": None,
            "amount": amount,
            "changed": False,
            "fixed_approver": None,
        }

    changed = False

    if policy.assign_workflow and document_request.workflow_id != policy.assign_workflow_id:
        document_request.workflow = policy.assign_workflow
        changed = True

    if policy.set_priority and document_request.priority != policy.set_priority:
        document_request.priority = policy.set_priority
        changed = True

    if changed:
        document_request.save(
            update_fields=[
                "workflow",
                "priority",
                "updated_at",
            ]
        )

    ApprovalPolicyEvaluation.objects.create(
        request=document_request,
        policy=policy,
        matched=True,
        extracted_amount=amount,
        old_priority=old_priority,
        new_priority=document_request.priority,
        old_workflow=old_workflow,
        new_workflow=document_request.workflow,
        fixed_approver=policy.fixed_approver,
        notes=f"Matched policy: {policy.name}",
    )

    return {
        "matched": True,
        "policy": policy,
        "amount": amount,
        "changed": changed,
        "fixed_approver": policy.fixed_approver,
    }


def get_latest_fixed_approver_from_policy(document_request):
    evaluation = (
        document_request.policy_evaluations.select_related("fixed_approver")
        .filter(
            matched=True,
            fixed_approver__isnull=False,
        )
        .order_by("-evaluated_at")
        .first()
    )

    if evaluation:
        return evaluation.fixed_approver

    return None