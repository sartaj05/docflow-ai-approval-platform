import os

from django import forms

from apps.documents.models import DocumentAttachment


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            return [single_file_clean(file, initial) for file in data]

        return single_file_clean(data, initial)


class DocumentAttachmentUploadForm(forms.Form):
    files = MultipleFileField(
        required=True,
        widget=MultipleFileInput(
            attrs={
                "class": "form-control",
                "multiple": True,
            }
        ),
        help_text="Upload one or multiple documents.",
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization

    def clean_files(self):
        files = self.cleaned_data["files"]

        if not isinstance(files, list):
            files = [files]

        if self.organization:
            allowed_extensions = self.organization.allowed_extensions_list
            max_size = self.organization.max_upload_size_bytes
        else:
            allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]
            max_size = 10 * 1024 * 1024

        for uploaded_file in files:
            ext = os.path.splitext(uploaded_file.name)[1].lower()

            if ext not in allowed_extensions:
                raise forms.ValidationError(
                    f"{uploaded_file.name} is not allowed. Allowed: {', '.join(allowed_extensions)}"
                )

            if uploaded_file.size > max_size:
                raise forms.ValidationError(
                    f"{uploaded_file.name} is too large. Max size: {max_size // (1024 * 1024)} MB."
                )

        return files
    
    
from django import forms


class DocumentReplaceForm(forms.Form):
    file = forms.FileField(
        required=True,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".pdf,.jpg,.jpeg,.png,.doc,.docx",
            }
        ),
        help_text="Upload replacement file. Supported: PDF, JPG, JPEG, PNG, DOC, DOCX.",
    )

    change_note = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Optional note explaining why this document is being replaced...",
            }
        ),
    )


class VersionRollbackForm(forms.Form):
    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Reason for rollback is required...",
            }
        ),
    )
    
class ManualTextCorrectionForm(forms.Form):
    corrected_text = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control correction-textarea",
                "rows": 18,
                "placeholder": "Review and correct extracted/OCR text here...",
            }
        ),
    )