"""
ARQUIVO: backfill — anexa o superdev aos boxes ACTIVE ja existentes.

POR QUE ELE EXISTE:
- _attach_support_membership roda no provisionamento de boxes NOVOS. Boxes criados
  antes desta feature (ou antes da conta superdev existir) precisam de backfill para
  o "sempre com o superdev" valer para todos.

O QUE ESTE ARQUIVO FAZ:
1. Itera boxes ACTIVE.
2. Aplica control.services._attach_support_membership (idempotente).
3. --dry-run apenas relata o que faria, sem gravar.

USO:
    python manage.py attach_superdev_to_boxes
    python manage.py attach_superdev_to_boxes --dry-run
"""

from django.core.management.base import BaseCommand

from control.models import Box, Membership
from control.services import _attach_support_membership, get_superdev_user


class Command(BaseCommand):
    help = 'Anexa a conta de suporte (superdev) aos boxes ACTIVE existentes (idempotente).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Apenas relata, nao grava.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        superdev = get_superdev_user()
        if superdev is None:
            self.stderr.write(
                'Superdev indisponivel (conta ausente/inativa ou SUPERDEV_AUTO_ATTACH=False). '
                'Rode `bootstrap_superdev` e confira as settings.'
            )
            return

        boxes = Box.objects.filter(status=Box.Status.ACTIVE).order_by('slug')
        attached = 0
        already = 0
        for box in boxes:
            if Membership.objects.filter(user=superdev, box=box).exists():
                already += 1
                continue
            if dry_run:
                self.stdout.write(f'[dry-run] anexaria superdev a {box.slug}')
                attached += 1
                continue
            _attach_support_membership(box)
            if Membership.objects.filter(user=superdev, box=box).exists():
                attached += 1
                self.stdout.write(self.style.SUCCESS(f'anexado: {box.slug}'))
            else:
                self.stderr.write(f'FALHOU ao anexar: {box.slug} (ver logs)')

        verb = 'anexaria(m)' if dry_run else 'anexado(s)'
        self.stdout.write(self.style.SUCCESS(
            f'Concluido. {attached} {verb}, {already} ja tinha(m) superdev. Total ACTIVE: {boxes.count()}.'
        ))
