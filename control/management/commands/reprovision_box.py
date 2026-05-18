"""
ARQUIVO: management command para retomar provisioning de um Box com steps pendentes.

USO:
    python manage.py reprovision_box --slug=pilot

Útil quando provision_box falhou em algum step intermediário (ex.: migrate falhou por
timeout de conexão) e precisa ser retomado sem recriar o Box.

SAIDA MENSURÁVEL:
    Exit 0 se todos os steps concluem com sucesso.
    Exibe quais steps foram pulados (já ok) e quais foram executados.
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Retoma provisioning de um Box a partir do step pendente.'

    def add_arguments(self, parser):
        parser.add_argument('--slug', required=True, help='Slug do box a re-provisionar.')

    def handle(self, *args, **options):
        from control.models import Box
        from control.services import reprovision_box

        slug = options['slug']

        try:
            box = Box.objects.get(slug=slug)
        except Box.DoesNotExist:
            raise CommandError(f'Box com slug {slug!r} não encontrado.')

        if box.status == Box.Status.ARCHIVED:
            raise CommandError(f'Box {slug!r} está ARCHIVED. Não é possível re-provisionar.')

        self.stdout.write(f'Retomando provisioning de {slug!r} (status={box.status})...')
        try:
            box = reprovision_box(box)
        except Exception as exc:
            raise CommandError(f'Falha no reprovision: {exc}') from exc

        self.stdout.write(self.style.SUCCESS(
            f'Box {slug!r} provisionado com sucesso. status={box.status}'
        ))
