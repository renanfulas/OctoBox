"""
ARQUIVO: management command para provisionar um Box.

USO:
    python manage.py provision_box --slug=pilot --owner-email=dev@octobox.local --display-name="Box Piloto"
    python manage.py provision_box --slug=pilot --owner-email=dev@octobox.local  # usa slug como display_name

SAIDA MENSURÁVEL:
    Exit 0 + mensagem "Box box_<slug> provisionado com sucesso."
    `\\dt box_<slug>.*` em psql lista 30+ tabelas.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = 'Provisiona um novo Box (cria schema + migra + bootstrap roles + seed plans).'

    def add_arguments(self, parser):
        parser.add_argument('--slug', required=True, help='Slug do box (ex.: vila-mar). Máx 59 chars.')
        parser.add_argument('--owner-email', required=True, help='E-mail do usuário que será Owner.')
        parser.add_argument('--display-name', default='', help='Nome de exibição do box. Padrão: slug.')
        parser.add_argument('--plan', default='monthly', choices=['monthly', 'annual'], help='Plano de assinatura.')
        parser.add_argument('--dry-run', action='store_true', help='Simula sem persistir nada.')

    def handle(self, *args, **options):
        from control.services import provision_box

        slug = options['slug']
        owner_email = options['owner_email']
        display_name = options['display_name'] or slug
        plan = options['plan']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY RUN] Provisionaria Box slug={slug!r} owner={owner_email!r} plan={plan}'
            ))
            return

        try:
            owner = User.objects.get(email=owner_email)
        except User.DoesNotExist:
            raise CommandError(f'Usuário com e-mail {owner_email!r} não encontrado.')

        self.stdout.write(f'Provisionando Box slug={slug!r}...')
        try:
            box = provision_box(
                owner_user=owner,
                display_name=display_name,
                slug=slug,
                plan=plan,
            )
        except Exception as exc:
            raise CommandError(f'Falha no provisioning: {exc}') from exc

        self.stdout.write(self.style.SUCCESS(
            f'Box {box.schema_name!r} provisionado com sucesso. status={box.status}'
        ))
