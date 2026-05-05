import re

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import (
    can_create_request,
    can_manage_request,
    get_user_organization,
)
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
    ApprovalAction,
    ApprovalActionType,
    ApprovalStepStatus,
    DocumentRequest,
    RequestCategory,
    RequestPriority,
    RequestStatus,
)
from apps.approvals.services.workflow_engine import generate_approval_steps_for_request
from apps.notifications.services.notification_service import notify_approval_assigned
from apps.approvals.services.policy_engine import apply_policy_to_request
from apps.approvals.services.watcher_service import (
    ACTIVITY_APPROVAL,
    get_or_create_watcher,
    notify_request_watchers,
)
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

    def patch(self, request, pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        if not can_manage_request(request.user, document_request):
            return Response(
                {"detail": "Only the creator can edit a draft request."},
                status=403,
            )

        serializer = RequestWriteSerializer(
            document_request,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        document_request = serializer.save()
        policy_result = apply_policy_to_request(document_request)
        document_request.refresh_from_db()
        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.UPDATED,
            model_name="DocumentRequest",
            object_id=document_request.pk,
            message=f"Approval request {document_request.request_number} updated through the API.",
            extra_data={"policy_matched": policy_result["matched"]},
        )
        return Response(RequestDetailSerializer(document_request).data)


class RequestCancelView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request, pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        if document_request.created_by_id != request.user.id:
            return Response(
                {"detail": "Only the request creator can cancel it."},
                status=403,
            )
        if not document_request.can_be_cancelled:
            return Response(
                {"detail": "This request cannot be cancelled."},
                status=400,
            )

        old_status = document_request.status
        document_request.status = RequestStatus.CANCELLED
        document_request.save(update_fields=["status", "updated_at"])
        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.CANCELLED,
            model_name="DocumentRequest",
            object_id=document_request.pk,
            message=f"Approval request {document_request.request_number} cancelled through the API.",
            extra_data={"old_status": old_status},
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
        return Response(RequestDetailSerializer(document_request).data)


class RequestSubmitView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    @transaction.atomic
    def post(self, request, pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        if document_request.created_by_id != request.user.id:
            return Response(
                {"detail": "Only the request creator can submit it."},
                status=403,
            )
        if not document_request.can_be_submitted:
            return Response({"detail": "Only draft requests can be submitted."}, status=400)

        policy_result = apply_policy_to_request(document_request)
        document_request.refresh_from_db()
        if not document_request.workflow or not document_request.workflow.steps.exists():
            return Response(
                {"detail": "Select a workflow that contains at least one approval step."},
                status=400,
            )

        document_request.status = RequestStatus.SUBMITTED
        document_request.submitted_at = timezone.now()
        document_request.save(update_fields=["status", "submitted_at", "updated_at"])
        try:
            generate_approval_steps_for_request(document_request)
        except ValueError as exc:
            document_request.status = RequestStatus.DRAFT
            document_request.submitted_at = None
            document_request.save(update_fields=["status", "submitted_at", "updated_at"])
            return Response({"detail": str(exc)}, status=400)

        current_step = document_request.approval_steps.filter(
            is_current=True,
            status=ApprovalStepStatus.PENDING,
        ).first()
        if current_step:
            notify_approval_assigned(approval_step=current_step, actor=request.user)

        ApprovalAction.objects.create(
            request=document_request,
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
            message=f"Approval request {document_request.request_number} submitted through the API.",
            extra_data={
                "workflow": document_request.workflow.name,
                "current_step": document_request.current_step,
                "policy_matched": policy_result["matched"],
            },
        )
        get_or_create_watcher(document_request=document_request, user=request.user)
        notify_request_watchers(
            document_request=document_request,
            actor=request.user,
            activity_type=ACTIVITY_APPROVAL,
            title=f"{document_request.request_number} submitted",
            message=f"{request.user.display_name} submitted {document_request.request_number} for approval.",
            object_type="DocumentRequest",
            object_id=document_request.pk,
        )
        return Response(RequestDetailSerializer(document_request).data)


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
