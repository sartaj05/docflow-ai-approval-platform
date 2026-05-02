import os
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import transaction

from apps.documents.models import DocumentAttachmentVersion


def get_file_extension(filename):
    return Path(filename).suffix.lower().replace(".", "")


def copy_file_to_content_file(file_field):
    if not file_field:
        return None

    file_field.open("rb")
    try:
        content = file_field.read()
    finally:
        file_field.close()

    return ContentFile(content)


def get_next_version_number(attachment):
    latest_version = attachment.versions.order_by("-version_number").first()

    if latest_version:
        return latest_version.version_number + 1

    return 1


@transaction.atomic
def create_attachment_snapshot(
    *,
    attachment,
    user=None,
    change_note="",
    is_current_snapshot=True,
):
    """
    Saves current active attachment state into DocumentAttachmentVersion.
    This runs before replacing active file or before rollback.
    """

    version_number = get_next_version_number(attachment)

    file_content = copy_file_to_content_file(attachment.file)

    version = DocumentAttachmentVersion(
        attachment=attachment,
        version_number=version_number,
        original_filename=attachment.original_filename,
        file_type=attachment.file_type,
        file_size=attachment.file_size,
        extracted_text=attachment.extracted_text,
        ai_summary=attachment.ai_summary,
        ai_category=attachment.ai_category,
        ai_extracted_data=attachment.ai_extracted_data or {},
        risk_level=attachment.risk_level,
        risk_notes=attachment.risk_notes,
        processing_error=attachment.processing_error,
        ai_processed=attachment.ai_processed,
        replaced_by=user,
        change_note=change_note,
        is_current_snapshot=is_current_snapshot,
    )

    if file_content:
        filename = os.path.basename(attachment.file.name)
        version.file.save(filename, file_content, save=False)

    version.save()

    return version


@transaction.atomic
def replace_attachment_file(
    *,
    attachment,
    new_file,
    user=None,
    change_note="",
    extracted_text="",
    ai_summary="",
    ai_category="",
    ai_extracted_data=None,
    risk_level="",
    risk_notes="",
    processing_error="",
    ai_processed=False,
):
    """
    1. Snapshot current active attachment into version history.
    2. Replace active attachment file and metadata.
    """

    snapshot = create_attachment_snapshot(
        attachment=attachment,
        user=user,
        change_note=change_note or "Document replaced.",
        is_current_snapshot=True,
    )

    attachment.file = new_file
    attachment.original_filename = new_file.name
    attachment.file_type = get_file_extension(new_file.name)
    attachment.file_size = new_file.size

    attachment.extracted_text = extracted_text or ""
    attachment.ai_summary = ai_summary or ""
    attachment.ai_category = ai_category or ""
    attachment.ai_extracted_data = ai_extracted_data or {}
    attachment.risk_level = risk_level or ""
    attachment.risk_notes = risk_notes or ""
    attachment.processing_error = processing_error or ""
    attachment.ai_processed = ai_processed

    attachment.save(
        update_fields=[
            "file",
            "original_filename",
            "file_type",
            "file_size",
            "extracted_text",
            "ai_summary",
            "ai_category",
            "ai_extracted_data",
            "risk_level",
            "risk_notes",
            "processing_error",
            "ai_processed",
            "updated_at",
        ]
    )

    return snapshot


@transaction.atomic
def rollback_attachment_to_version(
    *,
    attachment,
    version,
    user=None,
    reason="",
):
    """
    1. Snapshot current active attachment.
    2. Restore selected historical version into active attachment.
    """

    current_snapshot = create_attachment_snapshot(
        attachment=attachment,
        user=user,
        change_note=f"Snapshot before rollback. Reason: {reason}",
        is_current_snapshot=True,
    )

    version_file_content = copy_file_to_content_file(version.file)

    if version_file_content:
        filename = os.path.basename(version.file.name)
        attachment.file.save(filename, version_file_content, save=False)

    attachment.original_filename = version.original_filename
    attachment.file_type = version.file_type
    attachment.file_size = version.file_size
    attachment.extracted_text = version.extracted_text
    attachment.ai_summary = version.ai_summary
    attachment.ai_category = version.ai_category
    attachment.ai_extracted_data = version.ai_extracted_data or {}
    attachment.risk_level = version.risk_level
    attachment.risk_notes = version.risk_notes
    attachment.processing_error = version.processing_error
    attachment.ai_processed = version.ai_processed

    attachment.save(
        update_fields=[
            "file",
            "original_filename",
            "file_type",
            "file_size",
            "extracted_text",
            "ai_summary",
            "ai_category",
            "ai_extracted_data",
            "risk_level",
            "risk_notes",
            "processing_error",
            "ai_processed",
            "updated_at",
        ]
    )

    return current_snapshot