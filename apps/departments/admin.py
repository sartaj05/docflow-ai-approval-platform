from django.contrib import admin

from apps.departments.models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "organization",
        "head",
        "is_active",
        "created_at",
    ]

    search_fields = [
        "name",
        "organization__name",
        "head__username",
        "head__email",
        "head__full_name",
    ]

    list_filter = [
        "organization",
        "is_active",
        "created_at",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    autocomplete_fields = [
        "organization",
        "head",
        "created_by",
    ]