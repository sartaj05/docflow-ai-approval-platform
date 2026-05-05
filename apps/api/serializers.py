from rest_framework import serializers

from apps.approvals.models import ApprovalWorkflow, ApprovalWorkflowStep, DocumentRequest
from apps.departments.models import Department
from apps.api.permissions import get_user_organization


class RequestListSerializer(serializers.ModelSerializer):
    request_number = serializers.CharField(read_only=True)
    department_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    workflow_name = serializers.SerializerMethodField()

    class Meta:
        model = DocumentRequest
        fields = [
            "id",
            "request_number",
            "title",
            "category",
            "priority",
            "status",
            "risk_level",
            "department_name",
            "created_by_name",
            "workflow_name",
            "created_at",
            "submitted_at",
            "approved_at",
            "rejected_at",
        ]

    def get_department_name(self, obj):
        return obj.department.name if obj.department_id else None

    def get_created_by_name(self, obj):
        return obj.created_by.display_name if obj.created_by_id else None

    def get_workflow_name(self, obj):
        return obj.workflow.name if obj.workflow_id else None


class RequestDetailSerializer(RequestListSerializer):
    organization_id = serializers.IntegerField(read_only=True)
    department_id = serializers.IntegerField(read_only=True, allow_null=True)
    workflow_id = serializers.IntegerField(read_only=True, allow_null=True)
    created_by_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta(RequestListSerializer.Meta):
        fields = RequestListSerializer.Meta.fields + [
            "description",
            "current_step",
            "ai_summary",
            "ai_category",
            "ai_extracted_data",
            "risk_notes",
            "organization_id",
            "department_id",
            "workflow_id",
            "created_by_id",
            "updated_at",
        ]


class WorkflowStepOptionSerializer(serializers.ModelSerializer):
    approver_name = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalWorkflowStep
        fields = [
            "step_order",
            "role_required",
            "department_based",
            "sla_hours",
            "reminder_before_hours",
            "is_final_step",
            "approver_name",
        ]

    def get_approver_name(self, obj):
        return obj.approver_user.display_name if obj.approver_user_id else None


class WorkflowOptionSerializer(serializers.ModelSerializer):
    steps = WorkflowStepOptionSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalWorkflow
        fields = ["id", "name", "category", "description", "step_count", "steps"]


class DepartmentOptionSerializer(serializers.ModelSerializer):
    head_name = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "name", "description", "head_name"]

    def get_head_name(self, obj):
        return obj.head.display_name if obj.head_id else None


class RequestWriteSerializer(serializers.ModelSerializer):
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.none(),
        required=False,
        allow_null=True,
    )
    workflow = serializers.PrimaryKeyRelatedField(
        queryset=ApprovalWorkflow.objects.none(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = DocumentRequest
        fields = [
            "title",
            "category",
            "priority",
            "description",
            "department",
            "workflow",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        organization = get_user_organization(request.user) if request else None
        if organization:
            self.fields["department"].queryset = Department.objects.filter(
                organization=organization,
                is_active=True,
            )
            self.fields["workflow"].queryset = ApprovalWorkflow.objects.filter(
                organization=organization,
                is_active=True,
            )

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A title is required.")
        return value
