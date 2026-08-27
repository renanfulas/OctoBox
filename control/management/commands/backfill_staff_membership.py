"""
ARQUIVO: management command de backfill — cria Membership para staff que só tem Group.

USO:
    python manage.py backfill_staff_membership --box=pilot
    python manage.py backfill_staff_membership --box=pilot --dry-run

SAIDA MENSURÁVEL:
    Lista quantos usuários foram migrados (ou seriam, em --dry-run) e
    imprime username + papel resolvido para cada um.

POR QUE ELE EXISTE:
    Onda 1 (correção de tenancy/autorização, 2026-08-25/26): access.roles.get_user_role
    passou a resolver papel via control.Membership antes de auth.Group. Staff
    criado ANTES dessa mudança só tem Group — sem Membership, a listagem de
    /acessos/ escopada por box (Onda 1b) não os mostra, e eles não aparecem
    como geríveis por lá (ficam invisíveis para reset de senha, edição, etc.,
    embora continuem conseguindo logar — TenantBySessionMiddleware também
    exige Membership para resolver box, então na prática staff sem Membership
    já não consegue acessar rota privada nenhuma; este comando também
    resolve ISSO, não só a visibilidade na tela de acessos).

    Escopo por --box explícito, não automático: em ambiente com mais de um
    Box, não há como inferir de qual box cada User "sem Membership" seria
    staff — o operador decide, um box por vez. Mesmo padrão de
    activate_box/unarchive_box (nunca adivinhar box a partir de dado ambíguo).
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Cria Membership para usuários staff (com Group de papel) que ainda não têm, num box.'

    def add_arguments(self, parser):
        parser.add_argument('--box', required=True, help='Slug do box a backfillar.')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Lista quem seria migrado, sem gravar nada.',
        )

    def handle(self, *args, **options):
        from access.roles import SLUG_TO_MEMBERSHIP_ROLE
        from control.models import Box, Membership

        slug = options['box']
        dry_run = options['dry_run']

        try:
            box = Box.objects.get(slug=slug)
        except Box.DoesNotExist:
            raise CommandError(f'Box com slug {slug!r} não encontrado.')

        User = get_user_model()
        already_migrated_ids = set(
            Membership.objects.filter(box=box).values_list('user_id', flat=True)
        )

        candidates = (
            User.objects.filter(groups__name__in=SLUG_TO_MEMBERSHIP_ROLE.keys())
            .exclude(pk__in=already_migrated_ids)
            .distinct()
            .prefetch_related('groups')
        )

        migrated = []
        skipped_ambiguous = []
        would_migrate_count = 0
        for user in candidates:
            group_names = set(user.groups.values_list('name', flat=True))
            matched_roles = {
                SLUG_TO_MEMBERSHIP_ROLE[name]
                for name in group_names
                if name in SLUG_TO_MEMBERSHIP_ROLE
            }
            if len(matched_roles) != 1:
                # Usuário com Groups de papel conflitantes (ex.: Manager E
                # Coach ao mesmo tempo) — não adivinha, loga pra revisão manual.
                skipped_ambiguous.append((user.username, sorted(group_names)))
                continue

            role = matched_roles.pop()
            self.stdout.write(f'  {user.username} -> {role}')
            would_migrate_count += 1
            if not dry_run:
                migrated.append(
                    Membership(user=user, box=box, role=role, is_primary_box=True)
                )

        if not dry_run and migrated:
            Membership.objects.bulk_create(migrated, ignore_conflicts=True)

        if skipped_ambiguous:
            self.stdout.write(self.style.WARNING(
                f'{len(skipped_ambiguous)} usuário(s) com papéis ambíguos (múltiplos Groups de papel), pulados:'
            ))
            for username, groups in skipped_ambiguous:
                self.stdout.write(f'    {username}: {groups}')

        verb = 'seriam migrados' if dry_run else 'migrados'
        self.stdout.write(self.style.SUCCESS(
            f'{would_migrate_count} usuário(s) {verb} para Membership em box={slug!r}.'
        ))
