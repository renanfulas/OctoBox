"""
ARQUIVO: management command para restaurar um Box arquivado.

USO:
    python manage.py unarchive_box --slug=pilot
    python manage.py unarchive_box --slug=pilot --reason="Cliente voltou" --confirm

SAIDA MENSURÁVEL:
    Exit 0 + mensagem "Box <slug> restaurado como box_<slug> (status SUSPENDED)."
    Box.status = SUSPENDED. Schema renomeado de volta.

POR QUE SUSPENDED E NÃO ACTIVE:
    Restaurar os dados e liberar o acesso são duas decisões diferentes. Este
    comando faz só a primeira. O acesso volta pelo caminho normal de billing
    (invoice.payment_succeeded → ACTIVE), para não existir atalho que devolva
    box ativo sem assinatura viva.
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Restaura um Box ARCHIVED (schema volta a box_<slug>, status SUSPENDED).'

    def add_arguments(self, parser):
        parser.add_argument('--slug', required=True, help='Slug do box a restaurar.')
        parser.add_argument('--reason', default='', help='Motivo (para PlatformAuditEvent).')
        parser.add_argument('--confirm', action='store_true', help='Confirmar sem prompt interativo.')

    def handle(self, *args, **options):
        from control.models import Box
        from control.services import unarchive_box

        slug = options['slug']
        reason = options['reason']
        confirm = options['confirm']

        try:
            box = Box.objects.get(slug=slug)
        except Box.DoesNotExist:
            raise CommandError(f'Box com slug {slug!r} não encontrado.')

        if box.status != Box.Status.ARCHIVED:
            raise CommandError(
                f'Box {slug!r} está {box.status!r}, não ARCHIVED. Nada a restaurar.'
            )

        destino = f'box_{box.slug}'
        if not confirm:
            self.stdout.write(self.style.WARNING(
                f'Este comando renomeará o schema {box.schema_name!r} de volta para {destino!r}.'
            ))
            self.stdout.write(
                'O Box ficará SUSPENDED — o acesso só volta quando um pagamento for confirmado.'
            )
            answer = input('Confirmar restauração? (sim/não): ').strip().lower()
            if answer not in ('sim', 's', 'yes', 'y'):
                self.stdout.write('Operação cancelada.')
                return

        self.stdout.write(f'Restaurando Box {slug!r}...')
        try:
            box = unarchive_box(box, reason=reason)
        except ValueError as exc:
            # ValueError aqui é sempre guarda de segurança do serviço (schema
            # destino já existe, schema origem sumiu, status errado), não bug.
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            raise CommandError(f'Falha na restauração: {exc}') from exc

        self.stdout.write(self.style.SUCCESS(
            f'Box {slug!r} restaurado como {box.schema_name!r} (status {box.status}).'
        ))
        self.stdout.write(
            'Acesso continua bloqueado até invoice.payment_succeeded reativar o box.'
        )
