from django import forms

from apps.dashboard.models import RestoreJobLog

from apps.dashboard.models import MaintenanceMode
class RestoreUploadForm(forms.ModelForm):
    class Meta:
        model = RestoreJobLog
        fields = [
            "uploaded_file",
            "restore_notes",
        ]

        widgets = {
            "uploaded_file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".json,.sql,.zip",
                }
            ),
            "restore_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Optional notes about this restore file...",
                }
            ),
        }

    def clean_uploaded_file(self):
        uploaded_file = self.cleaned_data["uploaded_file"]

        allowed_extensions = [
            ".json",
            ".sql",
            ".zip",
        ]

        filename = uploaded_file.name.lower()

        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise forms.ValidationError(
                "Only .json, .sql, and .zip restore files are allowed."
            )

        max_size = 1024 * 1024 * 1024  # 1 GB

        if uploaded_file.size > max_size:
            raise forms.ValidationError(
                "Restore file cannot be larger than 1 GB."
            )

        return uploaded_file


class RestoreConfirmForm(forms.Form):
    confirmation_text = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Type RESTORE CONFIRM to continue",
            }
        ),
    )

    def clean_confirmation_text(self):
        value = self.cleaned_data["confirmation_text"].strip()

        if value != "RESTORE CONFIRM":
            raise forms.ValidationError(
                "You must type RESTORE CONFIRM exactly."
            )

        return value
    
    
class MaintenanceModeForm(forms.ModelForm):
    class Meta:
        model = MaintenanceMode
        fields = [
            "title",
            "message",
            "allow_super_admin_bypass",
            "allow_staff_bypass",
            "allowed_ips",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "System Maintenance",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Write the maintenance message users will see...",
                }
            ),
            "allow_super_admin_bypass": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "allow_staff_bypass": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "allowed_ips": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Example: 127.0.0.1,192.168.1.10",
                }
            ),
        }