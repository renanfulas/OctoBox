from django.core.management.base import BaseCommand, CommandError

from control.tenant_write_fence import TenantFenceTargetMissing, set_tenant_write_fence


class Command(BaseCommand):
    help = 'Ativa ou remove o fence de escrita de um box após drenar requests/jobs protegidos.'

    def add_arguments(self, parser):
        parser.add_argument('--schema', required=True, help='Schema box_<slug> do tenant.')
        action = parser.add_mutually_exclusive_group(required=True)
        action.add_argument('--freeze', action='store_true', help='Bloqueia novas operações do tenant.')
        action.add_argument('--unfreeze', action='store_true', help='Libera o tenant novamente.')
        parser.add_argument('--reason', default='', help='Motivo operacional (obrigatório em --freeze).')

    def handle(self, *args, **options):
        schema_name = options['schema']
        if options['freeze'] and not options['reason'].strip():
            raise CommandError('--reason é obrigatório ao congelar o tenant.')
        if not schema_name.startswith('box_'):
            raise CommandError('--schema deve identificar um tenant box_<slug>.')
        try:
            box, changed = set_tenant_write_fence(
                schema_name=schema_name,
                frozen=options['freeze'],
                reason=options['reason'],
            )
        except TenantFenceTargetMissing as exc:
            raise CommandError(str(exc)) from exc

        action = 'congelado' if options['freeze'] else 'liberado'
        suffix = 'estado já estava aplicado' if not changed else 'transição gravada'
        self.stdout.write(self.style.SUCCESS(f'{box.schema_name}: {action} ({suffix}).'))
        if box.write_frozen_at:
            self.stdout.write(f'freeze_at={box.write_frozen_at.isoformat()}')
            self.stdout.write(f'reason={box.write_freeze_reason}')
