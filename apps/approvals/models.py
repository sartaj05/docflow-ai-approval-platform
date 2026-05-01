from django.conf import settings
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.db import models
from django.utils import timezone

class RequestStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    IN_REVIEW = "IN_REVIEW", "In Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class RequestPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    URGENT = "URGENT", "Urgent"


class RequestCategory(models.TextChoices):
    PURCHASE = "PURCHASE", "Purchase"
    LEAVE = "LEAVE", "Leave"
    VENDOR_PAYMENT = "VENDOR_PAYMENT", "Vendor Payment"
    CONTRACT = "CONTRACT", "Contract"
    HR_DOCUMENT = "HR_DOCUMENT", "HR Document"
    STUDENT_INSTITUTE_REQUEST = "STUDENT_INSTITUTE_REQUEST", "Student/Institute Request"
    MEDICAL = "MEDICAL", "Medical"
    TENDER = "TENDER", "Tender"
    GENERAL = "GENERAL", "General"


class RiskLevel(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class ApprovalStepStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    SKIPPED = "SKIPPED", "Skipped"


class ApprovalActionType(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    COMMENTED = "COMMENTED", "Commented"
    FORWARDED = "FORWARDED", "Forwarded"
    CANCELLED = "CANCELLED", "Cancelled"
    REOPENED = "REOPENED", "Reopened"


class ApprovalWorkflow(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="approval_workflows",
    )

    name = models.CharField(max_length=150)

    category = models.CharField(
        max_length=40,
        choices=RequestCategory.choices,
        default=RequestCategory.GENERAL,
    )

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_approval_workflows",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["organization", "name"]
        indexes = [
            models.Index(fields=["organization", "category"]),
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.organization.name}"

    @property
    def step_count(self):
        return self.steps.count()


class ApprovalWorkflowStep(models.Model):
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    step_order = models.PositiveIntegerField()

    role_required = models.CharField(
        max_length=30,
        choices=[
            ("ORG_ADMIN", "Organization Admin"),
            ("DEPARTMENT_HEAD", "Department Head"),
            ("STAFF", "Staff/User"),
            ("APPROVER", "Approver"),
            ("AUDITOR", "Auditor"),
        ],
        default="APPROVER",
    )

    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="workflow_steps_assigned",
        blank=True,
        null=True,
        help_text="Optional fixed approver for this workflow step.",
    )

    department_based = models.BooleanField(
        default=False,
        help_text="If enabled, system will assign the request department head.",
    )

    sla_hours = models.PositiveIntegerField(
        default=24,
        help_text="How many hours this step can remain pending before becoming overdue.",
    )

    reminder_before_hours = models.PositiveIntegerField(
        default=4,
        help_text="Send reminder this many hours before due time.",
    )

    is_final_step = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["step_order"]
        unique_together = ["workflow", "step_order"]
        indexes = [
            models.Index(fields=["workflow", "step_order"]),
            models.Index(fields=["role_required"]),
            models.Index(fields=["is_final_step"]),
        ]

    def __str__(self):
        return f"{self.workflow.name} - Step {self.step_order}"


class DocumentRequest(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="document_requests",
    )

    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        related_name="document_requests",
        blank=True,
        null=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_document_requests",
        blank=True,
        null=True,
    )

    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.SET_NULL,
        related_name="document_requests",
        blank=True,
        null=True,
    )

    title = models.CharField(max_length=255)

    category = models.CharField(
        max_length=40,
        choices=RequestCategory.choices,
        default=RequestCategory.GENERAL,
    )

    priority = models.CharField(
        max_length=20,
        choices=RequestPriority.choices,
        default=RequestPriority.MEDIUM,
    )

    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.DRAFT,
    )

    current_step = models.PositiveIntegerField(default=0)

    ai_summary = models.TextField(blank=True)

    ai_category = models.CharField(max_length=100, blank=True)

    ai_extracted_data = models.JSONField(default=dict, blank=True)

    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        blank=True,
    )

    risk_notes = models.TextField(blank=True)

    submitted_at = models.DateTimeField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "category"]),
            models.Index(fields=["organization", "priority"]),
            models.Index(fields=["organization", "risk_level"]),
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["created_by", "status"]),
            models.Index(fields=["department", "status"]),
            models.Index(fields=["workflow", "status"]),
        ]

    def __str__(self):
        return f"{self.request_number} | {self.title}"

    @property
    def request_number(self):
        if self.organization:
            return self.organization.build_request_number(self.id)

        return f"REQ-{self.id:05d}"

    @property
    def is_draft(self):
        return self.status == RequestStatus.DRAFT

    @property
    def is_submitted(self):
        return self.status == RequestStatus.SUBMITTED

    @property
    def is_in_review(self):
        return self.status == RequestStatus.IN_REVIEW

    @property
    def is_approved(self):
        return self.status == RequestStatus.APPROVED

    @property
    def is_rejected(self):
        return self.status == RequestStatus.REJECTED

    @property
    def can_be_submitted(self):
        return self.status == RequestStatus.DRAFT

    @property
    def can_be_cancelled(self):
        return self.status in [
            RequestStatus.DRAFT,
            RequestStatus.SUBMITTED,
            RequestStatus.IN_REVIEW,
        ]

    def submit(self):
        self.status = RequestStatus.SUBMITTED
        self.submitted_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "submitted_at",
                "updated_at",
            ]
        )

    def cancel(self):
        self.status = RequestStatus.CANCELLED
        self.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )


