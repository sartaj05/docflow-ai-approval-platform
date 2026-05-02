from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.approvals.models import DocumentRequest, RequestStatus
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.documents.forms import (
    DocumentAttachmentUploadForm,
    DocumentReplaceForm,
    ManualTextCorrectionForm,
    VersionRollbackForm,
)
from apps.documents.models import DocumentAttachment, DocumentAttachmentVersion
from apps.documents.services.ai_processor import process_attachment_with_ai
from apps.documents.services.file_helpers import get_file_type
from apps.documents.services.pdf_extractor import extract_text_from_pdf
from apps.documents.services.versioning import (
    replace_attachment_file,
    rollback_attachment_to_version,
)

from apps.documents.models import (
    DocumentAIProcessingHistory,
    DocumentAttachment,
    DocumentAttachmentVersion,
)
from apps.documents.services.ai_reprocessor import rerun_ai_for_attachment
# ==========================================================
# Permission / scope helpers
# ==========================================================

def get_user_profile(user):
    return getattr(user, "profile", None)


def get_scoped_document_request_queryset(user):
    if user.is_superuser:
        return DocumentRequest.objects.select_related(
            "organization",
            "department",
            "created_by",
            "workflow",
        ).all()

    profile = get_user_profile(user)

    if not profile or not profile.organization:
        return DocumentRequest.objects.none()

    qs = DocumentRequest.objects.select_related(
        "organization",
        "department",
        "created_by",
        "workflow",
    ).filter(
        organization=profile.organization,
    )

    if profile.role == UserRole.ORG_ADMIN:
        return qs

    if profile.role == UserRole.DEPARTMENT_HEAD:
        if profile.department:
            return qs.filter(department=profile.department)

        return DocumentRequest.objects.none()

    if profile.role == UserRole.STAFF:
        return qs.filter(created_by=user)

    if profile.role == UserRole.APPROVER:
        return qs.filter(approval_steps__assigned_to=user).distinct()

    if profile.role == UserRole.AUDITOR:
        return qs

    return DocumentRequest.objects.none()


def can_upload_documents(user, document_request):
    if user.is_superuser:
        return False

    if document_request.created_by_id != user.id:
        return False

    return document_request.status == RequestStatus.DRAFT


def can_delete_document(user, attachment):
    if user.is_superuser:
        return False

    if attachment.request.created_by_id != user.id:
        return False

    return attachment.request.status == RequestStatus.DRAFT


def can_replace_attachment(user, attachment):
    if user.is_superuser:
        return False

    document_request = attachment.request

    if document_request.status != RequestStatus.DRAFT:
        return False

    return document_request.created_by_id == user.id


def can_rollback_attachment(user, attachment):
    if user.is_superuser:
        return False

    document_request = attachment.request

    if document_request.status != RequestStatus.DRAFT:
        return False

    return document_request.created_by_id == user.id


def can_view_attachment_versions(user, attachment):
    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    if not profile:
        return False

    if profile.organization_id != attachment.request.organization_id:
        return False

    if attachment.request.created_by_id == user.id:
        return True

    if profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.DEPARTMENT_HEAD,
        UserRole.APPROVER,
        UserRole.AUDITOR,
    ]:
        return True

    return False


def can_correct_attachment_text(user, attachment):
    if user.is_superuser:
        return False

    document_request = attachment.request
    profile = getattr(user, "profile", None)

    if not profile:
        return False

    if profile.organization_id != document_request.organization_id:
        return False

    if document_request.created_by_id == user.id:
        return True

    return profile.role in [
        UserRole.ORG_ADMIN,
        UserRole.DEPARTMENT_HEAD,
        UserRole.AUDITOR,
    ]


# ==========================================================
# Extraction helper
# ==========================================================

