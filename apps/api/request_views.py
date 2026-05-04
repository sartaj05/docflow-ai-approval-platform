from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.api.permissions import scoped_departments, scoped_workflows
from apps.api.serializers import (
    DepartmentOptionSerializer,
    RequestDetailSerializer,
    RequestListSerializer,
    WorkflowOptionSerializer,
)
from apps.approvals.models import DocumentRequest


class RequestListView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        requests = scoped_requests(request.user)
        serializer = RequestListSerializer(requests, many=True)
        return Response(serializer.data)


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
