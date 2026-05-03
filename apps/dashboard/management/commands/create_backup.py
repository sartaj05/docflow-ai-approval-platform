from django.core.management.base import BaseCommand

from apps.dashboard.services.backup_export_service import (
    create_audit_log_export_csv,
    create_database_backup,
    create_full_backup_zip,
    create_media_backup_zip,
    create_notification_delivery_export_csv,
    create_request_export_csv,
)


class Command(BaseCommand):
    help = "Create DocFlow AI backup/export files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            choices=[
                "database",
                "media",
                "full",
                "audit",
                "notifications",
                "requests",
            ],
            default="full",
            help="Backup/export type to create.",
        )

    def handle(self, *args, **options):
        backup_type = options["type"]

        if backup_type == "database":
            file_path = create_database_backup(prefer_pg_dump=True)

        elif backup_type == "media":
            file_path = create_media_backup_zip()

        elif backup_type == "audit":
            file_path = create_audit_log_export_csv()

        elif backup_type == "notifications":
            file_path = create_notification_delivery_export_csv()

        elif backup_type == "requests":
            file_path = create_request_export_csv()

        else:
            file_path = create_full_backup_zip()

        self.stdout.write(
            self.style.SUCCESS(
                f"{backup_type} backup/export created: {file_path}"
            )
        )