"""Remove apenas prévias diárias vencidas; recibos confirmados são duráveis."""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from shared_support.tenant_sweep import (
    add_tenant_sweep_arguments, sweep_active_tenants, write_tenant_sweep_summary,
)
from student_app.models import WodApplyIntent


class Command(BaseCommand):
    help = 'Remove intenções diárias não confirmadas cuja prévia expirou.'

    def add_arguments(self, parser):
        add_tenant_sweep_arguments(parser)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--batch-size', type=int, default=500)

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        if batch_size < 1 or batch_size > 5000:
            raise CommandError('batch-size deve ficar entre 1 e 5000.')

        def run_box(box):
            expired = WodApplyIntent.objects.filter(
                state=WodApplyIntent.State.PREPARED,
                expires_at__lt=timezone.now(),
            )
            if options['dry_run']:
                result = f'removeriam={expired.count()}'
            else:
                deleted_count = 0
                while True:
                    ids = list(expired.values_list('pk', flat=True)[:batch_size])
                    if not ids:
                        break
                    deleted, _ = WodApplyIntent.objects.filter(
                        pk__in=ids, state=WodApplyIntent.State.PREPARED,
                    ).delete()
                    deleted_count += deleted
                result = f'removidos={deleted_count}'
            self.stdout.write(f'{box.schema_name}: {result}')
            return result

        sweep = sweep_active_tenants(run_box, only_schema=options['schema'])
        write_tenant_sweep_summary(self, sweep)
        if sweep.schemas_failed:
            raise CommandError(f'Falha em {sweep.schemas_failed} box(es).')
