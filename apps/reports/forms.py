from django import forms

from apps.approvals.models import (
    RequestCategory,
    RequestPriority,
    RequestStatus,
    RiskLevel,
)
from apps.departments.models import Department


class ReportFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search request no, title, creator, AI summary...",
            }
        ),
    )

    status = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    category = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    priority = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    risk_level = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    department = forms.ModelChoiceField(
        required=False,
        queryset=Department.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    def __init__(self, *args, organization=None, include_department=True, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["status"].choices = [("", "All Status")] + list(RequestStatus.choices)
        self.fields["category"].choices = [("", "All Categories")] + list(RequestCategory.choices)
        self.fields["priority"].choices = [("", "All Priorities")] + list(RequestPriority.choices)
        self.fields["risk_level"].choices = [("", "All Risk Levels")] + list(RiskLevel.choices)

        if organization:
            self.fields["department"].queryset = Department.objects.filter(
                organization=organization,
                is_active=True,
            ).order_by("name")
        else:
            self.fields["department"].queryset = Department.objects.none()

        if not include_department:
            self.fields.pop("department")
            
            
from datetime import timedelta

from django import forms
from django.utils import timezone

from apps.reports.models import RequestShareLink


class RequestShareLinkForm(forms.ModelForm):
    expiry_days = forms.IntegerField(
        min_value=1,
        max_value=30,
        initial=7,
        help_text="Share link expiry in days. Maximum 30 days.",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": 1,
                "max": 30,
            }
        ),
    )

    class Meta:
        model = RequestShareLink
        fields = [
            "title",
            "allow_summary_view",
            "allow_archive_download",
            "expiry_days",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Vendor approval summary share link",
                }
            ),
            "allow_summary_view": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "allow_archive_download": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def save(self, commit=True):
        share_link = super().save(commit=False)
        expiry_days = self.cleaned_data.get("expiry_days", 7)
        share_link.expires_at = timezone.now() + timedelta(days=expiry_days)

        if commit:
            share_link.save()

        return share_link
    
    
from django import forms


class CertificateInvalidateForm(forms.Form):
    reason = forms.CharField(
        required=True,
        min_length=5,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter reason for invalidating this certificate...",
            }
        ),
    )