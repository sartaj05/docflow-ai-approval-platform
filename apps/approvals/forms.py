from django import forms

from apps.accounts.models import User, UserRole
from apps.approvals.models import (
    ApprovalWorkflow,
    ApprovalWorkflowStep,
    DocumentRequest,
    RequestDiscussionComment,
)
from django.utils import timezone
from apps.approvals.models import ApprovalDelegation
from decimal import Decimal
from django import forms
from apps.approvals.models import ApprovalPolicy
class DocumentRequestForm(forms.ModelForm):
    class Meta:
        model = DocumentRequest
        fields = [
            "department",
            "workflow",
            "title",
            "category",
            "priority",
            "description",
        ]

        widgets = {
            "department": forms.Select(attrs={"class": "form-select"}),
            "workflow": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Vendor payment approval for ABC Traders",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Describe the approval request in detail...",
                }
            ),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.organization = organization

        if organization:
            self.fields["department"].queryset = (
                organization.departments.filter(is_active=True).order_by("name")
            )

            self.fields["workflow"].queryset = (
                organization.approval_workflows.filter(is_active=True).order_by("name")
            )
        else:
            self.fields["department"].queryset = self.fields["department"].queryset.none()
            self.fields["workflow"].queryset = self.fields["workflow"].queryset.none()

        self.fields["department"].required = True
        self.fields["workflow"].required = True

    def clean_title(self):
        title = self.cleaned_data["title"].strip()

        if len(title) < 5:
            raise forms.ValidationError("Title must be at least 5 characters long.")

        return title

    def clean_department(self):
        department = self.cleaned_data.get("department")

        if department and self.organization and department.organization_id != self.organization.id:
            raise forms.ValidationError("Invalid department selected.")

        return department

    def clean_workflow(self):
        workflow = self.cleaned_data.get("workflow")

        if workflow and self.organization and workflow.organization_id != self.organization.id:
            raise forms.ValidationError("Invalid workflow selected.")

        if workflow and not workflow.steps.exists():
            raise forms.ValidationError("Selected workflow does not have steps.")

        return workflow


class DocumentRequestFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search title, description, request ID...",
            }
        ),
    )

    status = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    category = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    priority = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    department = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    risk_level = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(
        self,
        *args,
        organization=None,
        status_choices=None,
        category_choices=None,
        priority_choices=None,
        risk_choices=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.fields["status"].choices = [("", "All Status")] + list(status_choices or [])
        self.fields["category"].choices = [("", "All Categories")] + list(category_choices or [])
        self.fields["priority"].choices = [("", "All Priorities")] + list(priority_choices or [])
        self.fields["risk_level"].choices = [("", "All Risk Levels")] + list(risk_choices or [])

        department_choices = [("", "All Departments")]

        if organization:
            department_choices += [
                (str(dept.id), dept.name)
                for dept in organization.departments.filter(is_active=True).order_by("name")
            ]

        self.fields["department"].choices = department_choices


class ApprovalWorkflowForm(forms.ModelForm):
    class Meta:
        model = ApprovalWorkflow
        fields = [
            "name",
            "category",
            "description",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Vendor Payment Approval Flow",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe when this workflow should be used...",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        qs = ApprovalWorkflow.objects.filter(
            organization=self.organization,
            name__iexact=name,
        )

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "A workflow with this name already exists in your organization."
            )

        return name


class ApprovalWorkflowStepForm(forms.ModelForm):
    approver_user = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Fixed Approver",
    )

    class Meta:
        model = ApprovalWorkflowStep
        fields = [
            "step_order",
            "role_required",
            "approver_user",
            "department_based",
            "sla_hours",
            "reminder_before_hours",
            "is_final_step",
        ]

        widgets = {
            "step_order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "placeholder": "Example: 1",
                }
            ),
            "role_required": forms.Select(attrs={"class": "form-select"}),
            "department_based": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sla_hours": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 720,
                    "placeholder": "24",
                }
            ),
            "reminder_before_hours": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 168,
                    "placeholder": "4",
                }
            ),
            "is_final_step": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, workflow=None, organization=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.workflow = workflow
        self.organization = organization

        if organization:
            self.fields["approver_user"].queryset = (
                User.objects.filter(
                    profile__organization=organization,
                    profile__role__in=[
                        UserRole.ORG_ADMIN,
                        UserRole.DEPARTMENT_HEAD,
                        UserRole.APPROVER,
                    ],
                    profile__is_active=True,
                    is_active=True,
                )
                .select_related("profile")
                .order_by("full_name", "username")
            )

            self.fields["approver_user"].label_from_instance = (
                lambda user: f"{user.display_name} - {user.profile.get_role_display()}"
            )

        if self.instance and self.instance.pk and self.instance.approver_user:
            self.fields["approver_user"].initial = self.instance.approver_user

    def clean_step_order(self):
        step_order = self.cleaned_data["step_order"]

        qs = ApprovalWorkflowStep.objects.filter(
            workflow=self.workflow,
            step_order=step_order,
        )

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("This step order already exists in this workflow.")

        return step_order

    def clean_sla_hours(self):
        sla_hours = self.cleaned_data.get("sla_hours")

        if sla_hours < 1:
            raise forms.ValidationError("SLA hours must be at least 1.")

        if sla_hours > 720:
            raise forms.ValidationError("SLA hours cannot be more than 720 hours.")

        return sla_hours

    def clean_reminder_before_hours(self):
        reminder_before_hours = self.cleaned_data.get("reminder_before_hours")

        if reminder_before_hours < 1:
            raise forms.ValidationError("Reminder hours must be at least 1.")

        if reminder_before_hours > 168:
            raise forms.ValidationError("Reminder hours cannot be more than 168 hours.")

        return reminder_before_hours

    def clean(self):
        cleaned_data = super().clean()

        approver_user = cleaned_data.get("approver_user")
        department_based = cleaned_data.get("department_based")
        sla_hours = cleaned_data.get("sla_hours")
        reminder_before_hours = cleaned_data.get("reminder_before_hours")

        if approver_user and department_based:
            raise forms.ValidationError(
                "Use either fixed approver or department-based assignment, not both."
            )

        if sla_hours and reminder_before_hours and reminder_before_hours >= sla_hours:
            self.add_error(
                "reminder_before_hours",
                "Reminder hours must be less than SLA hours.",
            )

        return cleaned_data


class ApprovalStepActionForm(forms.Form):
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Write your approval/comment note...",
            }
        ),
    )


class ApprovalRejectForm(forms.Form):
    comment = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Rejection reason is required...",
            }
        ),
    )
