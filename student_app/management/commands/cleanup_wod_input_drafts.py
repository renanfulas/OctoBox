"""Expira e remove rascunhos WOD antigos no schema tenant corrente."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from shared_support.tenant_sweep import (
    add_tenant_sweep_arguments, sweep_active_tenants, write_tenant_sweep_summary,
)
from student_app.models import WodInputDraft


class Command(BaseCommand):
    help = 'Expira rascunhos WOD vencidos e remove inativos antigos em cada box ativo.'

    def add_arguments(self, parser):
        add_tenant_sweep_arguments(parser)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--batch-size', type=int, default=500)

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        if batch_size < 1 or batch_size > 5000:
            raise CommandError('batch-size deve ficar entre 1 e 5000.')

        def run_box(box):
            result = self._cleanup_current_schema(batch_size=batch_size, dry_run=options['dry_run'])
            self.stdout.write(f'{box.schema_name}: {result}')
            return result

        sweep = sweep_active_tenants(run_box, only_schema=options['schema'])
        write_tenant_sweep_summary(self, sweep)
        if sweep.schemas_failed:
            raise CommandError(f'Falha em {sweep.schemas_failed} box(es).')

    def _cleanup_current_schema(self, *, batch_size, dry_run):
        now = timezone.now()
        expired = WodInputDraft.objects.filter(state=WodInputDraft.State.ACTIVE, expires_at__lte=now)
        stale = WodInputDraft.objects.filter(
            state__in=[WodInputDraft.State.EXPIRED, WodInputDraft.State.DISCARDED],
            updated_at__lt=now - timedelta(days=30),
        )
        if dry_run:
            return f'expirariam={expired.count()} removeriam={stale.count()}'
        expired_count = expired.update(state=WodInputDraft.State.EXPIRED)
        deleted_count = 0
        while True:
            ids = list(stale.values_list('pk', flat=True)[:batch_size])
            if not ids:
                break
            deleted, _ = WodInputDraft.objects.filter(pk__in=ids).delete()
            deleted_count += deleted
        return f'expirados={expired_count} removidos={deleted_count}'
