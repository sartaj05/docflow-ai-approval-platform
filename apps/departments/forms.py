from django import forms

from apps.accounts.models import UserRole
from apps.departments.models import Department


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = [
            "name",
            "description",
            "head",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Finance Department",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Short department description",
                }
            ),
            "head": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.organization = organization

        if organization:
            self.fields["head"].queryset = (
                organization.user_profiles.filter(
                    role__in=[
                        UserRole.ORG_ADMIN,
                        UserRole.DEPARTMENT_HEAD,
                        UserRole.APPROVER,
                    ],
                    is_active=True,
                    user__is_active=True,
                )
                .select_related("user")
                .order_by("user__full_name", "user__username")
            )

            self.fields["head"].label_from_instance = (
                lambda profile: f"{profile.user.display_name} - {profile.get_role_display()}"
            )
        else:
            self.fields["head"].queryset = self.fields["head"].queryset.none()

        self.fields["head"].required = False
        self.fields["is_active"].required = False

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        qs = Department.objects.filter(
            organization=self.organization,
            name__iexact=name,
        )

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "A department with this name already exists in your organization."
            )

        return name

    def save(self, commit=True):
        department = super().save(commit=False)

        selected_profile = self.cleaned_data.get("head")

        if selected_profile:
            department.head = selected_profile.user
        else:
            department.head = None

        if commit:
            department.save()

        return department