from django.utils import timezone

from apps.accounts.models import UserRole
from apps.approvals.models import ApprovalDelegation


def get_active_delegation_for_user(user, organization=None):
    if not user:
        return None

    today = timezone.localdate()

    qs = ApprovalDelegation.objects.select_related(
        "delegator",
        "delegate_to",
        "organization",
    ).filter(
        delegator=user,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today,
        delegate_to__is_active=True,
        delegate_to__profile__is_active=True,
    )

    if organization:
        qs = qs.filter(organization=organization)

    return qs.order_by("-created_at").first()


def resolve_delegated_approver(user, organization=None):
    """
    Returns delegated approver if active delegation exists.
    Otherwise returns original user.
    """

    delegation = get_active_delegation_for_user(
        user=user,
        organization=organization,
    )

    if delegation:
        return delegation.delegate_to

    return user


def is_user_available_for_approval(user, organization=None):
    """
    User is considered unavailable if they currently have active delegation.
    """

    if not user:
        return False

    delegation = get_active_delegation_for_user(
        user=user,
        organization=organization,
    )

    return delegation is None


def get_org_admin_fallback(organization, exclude_user=None):
    qs = organization.user_profiles.select_related("user").filter(
        role=UserRole.ORG_ADMIN,
        is_active=True,
        user__is_active=True,
    )

    if exclude_user:
        qs = qs.exclude(user=exclude_user)

    profile = qs.order_by("user__full_name", "user__username").first()

    if profile:
        return profile.user

    return None


def get_delegation_note(original_user, resolved_user):
    if not original_user or not resolved_user:
        return ""

    if original_user.id == resolved_user.id:
        return ""

    return f"Delegated from {original_user.display_name} to {resolved_user.display_name}"