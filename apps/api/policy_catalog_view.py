from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.api.permissions import HasActiveWorkspace, get_user_organization
from apps.approvals.models import ApprovalPolicy


class PolicyCatalogAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        profile = getattr(request.user, "profile", None)
        if not request.user.is_superuser and (not profile or profile.role not in {UserRole.ORG_ADMIN, UserRole.AUDITOR}):
            return Response({"detail": "You do not have access to approval policies."}, status=403)
        policies = ApprovalPolicy.objects.select_related("assign_workflow", "fixed_approver")
        if not request.user.is_superuser:
            policies = policies.filter(organization=get_user_organization(request.user))
        policies = policies.order_by("priority_order", "name")
        return Response([{
            "id": item.pk,
            "name": item.name,
            "description": item.description,
            "category": item.category,
            "min_amount": str(item.min_amount) if item.min_amount is not None else None,
            "max_amount": str(item.max_amount) if item.max_amount is not None else None,
            "risk_level": item.risk_level,
            "priority": item.priority,
            "workflow": item.assign_workflow.name if item.assign_workflow_id else None,
            "is_active": item.is_active,
            "priority_order": item.priority_order,
        } for item in policies])
