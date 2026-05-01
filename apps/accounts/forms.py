from django import forms
from django.contrib.auth.password_validation import validate_password

from apps.accounts.models import User, UserRole
from apps.departments.models import Department
from apps.accounts.models import User, UserProfile, UserRole
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from apps.accounts.models import User, UserRole
from apps.departments.models import Department
from apps.organizations.models import Organization
MANAGEABLE_ORG_ROLES = [
    UserRole.ORG_ADMIN,
    UserRole.DEPARTMENT_HEAD,
    UserRole.STAFF,
    UserRole.APPROVER,
    UserRole.AUDITOR,
]


class OrganizationUserFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search name, username, email, phone...",
            }
        ),
    )

    role = forms.ChoiceField(
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

    status = forms.ChoiceField(
        required=False,
        choices=[
            ("", "All Status"),
            ("active", "Active"),
            ("inactive", "Inactive"),
        ],
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["role"].choices = [("", "All Roles")] + [
            (role, UserRole(role).label) for role in MANAGEABLE_ORG_ROLES
        ]

        if organization:
            self.fields["department"].queryset = Department.objects.filter(
                organization=organization,
                is_active=True,
            ).order_by("name")


class OrganizationUserCreateForm(forms.ModelForm):
    role = forms.ChoiceField(
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

    designation = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Example: Senior Executive",
            }
        ),
    )

    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Phone number",
            }
        ),
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter password",
            }
        ),
    )

    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirm password",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "full_name",
            "is_active",
        ]

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Username",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email address",
                }
            ),
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Full name",
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

        self.fields["role"].choices = [
            (role, UserRole(role).label) for role in MANAGEABLE_ORG_ROLES
        ]

        if organization:
            self.fields["department"].queryset = Department.objects.filter(
                organization=organization,
                is_active=True,
            ).order_by("name")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")

        return email

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")

        return username

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")

        role = cleaned_data.get("role")
        department = cleaned_data.get("department")

        if role == UserRole.DEPARTMENT_HEAD and not department:
            self.add_error(
                "department",
                "Department is required for Department Head role.",
            )

        return cleaned_data


class OrganizationUserUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(
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

    designation = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "email",
            "full_name",
            "is_active",
        ]

        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, organization=None, user_obj=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.organization = organization
        self.user_obj = user_obj

        self.fields["role"].choices = [
            (role, UserRole(role).label) for role in MANAGEABLE_ORG_ROLES
        ]

        if organization:
            self.fields["department"].queryset = Department.objects.filter(
                organization=organization,
                is_active=True,
            ).order_by("name")

        profile = getattr(user_obj, "profile", None)

        if profile:
            self.fields["role"].initial = profile.role
            self.fields["department"].initial = profile.department
            self.fields["designation"].initial = profile.designation
            self.fields["phone"].initial = profile.phone

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()

        existing = User.objects.filter(email__iexact=email)

        if self.user_obj:
            existing = existing.exclude(pk=self.user_obj.pk)

        if existing.exists():
            raise forms.ValidationError("A user with this email already exists.")

        return email

    def clean(self):
        cleaned_data = super().clean()

        role = cleaned_data.get("role")
        department = cleaned_data.get("department")

        if role == UserRole.DEPARTMENT_HEAD and not department:
            self.add_error(
                "department",
                "Department is required for Department Head role.",
            )

        return cleaned_data


class OrganizationUserPasswordResetForm(forms.Form):
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter new password",
            }
        ),
    )

    new_password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirm new password",
            }
        ),
    )

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", "Passwords do not match.")

        return cleaned_data
class LoginForm(forms.Form):
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter username or email",
                "autocomplete": "username",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter password",
                "autocomplete": "current-password",
            }
        ),
    )
class OrganizationRegistrationForm(forms.Form):
    organization_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Organization name",
            }
        ),
    )

    organization_email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Organization email",
            }
        ),
    )

    organization_phone = forms.CharField(
        required=False,
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Organization phone",
            }
        ),
    )

    organization_address = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Organization address",
            }
        ),
    )

    organization_logo = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    admin_full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Admin full name",
            }
        ),
    )

    admin_username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Admin username",
            }
        ),
    )

    admin_email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Admin email",
            }
        ),
    )

    admin_phone = forms.CharField(
        required=False,
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Admin phone",
            }
        ),
    )

    admin_password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
            }
        ),
    )

    admin_password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirm password",
            }
        ),
    )

    def clean_organization_name(self):
        name = self.cleaned_data.get("organization_name", "").strip()

        if not name:
            raise forms.ValidationError("Organization name is required.")

        if Organization.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("An organization with this name already exists.")

        return name

    def clean_organization_email(self):
        email = self.cleaned_data.get("organization_email", "").strip().lower()

        if Organization.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An organization with this email already exists.")

        return email

    def clean_organization_phone(self):
        phone = self.cleaned_data.get("organization_phone", "").strip()
        return phone

    def clean_admin_full_name(self):
        full_name = self.cleaned_data.get("admin_full_name", "").strip()

        if not full_name:
            raise forms.ValidationError("Admin full name is required.")

        return full_name

    def clean_admin_username(self):
        username = self.cleaned_data.get("admin_username", "").strip()

        if not username:
            raise forms.ValidationError("Admin username is required.")

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")

        return username

    def clean_admin_email(self):
        email = self.cleaned_data.get("admin_email", "").strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")

        return email

    def clean_admin_phone(self):
        phone = self.cleaned_data.get("admin_phone", "").strip()
        return phone

    def clean_admin_password1(self):
        password = self.cleaned_data.get("admin_password1")
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("admin_password1")
        password2 = cleaned_data.get("admin_password2")

        if password1 and password2 and password1 != password2:
            self.add_error("admin_password2", "Passwords do not match.")

        return cleaned_data

    @transaction.atomic
    def save(self):
        organization = Organization.objects.create(
            name=self.cleaned_data["organization_name"],
            email=self.cleaned_data["organization_email"],
            phone=self.cleaned_data.get("organization_phone", ""),
            address=self.cleaned_data.get("organization_address", ""),
            logo=self.cleaned_data.get("organization_logo"),
            is_active=True,
        )

        user = User.objects.create_user(
            username=self.cleaned_data["admin_username"],
            email=self.cleaned_data["admin_email"],
            password=self.cleaned_data["admin_password1"],
            full_name=self.cleaned_data["admin_full_name"],
            is_active=True,
        )

        profile = getattr(user, "profile", None)

        if profile:
            profile.organization = organization
            profile.role = UserRole.ORG_ADMIN
            profile.phone = self.cleaned_data.get("admin_phone", "")
            profile.designation = "Organization Admin"
            profile.is_active = True
            profile.save(
                update_fields=[
                    "organization",
                    "role",
                    "phone",
                    "designation",
                    "is_active",
                    "updated_at",
                ]
            )

        return organization, user
    
class UserSignatureSettingsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "signature_image",
            "signature_title",
            "signature_enabled",
        ]

        widgets = {
            "signature_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "signature_title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Final Approver, Director, Department Head",
                }
            ),
            "signature_enabled": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_signature_title(self):
        value = self.cleaned_data.get("signature_title", "").strip()

        if len(value) > 120:
            raise forms.ValidationError("Signature title cannot exceed 120 characters.")

        return value