def extract_text_for_attachment(attachment):
    """
    Extract text from attachment and save result.

    This supports both old extractor style:
        extracted_text, error = extract_text_from_pdf(path)

    And new OCR extractor style:
        {"text": "...", "ocr_used": True, ...}
    """

    if not attachment.is_pdf:
        attachment.processing_error = "AI text extraction currently supports PDF files only."
        attachment.save(
            update_fields=[
                "processing_error",
            ]
        )
        return False

    result = extract_text_from_pdf(attachment.file.path)

    extracted_text = ""
    error = ""

    if isinstance(result, dict):
        extracted_text = result.get("text", "") or ""
        error = result.get("error", "") or ""

        if hasattr(attachment, "ocr_used"):
            attachment.ocr_used = result.get("ocr_used", False)

        if hasattr(attachment, "ocr_confidence"):
            attachment.ocr_confidence = result.get("ocr_confidence")

        if hasattr(attachment, "ocr_status"):
            attachment.ocr_status = result.get("ocr_status", "NOT_REQUIRED")

    else:
        extracted_text, error = result

    attachment.extracted_text = extracted_text or ""
    attachment.processing_error = error or ""

    update_fields = [
        "extracted_text",
        "processing_error",
    ]

    if hasattr(attachment, "ocr_used"):
        update_fields.append("ocr_used")

    if hasattr(attachment, "ocr_confidence"):
        update_fields.append("ocr_confidence")

    if hasattr(attachment, "ocr_status"):
        update_fields.append("ocr_status")

    if hasattr(attachment, "updated_at"):
        update_fields.append("updated_at")

    attachment.save(update_fields=update_fields)

    return bool(attachment.extracted_text)


# ==========================================================
# Upload
# ==========================================================

@login_required
def attachment_upload(request, request_pk):
    document_request = get_object_or_404(
        get_scoped_document_request_queryset(request.user),
        pk=request_pk,
    )

    if not can_upload_documents(request.user, document_request):
        messages.error(
            request,
            "You can upload documents only for your own draft requests.",
        )
        return redirect("approvals:request_detail", pk=document_request.pk)

    form = DocumentAttachmentUploadForm(
        request.POST or None,
        request.FILES or None,
        organization=document_request.organization,
    )

    if request.method == "POST":
        if form.is_valid():
            files = request.FILES.getlist("files")

            if not files:
                files = form.cleaned_data.get("files", [])

            uploaded_count = 0
            ai_success_count = 0
            ai_failed_count = 0

            for uploaded_file in files:
                attachment = DocumentAttachment.objects.create(
                    request=document_request,
                    uploaded_by=request.user,
                    file=uploaded_file,
                    original_filename=uploaded_file.name,
                    file_type=get_file_type(uploaded_file.name),
                    file_size=uploaded_file.size,
                )

                extraction_success = extract_text_for_attachment(attachment)

                extra_data = {
                    "request_id": document_request.pk,
                    "file_type": attachment.file_type,
                    "file_size": attachment.file_size,
                    "text_extracted": bool(attachment.extracted_text),
                    "processing_error": attachment.processing_error,
                }

                if hasattr(attachment, "ocr_used"):
                    extra_data["ocr_used"] = attachment.ocr_used

                if hasattr(attachment, "ocr_confidence"):
                    extra_data["ocr_confidence"] = attachment.ocr_confidence

                if hasattr(attachment, "ocr_status"):
                    extra_data["ocr_status"] = attachment.ocr_status

                create_audit_log(
                    request=request,
                    organization=document_request.organization,
                    action=AuditAction.UPLOADED,
                    model_name="DocumentAttachment",
                    object_id=attachment.pk,
                    message=f"Document '{attachment.original_filename}' uploaded for {document_request.request_number}.",
                    extra_data=extra_data,
                )

                uploaded_count += 1

                if extraction_success and attachment.extracted_text:
                    ai_result = process_attachment_with_ai(
                        attachment=attachment,
                        request=request,
                    )

                    if ai_result.get("success"):
                        ai_success_count += 1
                    else:
                        ai_failed_count += 1

                else:
                    ai_failed_count += 1

            success_message = f"{uploaded_count} document(s) uploaded successfully."

            if ai_success_count:
                success_message += f" AI processed {ai_success_count} document(s)."

            if ai_failed_count:
                success_message += f" AI pending/failed for {ai_failed_count} document(s). Check document detail."

            messages.success(request, success_message)

            return redirect("approvals:request_detail", pk=document_request.pk)

    return render(
        request,
        "documents/attachment_upload.html",
        {
            "page_title": "Upload Documents",
            "form": form,
            "document_request": document_request,
        },
    )


# ==========================================================
# Detail / Delete / AI
# ==========================================================

@login_required
def attachment_detail(request, pk):
    attachment = get_object_or_404(
        DocumentAttachment.objects.select_related(
            "request",
            "request__organization",
            "request__department",
            "uploaded_by",
            "manual_corrected_by",
        ),
        pk=pk,
    )

    document_request = get_object_or_404(
        get_scoped_document_request_queryset(request.user),
        pk=attachment.request_id,
    )

    return render(
        request,
        "documents/attachment_detail.html",
        {
            "page_title": attachment.original_filename,
            "attachment": attachment,
            "document_request": document_request,
            "can_delete": can_delete_document(request.user, attachment),
            "can_correct_text": can_correct_attachment_text(request.user, attachment),
        },
    )


