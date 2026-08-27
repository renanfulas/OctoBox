"""
ARQUIVO: comando que dispara os lembretes de check-in de parceiro (cron).

POR QUE ELE EXISTE:
- Liga finance/partner_checkin_reminders.py a um cron rodando a cada ~10min.
  Cada execucao so envia o lembrete cuja janela (0/10/30min apos a aula) ja
  chegou; alunos ja lembrados na mesma janela nao recebem duplicata.
"""

from django.core.management.base import BaseCommand

from finance.partner_checkin_reminders import send_due_partner_checkin_reminders


class Command(BaseCommand):
    help = 'Envia lembretes de confirmacao de check-in Wellhub/TotalPass (0/10/30min apos o horario da aula).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=200,
            help='Limite de PartnerCheckInCharge verificados por box.',
        )

    def handle(self, *args, **options):
        report = send_due_partner_checkin_reminders(limit=options['limit'])

        self.stdout.write(
            self.style.SUCCESS(
                f"Lembretes de check-in de parceiro: {report['checked']} verificados, "
                f"{report['sent']} enviados."
            )
        )
        for entry in report['reminders']:
            self.stdout.write(
                f"  lembrete box={entry['box']} charge={entry['charge_id']} "
                f"tentativa={entry['attempt']} canal={entry['channel']}"
            )
