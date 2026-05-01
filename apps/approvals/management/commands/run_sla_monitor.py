from django.core.management.base import BaseCommand

from apps.approvals.services.sla_engine import run_sla_monitor


class Command(BaseCommand):
    help = "Run SLA monitor manually."

    def handle(self, *args, **options):
        summary = run_sla_monitor()

        self.stdout.write(
            self.style.SUCCESS(
                f"SLA monitor completed. "
                f"Checked: {summary['checked']}, "
                f"Reminders: {summary['reminders_sent']}, "
                f"Overdue: {summary['overdue_marked']}, "
                f"Escalated: {summary['escalated']}"
            )
        )