@login_required
def attachment_delete(request, pk):
    attachment = get_object_or_404(
        DocumentAttachment.objects.select_related(
            "request",
            "request__organization",
        ),
        pk=pk,
    )

    document_request = get_object_or_404(
        get_scoped_document_request_queryset(request.user),
        pk=attachment.request_id,
    )

    if not can_delete_document(request.user, attachment):
        messages.error(
            request,
            "You can delete documents only from your own draft requests.",
        )
        return redirect("approvals:request_detail", pk=document_request.pk)

    if request.method == "POST":
        file_name = attachment.original_filename

        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.DELETED,
            model_name="DocumentAttachment",
            object_id=attachment.pk,
            message=f"Document '{attachment.original_filename}' deleted from {document_request.request_number}.",
            extra_data={
                "request_id": document_request.pk,
                "file_name": attachment.original_filename,
                "ai_processed": attachment.ai_processed,
                "risk_level": attachment.risk_level,
            },
        )

        if attachment.file:
            attachment.file.delete(save=False)

        attachment.delete()

        messages.success(
            request,
            f"Document '{file_name}' deleted successfully.",
        )
        return redirect("approvals:request_detail", pk=document_request.pk)

    return render(
        request,
        "documents/attachment_confirm_delete.html",
        {
            "page_title": "Delete Document",
            "attachment": attachment,
            "document_request": document_request,
        },
    )


@login_required
def attachment_process_ai(request, pk):
    attachment = get_object_or_404(
        DocumentAttachment.objects.select_related(
            "request",
            "request__organization",
            "request__created_by",
        ),
        pk=pk,
    )

    document_request = get_object_or_404(
        get_scoped_document_request_queryset(request.user),
        pk=attachment.request_id,
    )

    if request.method != "POST":
        return redirect("documents:attachment_detail", pk=attachment.pk)

    if not can_upload_documents(request.user, document_request):
        messages.error(
            request,
            "You can reprocess AI only for your own draft request documents.",
        )
        return redirect("documents:attachment_detail", pk=attachment.pk)

    if not attachment.extracted_text:
        extracted = extract_text_for_attachment(attachment)

        if not extracted:
            messages.error(
                request,
                "No readable text found. AI processing cannot continue.",
            )
            return redirect("documents:attachment_detail", pk=attachment.pk)

    result = process_attachment_with_ai(
        attachment=attachment,
        request=request,
    )

    if result.get("success"):
        messages.success(request, "AI processing completed successfully.")
    else:
        messages.error(
            request,
            f"AI processing failed: {result.get('error')}",
        )

    return redirect("documents:attachment_detail", pk=attachment.pk)


# ==========================================================
# Manual correction
# ==========================================================

@login_required
def attachment_manual_correction(request, pk):
    attachment = get_object_or_404(
        DocumentAttachment.objects.select_related(
            "request",
            "request__organization",
            "request__created_by",
            "manual_corrected_by",
        ),
        pk=pk,
    )

    document_request = get_object_or_404(
        get_scoped_document_request_queryset(request.user),
        pk=attachment.request_id,
    )

    if not can_correct_attachment_text(request.user, attachment):
        messages.error(request, "You do not have permission to correct this document text.")
        return redirect("documents:attachment_detail", pk=attachment.pk)

    initial_text = ""

    if hasattr(attachment, "manual_corrected_text") and attachment.manual_corrected_text:
        initial_text = attachment.manual_corrected_text
    else:
        initial_text = attachment.extracted_text or ""

    form = ManualTextCorrectionForm(
        request.POST or None,
        initial={
            "corrected_text": initial_text,
        },
    )

    if request.method == "POST":
        if form.is_valid():
            corrected_text = form.cleaned_data["corrected_text"].strip()

            attachment.extracted_text = corrected_text

            update_fields = [
                "extracted_text",
                "processing_error",
            ]

            attachment.processing_error = ""

            if hasattr(attachment, "manual_corrected_text"):
                attachment.manual_corrected_text = corrected_text
                update_fields.append("manual_corrected_text")

            if hasattr(attachment, "ocr_status"):
                attachment.ocr_status = "MANUAL_CORRECTED"
                update_fields.append("ocr_status")

            if hasattr(attachment, "manual_corrected_by"):
                attachment.manual_corrected_by = request.user
                update_fields.append("manual_corrected_by")

            if hasattr(attachment, "manual_corrected_at"):
                attachment.manual_corrected_at = timezone.now()
                update_fields.append("manual_corrected_at")

            if hasattr(attachment, "updated_at"):
                update_fields.append("updated_at")

            attachment.save(update_fields=update_fields)

            create_audit_log(
                request=request,
                organization=document_request.organization,
                action=AuditAction.UPDATED,
                model_name="DocumentAttachment",
                object_id=attachment.pk,
                message=f"Manual text correction completed for {attachment.original_filename}.",
                extra_data={
                    "request_number": document_request.request_number,
                    "filename": attachment.original_filename,
                    "corrected_by": request.user.display_name,
                    "ocr_confidence": getattr(attachment, "ocr_confidence", None),
                    "ocr_status": getattr(attachment, "ocr_status", ""),
                },
            )

            messages.success(request, "Document text corrected successfully.")
            return redirect("documents:attachment_detail", pk=attachment.pk)

    return render(
        request,
        "documents/attachment_manual_correction.html",
        {
            "page_title": "Manual Text Correction",
            "attachment": attachment,
            "document_request": document_request,
            "form": form,
        },
    )