class ApprovalDelegationForm(forms.ModelForm):
    delegator = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
        label="Delegating User",
    )

    delegate_to = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
        label="Delegate To",
    )

    class Meta:
        model = ApprovalDelegation
        fields = [
            "delegator",
            "delegate_to",
            "reason",
            "start_date",
            "end_date",
            "is_active",
        ]

        widgets = {
            "reason": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: On leave, vacation, training, temporary duty",
                }
            ),
            "start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "end_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, organization=None, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.organization = organization
        self.current_user = current_user

        if organization:
            users = (
                User.objects.filter(
                    profile__organization=organization,
                    profile__role__in=[
                        UserRole.ORG_ADMIN,
                        UserRole.DEPARTMENT_HEAD,
                        UserRole.APPROVER,
                    ],
                    profile__is_active=True,
                    is_active=True,
                )
                .select_related("profile")
                .order_by("full_name", "username")
            )

            self.fields["delegator"].queryset = users
            self.fields["delegate_to"].queryset = users
        else:
            self.fields["delegator"].queryset = User.objects.none()
            self.fields["delegate_to"].queryset = User.objects.none()

        self.fields["delegator"].label_from_instance = self.get_user_label
        self.fields["delegate_to"].label_from_instance = self.get_user_label

    def get_user_label(self, user):
        profile = getattr(user, "profile", None)

        if profile:
            return f"{user.display_name} - {profile.get_role_display()}"

        return user.display_name

    def clean(self):
        cleaned_data = super().clean()

        delegator = cleaned_data.get("delegator")
        delegate_to = cleaned_data.get("delegate_to")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if delegator and delegate_to and delegator.id == delegate_to.id:
            self.add_error(
                "delegate_to",
                "Delegator and delegate cannot be the same user.",
            )

        if start_date and end_date and end_date < start_date:
            self.add_error(
                "end_date",
                "End date cannot be before start date.",
            )

        if end_date and end_date < timezone.localdate():
            self.add_error(
                "end_date",
                "End date cannot be in the past.",
            )

        if delegator and delegate_to and self.organization:
            delegator_profile = getattr(delegator, "profile", None)
            delegate_profile = getattr(delegate_to, "profile", None)

            if not delegator_profile or delegator_profile.organization_id != self.organization.id:
                self.add_error("delegator", "Invalid delegator selected.")

            if not delegate_profile or delegate_profile.organization_id != self.organization.id:
                self.add_error("delegate_to", "Invalid delegate user selected.")

        if delegator and start_date and end_date:
            overlapping_qs = ApprovalDelegation.objects.filter(
                organization=self.organization,
                delegator=delegator,
                is_active=True,
                start_date__lte=end_date,
                end_date__gte=start_date,
            )

            if self.instance.pk:
                overlapping_qs = overlapping_qs.exclude(pk=self.instance.pk)

            if overlapping_qs.exists():
                self.add_error(
                    "start_date",
                    "This user already has an active delegation in the selected date range.",
                )

        return cleaned_data
    
class BulkApprovalActionForm(forms.Form):
    selected_steps = forms.MultipleChoiceField(
        required=True,
        widget=forms.CheckboxSelectMultiple,
    )

    action = forms.ChoiceField(
        required=True,
        choices=[
            ("approve", "Approve Selected"),
            ("reject", "Reject Selected"),
            ("comment", "Comment Selected"),
            ("remind", "Send Reminder"),
        ],
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Write approval note, rejection reason, comment, or reminder message...",
            }
        ),
    )

    def __init__(self, *args, steps_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.steps_queryset = steps_queryset

        if steps_queryset is not None:
            self.fields["selected_steps"].choices = [
                (
                    str(step.pk),
                    f"{step.request.request_number} - Step {step.step_order}",
                )
                for step in steps_queryset
            ]
        else:
            self.fields["selected_steps"].choices = []

    def clean(self):
        cleaned_data = super().clean()

        action = cleaned_data.get("action")
        comment = cleaned_data.get("comment", "").strip()

        if action == "reject" and not comment:
            self.add_error(
                "comment",
                "Rejection reason is required for bulk reject.",
            )

        if action == "comment" and not comment:
            self.add_error(
                "comment",
                "Comment is required for bulk comment.",
            )

        return cleaned_data


class ApprovalReminderForm(forms.Form):
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Optional reminder message...",
            }
        ),
    )    
