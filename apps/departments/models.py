from django.conf import settings
from django.db import models


class Department(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="departments",
    )

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="headed_departments",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_departments",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["organization", "name"]
        indexes = [
            models.Index(fields=["organization", "name"]),
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.organization.name}"