# ==========================================================
# Versioning
# ==========================================================

@login_required
def attachment_replace(request, pk):
    attachment = get_object_or_404(
        DocumentAttachment.objects.select_related(
            "request",
            "request__organization",
            "request__created_by",
        ),
        pk=pk,
    )

    document_request = attachment.request

    if not can_replace_attachment(request.user, attachment):
        messages.error(request, "You can replace documents only while the request is in Draft status.")
        return redirect("documents:attachment_detail", pk=attachment.pk)

    form = DocumentReplaceForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if form.is_valid():
            new_file = form.cleaned_data["file"]
            change_note = form.cleaned_data.get("change_note", "")

            snapshot = replace_attachment_file(
                attachment=attachment,
                new_file=new_file,
                user=request.user,
                change_note=change_note,
            )

            extraction_success = extract_text_for_attachment(attachment)

            if extraction_success and attachment.extracted_text:
                process_attachment_with_ai(
                    attachment=attachment,
                    request=request,
                )

            create_audit_log(
                request=request,
                organization=document_request.organization,
                action=AuditAction.UPDATED,
                model_name="DocumentAttachment",
                object_id=attachment.pk,
                message=(
                    f"Document {attachment.original_filename} replaced for "
                    f"{document_request.request_number}."
                ),
                extra_data={
                    "request_number": document_request.request_number,
                    "snapshot_version": snapshot.version_number,
                    "new_filename": new_file.name,
                    "change_note": change_note,
                    "ocr_used": getattr(attachment, "ocr_used", False),
                    "ocr_confidence": getattr(attachment, "ocr_confidence", None),
                    "ocr_status": getattr(attachment, "ocr_status", ""),
                },
            )

            messages.success(
                request,
                "Document replaced successfully. Previous file saved in version history.",
            )
            return redirect("documents:attachment_detail", pk=attachment.pk)

    return render(
        request,
        "documents/attachment_replace.html",
        {
            "page_title": "Replace Document",
            "attachment": attachment,
            "document_request": document_request,
            "form": form,
        },
    )


@login_required
def attachment_versions(request, pk):
    attachment = get_object_or_404(
        DocumentAttachment.objects.select_related(
            "request",
            "request__organization",
            "uploaded_by",
        ),
        pk=pk,
    )

    if not can_view_attachment_versions(request.user, attachment):
        messages.error(request, "You do not have permission to view document versions.")
        return redirect("approvals:request_list")

    versions = attachment.versions.select_related("replaced_by").order_by("-version_number")

    return render(
        request,
        "documents/attachment_versions.html",
        {
            "page_title": "Document Versions",
            "attachment": attachment,
            "document_request": attachment.request,
            "versions": versions,
            "can_rollback": can_rollback_attachment(request.user, attachment),
        },
    )


@login_required
def attachment_version_compare(request, pk, version_pk):
    attachment = get_object_or_404(
        DocumentAttachment.objects.select_related(
            "request",
            "request__organization",
        ),
        pk=pk,
    )

    version = get_object_or_404(
        DocumentAttachmentVersion.objects.select_related(
            "attachment",
            "replaced_by",
        ),
        pk=version_pk,
        attachment=attachment,
    )

    if not can_view_attachment_versions(request.user, attachment):
        messages.error(request, "You do not have permission to compare document versions.")
        return redirect("approvals:request_list")

    return render(
        request,
        "documents/attachment_version_compare.html",
        {
            "page_title": "Compare Document Version",
            "attachment": attachment,
            "version": version,
            "document_request": attachment.request,
            "can_rollback": can_rollback_attachment(request.user, attachment),
        },
    )


