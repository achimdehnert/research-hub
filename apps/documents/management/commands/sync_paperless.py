"""Management command: sync documents from Paperless-ngx (ADR-144).

Usage:
    python manage.py sync_paperless           # incremental (last 24h)
    python manage.py sync_paperless --full    # full sync
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.documents.services import sync_all_documents


class Command(BaseCommand):
    help = "Sync documents from Paperless-ngx into DocumentMetadata"

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            default=False,
            help="Full sync (all documents). Default: incremental (last 24h).",
        )

    def handle(self, *args, **options):
        from django.utils import timezone

        modified_after = None
        if not options["full"]:
            modified_after = timezone.now() - timezone.timedelta(days=1)
            self.stdout.write(f"Incremental sync (since {modified_after.isoformat()})...")
        else:
            self.stdout.write("Full sync...")

        result = sync_all_documents(modified_after=modified_after)

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete: {result['created']} created, "
                f"{result['updated']} updated, {result['errors']} errors "
                f"({result['total']} total from Paperless)"
            )
        )