class ApprovalStep(models.Model):
    request = models.ForeignKey(
        DocumentRequest,
        on_delete=models.CASCADE,
        related_name="approval_steps",
    )

    workflow_step = models.ForeignKey(
        ApprovalWorkflowStep,
        on_delete=models.SET_NULL,
        related_name="generated_steps",
        blank=True,
        null=True,
    )

    step_order = models.PositiveIntegerField()

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_approval_steps",
        blank=True,
        null=True,
    )

    role_required = models.CharField(max_length=30)

    status = models.CharField(
        max_length=20,
        choices=ApprovalStepStatus.choices,
        default=ApprovalStepStatus.PENDING,
    )

    approved_at = models.DateTimeField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)

    comments = models.TextField(blank=True)

    due_at = models.DateTimeField(blank=True, null=True)
    reminder_sent_at = models.DateTimeField(blank=True, null=True)
    escalated_at = models.DateTimeField(blank=True, null=True)

    is_overdue = models.BooleanField(default=False)
    escalation_count = models.PositiveIntegerField(default=0)

    is_current = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["step_order"]
        unique_together = ["request", "step_order"]
        indexes = [
            models.Index(fields=["request", "step_order"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_current"]),
            models.Index(fields=["due_at"]),
            models.Index(fields=["is_overdue"]),
            models.Index(fields=["escalated_at"]),
        ]

    def __str__(self):
        return f"{self.request.request_number} - Step {self.step_order}"

    @property
    def is_pending(self):
        return self.status == ApprovalStepStatus.PENDING

    @property
    def is_approved(self):
        return self.status == ApprovalStepStatus.APPROVED

    @property
    def is_rejected(self):
        return self.status == ApprovalStepStatus.REJECTED

    @property
    def is_due_passed(self):
        if not self.due_at:
            return False

        return timezone.now() > self.due_at

    @property
    def hours_until_due(self):
        if not self.due_at:
            return None

        delta = self.due_at - timezone.now()
        return round(delta.total_seconds() / 3600, 2)

    @property
    def overdue_hours(self):
        if not self.due_at:
            return 0

        if timezone.now() <= self.due_at:
            return 0

        delta = timezone.now() - self.due_at
        return round(delta.total_seconds() / 3600, 2)


class ApprovalAction(models.Model):
    request = models.ForeignKey(
        DocumentRequest,
        on_delete=models.CASCADE,
        related_name="approval_actions",
    )

    step = models.ForeignKey(
        ApprovalStep,
        on_delete=models.SET_NULL,
        related_name="actions",
        blank=True,
        null=True,
    )

    action_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approval_actions",
        blank=True,
        null=True,
    )

    action_type = models.CharField(
        max_length=30,
        choices=ApprovalActionType.choices,
    )

    comment = models.TextField(blank=True)

    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["request", "created_at"]),
            models.Index(fields=["step", "created_at"]),
            models.Index(fields=["action_by", "created_at"]),
            models.Index(fields=["action_type"]),
        ]

    def __str__(self):
        return f"{self.request.request_number} - {self.get_action_type_display()}"
    
