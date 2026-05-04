import re

from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import DefaultPagePagination
from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.api.permissions import scoped_departments, scoped_workflows
from apps.api.serializers import (
    DepartmentOptionSerializer,
    RequestDetailSerializer,
    RequestListSerializer,
    WorkflowOptionSerializer,
)
from apps.approvals.models import RequestCategory, RequestPriority, RequestStatus


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
