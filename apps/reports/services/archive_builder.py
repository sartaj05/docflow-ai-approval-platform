import os
import zipfile
from io import BytesIO

from django.utils import timezone


def safe_text(value):
    if value is None:
        return "-"

    return str(value)


def build_request_metadata_text(document_request):
    lines = [
        "DOCFLOW AI - REQUEST METADATA",
        "=" * 60,
        "",
        f"Request Number : {document_request.request_number}",
        f"Title          : {document_request.title}",
        f"Organization   : {document_request.organization.name if document_request.organization else '-'}",
        f"Department     : {document_request.department.name if document_request.department else '-'}",
        f"Created By     : {document_request.created_by.display_name if document_request.created_by else '-'}",
        f"Workflow       : {document_request.workflow.name if document_request.workflow else '-'}",
        f"Category       : {document_request.get_category_display()}",
        f"Priority       : {document_request.get_priority_display()}",
        f"Status         : {document_request.get_status_display()}",
        f"Risk Level     : {document_request.risk_level or '-'}",
        "",
        "DATES",
        "-" * 60,
        f"Created At     : {document_request.created_at}",
        f"Submitted At   : {document_request.submitted_at or '-'}",
        f"Approved At    : {document_request.approved_at or '-'}",
        f"Rejected At    : {document_request.rejected_at or '-'}",
        "",
        "DESCRIPTION",
        "-" * 60,
        safe_text(document_request.description),
        "",
    ]

    return "\n".join(lines)


def build_ai_ocr_summary_text(document_request, attachments):
    lines = [
        "DOCFLOW AI - AI / OCR SUMMARY",
        "=" * 60,
        "",
        "REQUEST AI RESULT",
        "-" * 60,
        f"AI Summary      : {document_request.ai_summary or '-'}",
        f"AI Category     : {document_request.ai_category or '-'}",
        f"Risk Level      : {document_request.risk_level or '-'}",
        f"Risk Notes      : {document_request.risk_notes or '-'}",
        f"Extracted Data  : {document_request.ai_extracted_data or '-'}",
        "",
        "ATTACHMENT AI / OCR RESULT",
        "-" * 60,
    ]

    for attachment in attachments:
        lines.extend(
            [
                "",
                f"File Name       : {attachment.original_filename}",
                f"File Type       : {attachment.file_type}",
                f"File Size       : {attachment.file_size}",
                f"AI Processed    : {attachment.ai_processed}",
                f"AI Summary      : {attachment.ai_summary or '-'}",
                f"AI Category     : {attachment.ai_category or '-'}",
                f"Risk Level      : {attachment.risk_level or '-'}",
                f"Risk Notes      : {attachment.risk_notes or '-'}",
                f"OCR Used        : {getattr(attachment, 'ocr_used', False)}",
                f"OCR Confidence  : {getattr(attachment, 'ocr_confidence', '-')}",
                f"OCR Status      : {getattr(attachment, 'ocr_status', '-')}",
                "",
                "Extracted Text:",
                safe_text(attachment.extracted_text),
                "-" * 60,
            ]
        )

    return "\n".join(lines)


def build_approval_timeline_text(document_request, approval_steps, approval_actions):
    lines = [
        "DOCFLOW AI - APPROVAL TIMELINE",
        "=" * 60,
        "",
        "APPROVAL STEPS",
        "-" * 60,
    ]

    for step in approval_steps:
        lines.extend(
            [
                "",
                f"Step Order      : {step.step_order}",
                f"Role Required   : {step.role_required}",
                f"Assigned To     : {step.assigned_to.display_name if step.assigned_to else '-'}",
                f"Status          : {step.get_status_display()}",
                f"Is Current      : {step.is_current}",
                f"Due At          : {getattr(step, 'due_at', '-') or '-'}",
                f"Approved At     : {step.approved_at or '-'}",
                f"Rejected At     : {step.rejected_at or '-'}",
                f"Comments        : {step.comments or '-'}",
            ]
        )

    lines.extend(
        [
            "",
            "",
            "APPROVAL ACTIONS",
            "-" * 60,
        ]
    )

    for action in approval_actions:
        lines.extend(
            [
                "",
                f"Action          : {action.get_action_type_display()}",
                f"Step            : {action.step.step_order if action.step else '-'}",
                f"Action By       : {action.action_by.display_name if action.action_by else 'System'}",
                f"Old Status      : {action.old_status or '-'}",
                f"New Status      : {action.new_status or '-'}",
                f"Comment         : {action.comment or '-'}",
                f"Created At      : {action.created_at}",
            ]
        )

    return "\n".join(lines)