class ApprovalPolicyForm(forms.ModelForm):
    fixed_approver = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Fixed Approver",
    )

    class Meta:
        model = ApprovalPolicy
        fields = [
            "name",
            "description",
            "category",
            "min_amount",
            "max_amount",
            "risk_level",
            "priority",
            "assign_workflow",
            "set_priority",
            "fixed_approver",
            "priority_order",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Vendor Payment Above 1 Lakh",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe when this policy should apply...",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "min_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Example: 100000",
                }
            ),
            "max_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Optional maximum amount",
                }
            ),
            "risk_level": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "assign_workflow": forms.Select(attrs={"class": "form-select"}),
            "set_priority": forms.Select(attrs={"class": "form-select"}),
            "priority_order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "placeholder": "100",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.organization = organization

        self.fields["category"].required = False
        self.fields["risk_level"].required = False
        self.fields["priority"].required = False
        self.fields["set_priority"].required = False
        self.fields["assign_workflow"].required = False

        self.fields["category"].choices = [("", "Any Category")] + list(self.fields["category"].choices)[1:]
        self.fields["risk_level"].choices = [("", "Any Risk Level")] + list(self.fields["risk_level"].choices)[1:]
        self.fields["priority"].choices = [("", "Any Priority")] + list(self.fields["priority"].choices)[1:]
        self.fields["set_priority"].choices = [("", "Do Not Change Priority")] + list(self.fields["set_priority"].choices)[1:]

        if organization:
            self.fields["assign_workflow"].queryset = (
                organization.approval_workflows.filter(is_active=True).order_by("name")
            )

            self.fields["fixed_approver"].queryset = (
                User.objects.filter(
                    profile__organization=organization,
                    profile__role__in=[
                        UserRole.ORG_ADMIN,
                        UserRole.DEPARTMENT_HEAD,
                        UserRole.APPROVER,
                    ],
                    profile__is_active=True,
                    is_active=True,
                )
                .select_related("profile")
                .order_by("full_name", "username")
            )

            self.fields["fixed_approver"].label_from_instance = (
                lambda user: f"{user.display_name} - {user.profile.get_role_display()}"
            )
        else:
            self.fields["assign_workflow"].queryset = ApprovalWorkflow.objects.none()
            self.fields["fixed_approver"].queryset = User.objects.none()

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        qs = ApprovalPolicy.objects.filter(
            organization=self.organization,
            name__iexact=name,
        )

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("A policy with this name already exists.")

        return name

    def clean(self):
        cleaned_data = super().clean()

        min_amount = cleaned_data.get("min_amount")
        max_amount = cleaned_data.get("max_amount")
        assign_workflow = cleaned_data.get("assign_workflow")
        set_priority = cleaned_data.get("set_priority")
        fixed_approver = cleaned_data.get("fixed_approver")

        if min_amount is not None and min_amount < Decimal("0"):
            self.add_error("min_amount", "Minimum amount cannot be negative.")

        if max_amount is not None and max_amount < Decimal("0"):
            self.add_error("max_amount", "Maximum amount cannot be negative.")

        if min_amount is not None and max_amount is not None and max_amount < min_amount:
            self.add_error("max_amount", "Maximum amount cannot be less than minimum amount.")

        if not assign_workflow and not set_priority and not fixed_approver:
            raise forms.ValidationError(
                "Policy must apply at least one action: assign workflow, set priority, or fixed approver."
            )

        if assign_workflow and self.organization and assign_workflow.organization_id != self.organization.id:
            self.add_error("assign_workflow", "Invalid workflow selected.")

        if fixed_approver:
            profile = getattr(fixed_approver, "profile", None)

            if not profile or profile.organization_id != self.organization.id:
                self.add_error("fixed_approver", "Invalid approver selected.")

        return cleaned_data 
    
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            MultipleFileInput(
                attrs={
                    "class": "form-control",
                    "multiple": True,
                }
            ),
        )
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            result = [
                single_file_clean(file_item, initial)
                for file_item in data
            ]
        else:
            result = single_file_clean(data, initial)

        return result


class RequestDiscussionCommentForm(forms.ModelForm):
    attachments = MultipleFileField(
        required=False,
        help_text="Optional. You can attach screenshots, PDFs, or supporting files.",
    )

    class Meta:
        model = RequestDiscussionComment
        fields = [
            "message",
        ]

        widgets = {
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Write an internal comment. Use @username to mention users...",
                }
            ),
        }

    def clean_message(self):
        message = self.cleaned_data.get("message", "").strip()

        if len(message) < 2:
            raise forms.ValidationError("Comment must contain at least 2 characters.")

        return message