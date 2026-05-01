from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import User, UserProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = [
        "username",
        "email",
        "full_name",
        "is_staff",
        "is_superuser",
        "is_active",
        "created_at",
    ]

    search_fields = [
        "username",
        "email",
        "full_name",
        "first_name",
        "last_name",
    ]

    list_filter = [
        "is_staff",
        "is_superuser",
        "is_active",
        "created_at",
    ]

    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "DocFlow AI Extra Fields",
            {
                "fields": (
                    "full_name",
                    "is_email_verified",
                )
            },
        ),
    )

    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            "DocFlow AI Extra Fields",
            {
                "fields": (
                    "email",
                    "full_name",
                )
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "organization",
        "department",
        "role",
        "phone",
        "designation",
        "is_active",
        "created_at",
    ]

    search_fields = [
        "user__username",
        "user__email",
        "user__full_name",
        "organization__name",
        "department__name",
        "phone",
        "designation",
    ]

    list_filter = [
        "role",
        "organization",
        "department",
        "is_active",
        "created_at",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]