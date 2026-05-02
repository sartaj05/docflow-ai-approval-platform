from django import forms

from apps.notifications.models import NotificationPreference


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = [
            "in_app_enabled",
            "email_enabled",

            "watched_request_in_app",
            "watched_request_email",

            "comments_in_app",
            "comments_email",

            "approvals_in_app",
            "approvals_email",

            "documents_in_app",
            "documents_email",

            "ai_in_app",
            "ai_email",

            "reminders_in_app",
            "reminders_email",

            "certificates_in_app",
            "certificates_email",

            "daily_summary_email",
        ]

        widgets = {
            "in_app_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "email_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "watched_request_in_app": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "watched_request_email": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "comments_in_app": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "comments_email": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "approvals_in_app": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "approvals_email": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "documents_in_app": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "documents_email": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "ai_in_app": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "ai_email": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "reminders_in_app": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "reminders_email": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "certificates_in_app": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "certificates_email": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "daily_summary_email": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }