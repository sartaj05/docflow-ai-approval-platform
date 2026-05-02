from django.core.management.base import BaseCommand

from apps.documents.models import DocumentAttachment
from apps.documents.services.document_processor import process_document_file


class Command(BaseCommand):
    help = "Re-run OCR/document extraction for attachments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--failed-only",
            action="store_true",
            help="Only process OCR failed or low confidence documents.",
        )

    def handle(self, *args, **options):
        qs = DocumentAttachment.objects.all()

        if options["failed_only"]:
            qs = qs.filter(
                ocr_status__in=[
                    "FAILED",
                    "LOW_CONFIDENCE",
                ]
            )

        total = qs.count()
        processed = 0

        for attachment in qs:
            if not attachment.file:
                continue

            result = process_document_file(
                file_path=attachment.file.path,
                filename=attachment.original_filename,
            )

            attachment.extracted_text = result.get("text", "")
            attachment.ocr_used = result.get("ocr_used", False)
            attachment.ocr_confidence = result.get("ocr_confidence")
            attachment.ocr_status = result.get("ocr_status", "NOT_REQUIRED")
            attachment.processing_error = result.get("error", "")
            attachment.save(
                update_fields=[
                    "extracted_text",
                    "ocr_used",
                    "ocr_confidence",
                    "ocr_status",
                    "processing_error",
                    "updated_at",
                ]
            )

            processed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"OCR completed. Processed {processed}/{total} attachments."
            )
        )