def build_version_history_text(attachments):
    lines = [
        "DOCFLOW AI - DOCUMENT VERSION HISTORY",
        "=" * 60,
        "",
    ]

    for attachment in attachments:
        lines.extend(
            [
                "",
                f"CURRENT FILE: {attachment.original_filename}",
                "-" * 60,
                f"Current Version : v{attachment.current_version_number}",
                f"Total Versions  : {attachment.total_versions}",
                f"File Type       : {attachment.file_type}",
                f"File Size       : {attachment.file_size}",
                "",
                "Previous Versions:",
            ]
        )

        versions = attachment.versions.select_related("replaced_by").order_by("-version_number")

        if not versions:
            lines.append("No previous versions found.")
            continue

        for version in versions:
            lines.extend(
                [
                    "",
                    f"Version         : v{version.version_number}",
                    f"Filename        : {version.original_filename}",
                    f"File Type       : {version.file_type}",
                    f"File Size       : {version.file_size}",
                    f"Changed By      : {version.replaced_by.display_name if version.replaced_by else 'System'}",
                    f"Change Note     : {version.change_note or '-'}",
                    f"Created At      : {version.created_at}",
                ]
            )

    return "\n".join(lines)


def add_file_to_zip(zip_file, file_field, folder_name, fallback_name):
    if not file_field:
        return

    try:
        if not file_field.path or not os.path.exists(file_field.path):
            return

        filename = os.path.basename(file_field.name) or fallback_name
        zip_path = f"{folder_name}/{filename}"

        zip_file.write(file_field.path, zip_path)

    except Exception:
        return


def build_request_archive_zip(document_request):
    attachments = (
        document_request.attachments
        .select_related("uploaded_by")
        .prefetch_related("versions")
        .order_by("created_at")
    )

    approval_steps = (
        document_request.approval_steps
        .select_related("assigned_to")
        .order_by("step_order")
    )

    approval_actions = (
        document_request.approval_actions
        .select_related("action_by", "step")
        .order_by("created_at")
    )

    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(
            "01_request_metadata.txt",
            build_request_metadata_text(document_request),
        )

        zip_file.writestr(
            "02_ai_ocr_summary.txt",
            build_ai_ocr_summary_text(document_request, attachments),
        )

        zip_file.writestr(
            "03_approval_timeline.txt",
            build_approval_timeline_text(
                document_request,
                approval_steps,
                approval_actions,
            ),
        )

        zip_file.writestr(
            "04_document_version_history.txt",
            build_version_history_text(attachments),
        )

        zip_file.writestr(
            "README.txt",
            (
                "DocFlow AI Final Approval Archive\n"
                "=================================\n\n"
                f"Generated At: {timezone.now()}\n"
                f"Request    : {document_request.request_number}\n\n"
                "Folders:\n"
                "- attachments/current_files contains active uploaded documents.\n"
                "- attachments/version_history contains previous versions.\n"
                "- TXT files contain metadata, AI/OCR summary, approval timeline, and version history.\n"
            ),
        )

        for attachment in attachments:
            add_file_to_zip(
                zip_file=zip_file,
                file_field=attachment.file,
                folder_name="attachments/current_files",
                fallback_name=attachment.original_filename,
            )

            for version in attachment.versions.all():
                add_file_to_zip(
                    zip_file=zip_file,
                    file_field=version.file,
                    folder_name=f"attachments/version_history/{attachment.pk}",
                    fallback_name=version.original_filename,
                )

    zip_buffer.seek(0)

    return zip_buffer