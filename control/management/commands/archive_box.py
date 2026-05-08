"""
ARQUIVO: management command para arquivar um Box.

USO:
    python manage.py archive_box --slug=pilot
    python manage.py archive_box --slug=pilot --reason="Offboarding cliente X"

SAIDA MENSURÁVEL:
    Exit 0 + mensagem "Box box_<slug> arquivado como archived_box_<slug>_<ts>."
    Box.status = ARCHIVED. Schema renomeado.

AVISO: operação irreversível via código. Reversão manual via SQL se necessário.
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Arquiva um Box (status ARCHIVED + rename schema para archived_box_<slug>_<ts>).'

    def add_arguments(self, parser):
        parser.add_argument('--slug', required=True, help='Slug do box a arquivar.')
        parser.add_argument('--reason', default='', help='Motivo do arquivamento (para PlatformAuditEvent).')
        parser.add_argument('--confirm', action='store_true', help='Confirmar operação sem prompt interativo.')

    def handle(self, *args, **options):
        from control.models import Box
        from control.services import archive_box

        slug = options['slug']
        reason = options['reason']
        confirm = options['confirm']

        try:
            box = Box.objects.get(slug=slug)
        except Box.DoesNotExist:
            raise CommandError(f'Box com slug {slug!r} não encontrado.')

        if box.status == Box.Status.ARCHIVED:
            self.stdout.write(self.style.WARNING(f'Box {slug!r} já está ARCHIVED.'))
            return

        if not confirm:
            self.stdout.write(self.style.WARNING(
                f'ATENÇÃO: Este comando arquivará o Box {slug!r} (schema: {box.schema_name}).'
            ))
            self.stdout.write('Use --confirm para prosseguir sem prompt, ou confirme abaixo.')
            answer = input('Confirmar archiving? (sim/não): ').strip().lower()
            if answer not in ('sim', 's', 'yes', 'y'):
                self.stdout.write('Operação cancelada.')
                return

        self.stdout.write(f'Arquivando Box {slug!r}...')
        try:
            box = archive_box(box, reason=reason)
        except Exception as exc:
            raise CommandError(f'Falha no archiving: {exc}') from exc

        self.stdout.write(self.style.SUCCESS(
            f'Box {slug!r} arquivado como {box.schema_name!r}.'
        ))