@login_required
def attachment_rollback(request, pk, version_pk):
    attachment = get_object_or_404(
        DocumentAttachment.objects.select_related(
            "request",
            "request__organization",
        ),
        pk=pk,
    )

    version = get_object_or_404(
        DocumentAttachmentVersion.objects.select_related(
            "attachment",
            "replaced_by",
        ),
        pk=version_pk,
        attachment=attachment,
    )

    document_request = attachment.request

    if not can_rollback_attachment(request.user, attachment):
        messages.error(request, "Rollback is allowed only while request is in Draft status.")
        return redirect("documents:attachment_versions", pk=attachment.pk)

    form = VersionRollbackForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            reason = form.cleaned_data["reason"]

            rollback_attachment_to_version(
                attachment=attachment,
                version=version,
                user=request.user,
                reason=reason,
            )

            extraction_success = extract_text_for_attachment(attachment)

            if extraction_success and attachment.extracted_text:
                process_attachment_with_ai(
                    attachment=attachment,
                    request=request,
                )

            create_audit_log(
                request=request,
                organization=document_request.organization,
                action=AuditAction.UPDATED,
                model_name="DocumentAttachment",
                object_id=attachment.pk,
                message=(
                    f"Document rolled back to version {version.version_number} "
                    f"for {document_request.request_number}."
                ),
                extra_data={
                    "request_number": document_request.request_number,
                    "rollback_version": version.version_number,
                    "reason": reason,
                },
            )

            messages.success(request, f"Document rolled back to version {version.version_number}.")
            return redirect("documents:attachment_detail", pk=attachment.pk)

    return render(
        request,
        "documents/attachment_rollback_confirm.html",
        {
            "page_title": "Rollback Document",
            "attachment": attachment,
            "version": version,
            "document_request": document_request,
            "form": form,
        },
    )
    
@login_required
def attachment_reprocess_ai(request, pk):
    attachment = get_object_or_404(
        DocumentAttachment.objects.select_related(
            "request",
            "request__organization",
            "request__created_by",
            "manual_corrected_by",
        ),
        pk=pk,
    )

    document_request = get_object_or_404(
        get_scoped_document_request_queryset(request.user),
        pk=attachment.request_id,
    )

    if request.method != "POST":
        return redirect("documents:attachment_detail", pk=attachment.pk)

    if not can_correct_attachment_text(request.user, attachment):
        messages.error(request, "You do not have permission to re-run AI for this document.")
        return redirect("documents:attachment_detail", pk=attachment.pk)

    result = rerun_ai_for_attachment(
        attachment=attachment,
        request=request,
        processed_by=request.user,
    )

    create_audit_log(
        request=request,
        organization=document_request.organization,
        action=AuditAction.UPDATED,
        model_name="DocumentAttachment",
        object_id=attachment.pk,
        message=f"AI reprocessing triggered for {attachment.original_filename}.",
        extra_data={
            "request_number": document_request.request_number,
            "filename": attachment.original_filename,
            "success": result.get("success"),
            "error": result.get("error", ""),
            "history_id": result["history"].pk if result.get("history") else "",
        },
    )

    if result.get("success"):
        messages.success(request, "AI reprocessing completed successfully.")
    else:
        messages.error(
            request,
            f"AI reprocessing failed: {result.get('error')}",
        )

    return redirect("documents:attachment_detail", pk=attachment.pk)

@login_required
def attachment_ai_history(request, pk):
    attachment = get_object_or_404(
        DocumentAttachment.objects.select_related(
            "request",
            "request__organization",
            "uploaded_by",
            "manual_corrected_by",
        ),
        pk=pk,
    )

    document_request = get_object_or_404(
        get_scoped_document_request_queryset(request.user),
        pk=attachment.request_id,
    )

    if not can_view_attachment_versions(request.user, attachment):
        messages.error(request, "You do not have permission to view AI history.")
        return redirect("approvals:request_list")

    history_items = (
        attachment.ai_processing_history.select_related(
            "processed_by",
            "version",
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "documents/attachment_ai_history.html",
        {
            "page_title": "AI Processing History",
            "attachment": attachment,
            "document_request": document_request,
            "history_items": history_items,
            "can_reprocess_ai": can_correct_attachment_text(request.user, attachment),
        },
    )