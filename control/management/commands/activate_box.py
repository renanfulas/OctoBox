"""
ARQUIVO: management command para reativar manualmente um Box SUSPENDED.

USO:
    python manage.py activate_box --slug=pilot --reason="Cliente pagou por fora, confirmado com financeiro"

SAIDA MENSURÁVEL:
    Exit 0 + mensagem "Box <slug> reativado (status ACTIVE)."
    Box.status = ACTIVE. PlatformAuditEvent kind=box.activated_manual_support gravado.

POR QUE ELE EXISTE:
    Onda 2 fechou reprovision_box promovendo SUSPENDED->ACTIVE sem checar
    billing (era o mesmo furo que unarchive_box já fecha do lado do
    archive). Fechar essa porta sem abrir um caminho auditado transformaria
    o primeiro chamado de suporte em UPDATE manual direto no banco de
    produção. Este comando é esse caminho — com --reason obrigatório e
    trilha em PlatformAuditEvent.

    NÃO usar para reverter suspensão por ARCHIVED (usar unarchive_box) nem
    para promover um box em PROVISIONING (reprovision_box resolve sozinho).
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Reativa manualmente um Box SUSPENDED (status ACTIVE), com motivo obrigatório e audit.'

    def add_arguments(self, parser):
        parser.add_argument('--slug', required=True, help='Slug do box a reativar.')
        parser.add_argument('--reason', required=True, help='Motivo da reativação manual (obrigatório).')
        parser.add_argument('--confirm', action='store_true', help='Confirmar operação sem prompt interativo.')

    def handle(self, *args, **options):
        from control.models import Box
        from control.services import activate_box

        slug = options['slug']
        reason = options['reason']
        confirm = options['confirm']

        try:
            box = Box.objects.get(slug=slug)
        except Box.DoesNotExist:
            raise CommandError(f'Box com slug {slug!r} não encontrado.')

        if box.status != Box.Status.SUSPENDED:
            raise CommandError(
                f'Box {slug!r} está {box.status!r}, não SUSPENDED. '
                f'ARCHIVED: use unarchive_box. PROVISIONING: use reprovision_box.'
            )

        if not confirm:
            self.stdout.write(self.style.WARNING(
                f'ATENÇÃO: Este comando reativará o Box {slug!r} SEM confirmação de pagamento.'
            ))
            self.stdout.write(f'Motivo registrado: {reason!r}')
            self.stdout.write('Use --confirm para prosseguir sem prompt, ou confirme abaixo.')
            answer = input('Confirmar reativação manual? (sim/não): ').strip().lower()
            if answer not in ('sim', 's', 'yes', 'y'):
                self.stdout.write('Operação cancelada.')
                return

        self.stdout.write(f'Reativando Box {slug!r}...')
        try:
            box = activate_box(box, reason=reason)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            raise CommandError(f'Falha na reativação: {exc}') from exc

        self.stdout.write(self.style.SUCCESS(
            f'Box {slug!r} reativado (status {box.status}).'
        ))