class ApprovalDelegation(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="approval_delegations",
    )

    delegator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delegations_given",
        help_text="User who is unavailable or delegating approval authority.",
    )

    delegate_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delegations_received",
        help_text="User who will receive delegated approval assignments.",
    )

    reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="Reason like leave, vacation, training, temporary duty, etc.",
    )

    start_date = models.DateField()

    end_date = models.DateField()

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_approval_delegations",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["delegator", "is_active"]),
            models.Index(fields=["delegate_to", "is_active"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self):
        return f"{self.delegator} -> {self.delegate_to}"

    @property
    def is_currently_active(self):
        today = timezone.localdate()

        return (
            self.is_active
            and self.start_date <= today <= self.end_date
        )

    @property
    def date_range_display(self):
        return f"{self.start_date.strftime('%d %b %Y')} - {self.end_date.strftime('%d %b %Y')}"
    
    
class ApprovalReminder(models.Model):
    request = models.ForeignKey(
        DocumentRequest,
        on_delete=models.CASCADE,
        related_name="approval_reminders",
    )

    step = models.ForeignKey(
        ApprovalStep,
        on_delete=models.CASCADE,
        related_name="reminders",
    )

    sent_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approval_reminders_received",
        blank=True,
        null=True,
    )

    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approval_reminders_sent",
        blank=True,
        null=True,
    )

    message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["request", "created_at"]),
            models.Index(fields=["step", "created_at"]),
            models.Index(fields=["sent_to", "created_at"]),
            models.Index(fields=["sent_by", "created_at"]),
        ]

    def __str__(self):
        return f"Reminder for {self.request.request_number} - Step {self.step.step_order}"
    
    
class ApprovalPolicy(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="approval_policies",
    )

    name = models.CharField(max_length=150)

    description = models.TextField(blank=True)

    category = models.CharField(
        max_length=40,
        choices=RequestCategory.choices,
        blank=True,
        help_text="Optional. If selected, policy applies only to this request category.",
    )

    min_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Optional minimum amount condition.",
    )

    max_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Optional maximum amount condition.",
    )

    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        blank=True,
        help_text="Optional. If selected, policy applies only to this risk level.",
    )

    priority = models.CharField(
        max_length=20,
        choices=RequestPriority.choices,
        blank=True,
        help_text="Optional. If selected, policy applies only to this priority.",
    )

    assign_workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.SET_NULL,
        related_name="policies",
        blank=True,
        null=True,
        help_text="Workflow automatically selected when policy matches.",
    )

    set_priority = models.CharField(
        max_length=20,
        choices=RequestPriority.choices,
        blank=True,
        help_text="Optional. Priority to apply when policy matches.",
    )

    fixed_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approval_policy_fixed_assignments",
        blank=True,
        null=True,
        help_text="Optional. Dynamic approver assigned to first workflow step.",
    )

    is_active = models.BooleanField(default=True)

    priority_order = models.PositiveIntegerField(
        default=100,
        help_text="Lower number runs first.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_approval_policies",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority_order", "name"]
        unique_together = ["organization", "name"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "category"]),
            models.Index(fields=["organization", "priority_order"]),
            models.Index(fields=["min_amount", "max_amount"]),
            models.Index(fields=["risk_level"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.organization.name}"

    def matches_category(self, request_category):
        if not self.category:
            return True

        return self.category == request_category

    def matches_priority(self, request_priority):
        if not self.priority:
            return True

        return self.priority == request_priority

    def matches_risk(self, request_risk):
        if not self.risk_level:
            return True

        return self.risk_level == request_risk

    def matches_amount(self, amount):
        if amount is None:
            return self.min_amount is None and self.max_amount is None

        if self.min_amount is not None and amount < self.min_amount:
            return False

        if self.max_amount is not None and amount > self.max_amount:
            return False

        return True


class ApprovalPolicyEvaluation(models.Model):
    request = models.ForeignKey(
        DocumentRequest,
        on_delete=models.CASCADE,
        related_name="policy_evaluations",
    )

    policy = models.ForeignKey(
        ApprovalPolicy,
        on_delete=models.SET_NULL,
        related_name="evaluations",
        blank=True,
        null=True,
    )

    matched = models.BooleanField(default=False)

    extracted_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
    )

    old_priority = models.CharField(max_length=20, blank=True)
    new_priority = models.CharField(max_length=20, blank=True)

    old_workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.SET_NULL,
        related_name="old_policy_evaluations",
        blank=True,
        null=True,
    )

    new_workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.SET_NULL,
        related_name="new_policy_evaluations",
        blank=True,
        null=True,
    )

    fixed_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="policy_evaluations_as_fixed_approver",
        blank=True,
        null=True,
    )

    notes = models.TextField(blank=True)

    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-evaluated_at"]
        indexes = [
            models.Index(fields=["request", "evaluated_at"]),
            models.Index(fields=["policy", "matched"]),
        ]

    def __str__(self):
        if self.policy:
            return f"{self.request.request_number} - {self.policy.name}"

        return f"{self.request.request_number} - No Policy Match"
    
    
