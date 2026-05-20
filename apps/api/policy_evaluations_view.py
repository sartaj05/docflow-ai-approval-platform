from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.api.pagination import DefaultPagePagination
from apps.api.permissions import HasActiveWorkspace, get_user_organization
from apps.approvals.models import ApprovalPolicyEvaluation


class PolicyEvaluationHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        profile = getattr(request.user, "profile", None)
        if not request.user.is_superuser and (not profile or profile.role not in {UserRole.ORG_ADMIN, UserRole.AUDITOR}):
            return Response({"detail": "You do not have access to policy evaluations."}, status=403)
        rows = ApprovalPolicyEvaluation.objects.select_related(
            "request", "policy", "old_workflow", "new_workflow", "fixed_approver"
        )
        if not request.user.is_superuser:
            rows = rows.filter(request__organization=get_user_organization(request.user))
        request_id = request.query_params.get("request_id")
        if request_id:
            if not request_id.isdigit():
                return Response({"detail": "request_id must be an integer."}, status=400)
            rows = rows.filter(request_id=int(request_id))
        paginator = DefaultPagePagination()
        page = paginator.paginate_queryset(rows.order_by("-evaluated_at"), request, view=self)
        return paginator.get_paginated_response([{
            "id": item.pk,
            "request_id": item.request_id,
            "request_number": item.request.request_number,
            "policy": item.policy.name if item.policy_id else None,
            "matched": item.matched,
            "extracted_amount": str(item.extracted_amount) if item.extracted_amount is not None else None,
            "old_priority": item.old_priority,
            "new_priority": item.new_priority,
            "old_workflow": item.old_workflow.name if item.old_workflow_id else None,
            "new_workflow": item.new_workflow.name if item.new_workflow_id else None,
            "fixed_approver": item.fixed_approver.display_name if item.fixed_approver_id else None,
            "notes": item.notes,
            "evaluated_at": item.evaluated_at.isoformat(),
        } for item in page])
