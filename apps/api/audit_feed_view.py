from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import DefaultPagePagination
from apps.api.permissions import HasActiveWorkspace, get_user_organization
from apps.audit.models import AuditAction, AuditLog
from apps.accounts.models import UserRole


def audit_queryset(user):
    if user.is_superuser:
        return AuditLog.objects.select_related("user", "organization").all()
    profile = getattr(user, "profile", None)
    if not profile or profile.role not in {UserRole.ORG_ADMIN, UserRole.AUDITOR}:
        return AuditLog.objects.none()
    organization = get_user_organization(user)
    if not organization:
        return AuditLog.objects.none()
    return AuditLog.objects.select_related("user", "organization").filter(organization=organization)


class AuditFeedView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        if not request.user.is_superuser and not audit_queryset(request.user).exists() and getattr(getattr(request.user, "profile", None), "role", None) not in {UserRole.ORG_ADMIN, UserRole.AUDITOR}:
            return Response({"detail": "You do not have access to audit logs."}, status=403)
        logs = audit_queryset(request.user)
        action = request.query_params.get("action", "").strip().upper()
        allowed = {value for value, _ in AuditAction.choices}
        if action:
            if action not in allowed:
                return Response({"detail": "Invalid action filter.", "allowed": sorted(allowed)}, status=400)
            logs = logs.filter(action=action)
        for param, lookup in (("date_from", "created_at__date__gte"), ("date_to", "created_at__date__lte")):
            value = request.query_params.get(param)
            if value:
                parsed = parse_date(value)
                if not parsed:
                    return Response({"detail": f"{param} must use YYYY-MM-DD."}, status=400)
                logs = logs.filter(**{lookup: parsed})
        paginator = DefaultPagePagination()
        page = paginator.paginate_queryset(logs.order_by("-created_at"), request, view=self)
        data = [{
            "id": item.pk,
            "action": item.action,
            "model_name": item.model_name,
            "object_id": item.object_id,
            "message": item.message,
            "actor": item.user.display_name if item.user_id else None,
            "created_at": item.created_at.isoformat(),
        } for item in page]
        return paginator.get_paginated_response(data)
