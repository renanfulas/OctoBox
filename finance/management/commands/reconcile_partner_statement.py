"""
ARQUIVO: comando de reconciliacao do extrato Wellhub/TotalPass (manual, v1).

POR QUE ELE EXISTE:
- Enquanto nao existe integracao via API com Wellhub/TotalPass, o dono baixa o
  extrato do painel deles e importa aqui como CSV. Isso ja fecha o ciclo:
  presenca interna so vira receita reconhecida quando bate com o extrato
  oficial. Quando a API existir, o consumidor muda (webhook/pull), mas
  finance/reconciliation.py::reconcile_partner_statement fica igual.

FORMATO DO CSV (cabecalho obrigatorio): student_phone,date,value
  student_phone: mesmo numero cadastrado no Student (com DDI/DDD).
  date: YYYY-MM-DD (data da aula no extrato do parceiro).
  value: valor declarado pelo parceiro para aquele check-in.
"""

import csv

from django.core.management.base import BaseCommand, CommandError

from finance.model_definitions import PaymentSource
from finance.reconciliation import flag_stale_partner_checkins, reconcile_partner_statement


class Command(BaseCommand):
    help = 'Importa o extrato manual da Wellhub/TotalPass (CSV) e reconcilia com o ledger interno.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', help='Caminho do CSV do extrato (student_phone,date,value).')
        parser.add_argument(
            '--partner',
            choices=[PaymentSource.WELLHUB, PaymentSource.TOTALPASS],
            required=True,
        )
        parser.add_argument('--reference', default='', help='Identificador do extrato (ex.: competencia AAAA-MM).')
        parser.add_argument(
            '--stale-days',
            type=int,
            default=3,
            help='Apos reconciliar, marca como disputed check-ins mais velhos que N dias sem confirmacao.',
        )

    def handle(self, *args, **options):
        try:
            with open(options['csv_path'], newline='', encoding='utf-8') as fh:
                rows = list(csv.DictReader(fh))
        except OSError as exc:
            raise CommandError(f"Nao consegui ler {options['csv_path']}: {exc}") from exc

        report = reconcile_partner_statement(
            partner=options['partner'],
            rows=rows,
            statement_reference=options['reference'],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Extrato {options['partner']}: {report['matched']} reconciliados, "
                f"{report['orphan_count']} sem correspondencia interna."
            )
        )
        for orphan in report['orphans']:
            self.stdout.write(
                self.style.WARNING(
                    f"  extrato sem match box={orphan['box']} phone={orphan['phone']} date={orphan['date']}"
                )
            )

        stale_report = flag_stale_partner_checkins(older_than_days=options['stale_days'])
        if stale_report['flagged_count']:
            self.stdout.write(
                self.style.WARNING(
                    f"Check-ins sem confirmacao nem reconciliacao (>{options['stale_days']}d): "
                    f"{stale_report['flagged_count']} marcados como disputed."
                )
            )