class RequestDiscussionComment(models.Model):
    request = models.ForeignKey(
        DocumentRequest,
        on_delete=models.CASCADE,
        related_name="discussion_comments",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        blank=True,
        null=True,
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="request_discussion_comments",
        blank=True,
        null=True,
    )

    message = models.TextField()

    mentioned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="mentioned_in_request_comments",
        blank=True,
    )

    is_internal = models.BooleanField(
        default=True,
        help_text="Internal comments are visible only to authorized workspace users.",
    )

    is_deleted = models.BooleanField(default=False)

    deleted_at = models.DateTimeField(blank=True, null=True)

    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="deleted_request_discussion_comments",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["request", "created_at"]),
            models.Index(fields=["author", "created_at"]),
            models.Index(fields=["is_deleted"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return f"{self.request.request_number} - Comment #{self.pk}"

    @property
    def can_show_message(self):
        return not self.is_deleted

    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "deleted_by",
                "updated_at",
            ]
        )


class RequestDiscussionAttachment(models.Model):
    comment = models.ForeignKey(
        RequestDiscussionComment,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(
        upload_to="approval_discussion_attachments/",
    )

    original_filename = models.CharField(max_length=255)

    file_size = models.PositiveIntegerField(default=0)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="uploaded_discussion_attachments",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["comment", "created_at"]),
            models.Index(fields=["uploaded_by", "created_at"]),
        ]

    def __str__(self):
        return self.original_filename

    @property
    def file_size_mb(self):
        if not self.file_size:
            return "0.00"

        return f"{self.file_size / (1024 * 1024):.2f}"
    
    
    
class RequestWatcher(models.Model):
    request = models.ForeignKey(
        DocumentRequest,
        on_delete=models.CASCADE,
        related_name="watchers",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watched_approval_requests",
    )

    is_active = models.BooleanField(default=True)

    receive_comment_notifications = models.BooleanField(default=True)
    receive_document_notifications = models.BooleanField(default=True)
    receive_approval_notifications = models.BooleanField(default=True)
    receive_ai_notifications = models.BooleanField(default=True)
    receive_certificate_notifications = models.BooleanField(default=True)
    receive_reminder_notifications = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["request", "user"]
        indexes = [
            models.Index(fields=["request", "is_active"]),
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.user} watches {self.request.request_number}"

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    def activate(self):
        self.is_active = True
        self.save(update_fields=["is_active", "updated_at"])