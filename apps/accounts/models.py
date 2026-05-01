from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    ORG_ADMIN = "ORG_ADMIN", "Organization Admin"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD", "Department Head"
    STAFF = "STAFF", "Staff/User"
    APPROVER = "APPROVER", "Approver"
    AUDITOR = "AUDITOR", "Auditor"


class User(AbstractUser):
    email = models.EmailField(unique=True)

    full_name = models.CharField(max_length=150, blank=True)

    is_email_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.full_name or self.username

    @property
    def display_name(self):
        return self.full_name or self.get_full_name() or self.username


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="user_profiles",
        blank=True,
        null=True,
    )

    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        related_name="user_profiles",
        blank=True,
        null=True,
    )

    role = models.CharField(
        max_length=30,
        choices=UserRole.choices,
        default=UserRole.STAFF,
    )

    phone = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=120, blank=True)

    profile_photo = models.ImageField(
        upload_to="accounts/profile_photos/",
        blank=True,
        null=True,
    )

    # ==============================
    # Digital Signature Settings
    # ==============================

    signature_image = models.ImageField(
        upload_to="accounts/signatures/",
        blank=True,
        null=True,
        help_text="User signature image used for final approval certificates.",
    )

    signature_title = models.CharField(
        max_length=120,
        blank=True,
        help_text="Example: Final Approver, Department Head, Director.",
    )

    signature_enabled = models.BooleanField(
        default=True,
        help_text="Allow this user's signature to appear on approval certificates.",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "role"]),
            models.Index(fields=["role"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.user.display_name} - {self.get_role_display()}"

    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_org_admin(self):
        return self.role == UserRole.ORG_ADMIN

    @property
    def is_department_head(self):
        return self.role == UserRole.DEPARTMENT_HEAD

    @property
    def is_staff_user(self):
        return self.role == UserRole.STAFF

    @property
    def is_approver(self):
        return self.role == UserRole.APPROVER

    @property
    def is_auditor(self):
        return self.role == UserRole.AUDITOR

    @property
    def certificate_signature_title(self):
        if self.signature_title:
            return self.signature_title

        if self.designation:
            return self.designation

        return self.get_role_display()