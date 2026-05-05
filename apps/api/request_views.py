import re

from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import can_create_request, get_user_organization
from apps.api.pagination import DefaultPagePagination
from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.api.permissions import scoped_departments, scoped_workflows
from apps.api.serializers import (
    DepartmentOptionSerializer,
    RequestDetailSerializer,
    RequestListSerializer,
    RequestWriteSerializer,
    WorkflowOptionSerializer,
)
from apps.approvals.models import (
    DocumentRequest,
    RequestCategory,
    RequestPriority,
    RequestStatus,
)
from apps.approvals.services.policy_engine import apply_policy_to_request
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log


class RequestListView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        requests = scoped_requests(request.user)
        filters = {
            "status": {choice for choice, _ in RequestStatus.choices},
            "category": {choice for choice, _ in RequestCategory.choices},
            "priority": {choice for choice, _ in RequestPriority.choices},
        }

        for name, allowed_values in filters.items():
            value = request.query_params.get(name, "").strip().upper()
            if value:
                if value not in allowed_values:
                    return Response(
                        {"detail": f"Invalid {name} filter.", "allowed": sorted(allowed_values)},
                        status=400,
                    )
                requests = requests.filter(**{name: value})

        query = request.query_params.get("q", "").strip()
        if query:
            search_filter = Q(title__icontains=query) | Q(description__icontains=query)
            request_number = re.search(r"(\d+)$", query)
            if request_number:
                search_filter |= Q(pk=int(request_number.group(1)))
            requests = requests.filter(search_filter)

        date_from = request.query_params.get("date_from")
        if date_from:
            parsed_date = parse_date(date_from)
            if not parsed_date:
                return Response({"detail": "date_from must use YYYY-MM-DD."}, status=400)
            requests = requests.filter(created_at__date__gte=parsed_date)

        date_to = request.query_params.get("date_to")
        if date_to:
            parsed_date = parse_date(date_to)
            if not parsed_date:
                return Response({"detail": "date_to must use YYYY-MM-DD."}, status=400)
            requests = requests.filter(created_at__date__lte=parsed_date)

        paginator = DefaultPagePagination()
        page = paginator.paginate_queryset(requests, request, view=self)
        serializer = RequestListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if not can_create_request(request.user):
            return Response(
                {"detail": "You do not have permission to create requests."},
                status=403,
            )

        organization = get_user_organization(request.user)
        serializer = RequestWriteSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        document_request = serializer.save(
            organization=organization,
            created_by=request.user,
            status=RequestStatus.DRAFT,
        )

        policy_result = apply_policy_to_request(document_request)
        document_request.refresh_from_db()
        create_audit_log(
            request=request,
            organization=organization,
            action=AuditAction.CREATED,
            model_name="DocumentRequest",
            object_id=document_request.pk,
            message=f"Approval request {document_request.request_number} created through the API.",
            extra_data={
                "title": document_request.title,
                "category": document_request.category,
                "priority": document_request.priority,
                "policy_matched": policy_result["matched"],
            },
        )
        return Response(
            RequestDetailSerializer(document_request).data,
            status=201,
        )


class RequestDetailView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        serializer = RequestDetailSerializer(document_request)
        return Response(serializer.data)


class WorkflowListView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        workflows = scoped_workflows(request.user).order_by("name")
        serializer = WorkflowOptionSerializer(workflows, many=True)
        return Response(serializer.data)


class DepartmentListView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        departments = scoped_departments(request.user).select_related("head").order_by("name")
        serializer = DepartmentOptionSerializer(departments, many=True)
        return Response(serializer.data)
