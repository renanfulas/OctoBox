"""
COMANDO: seed_legacy_payment_schedule

POR QUE EXISTE:
- O gate de acesso por pagamento (billing.py + PublicWorkoutDetailView)
  so' bloqueia quando EXISTE uma PublicWorkoutSubscription pro slug E ela
  nao esta ACTIVE. Os 10 clientes legados (seed_legacy_workout_accounts.py)
  nunca passaram pelo checkout Stripe deste corredor — pagam o Renan por
  fora — e por isso nunca tiveram nenhum PublicWorkoutPayment criado. Sem
  um ciclo de cobranca registrado, a regua de avisos + suspensao
  automatica em D+2 (drain_due_notices, ja rodando de verdade num
  systemd timer) nunca tem o que avaliar pra eles: PENDING_PAYMENT
  nunca acontece sozinho se ninguem primeiro disser QUANDO cada um
  vence.
- Este comando cria esse primeiro (ou proximo) ciclo de cobranca +
  regua de 5 avisos pra cada cliente legado, de forma explicita e
  auditavel — nunca adivinha data nem valor.
- Mesma disciplina de PII de seed_legacy_workout_accounts.py: nada de
  slug/data/valor fica hardcoded em codigo versionado, so' como
  argumento de linha de comando, no momento em que roda.

USO:
    python manage.py seed_legacy_payment_schedule --dry-run \
        --payment bruno:2026-10-05:97.00 --payment juliana:2026-10-20:97.00
    python manage.py seed_legacy_payment_schedule \
        --payment bruno:2026-10-05:97.00

PONTOS CRITICOS:
- So' funciona pra slug que JA tem PublicWorkoutSubscription (criada por
  seed_legacy_workout_accounts.py) — sem isso, CommandError explicito,
  nunca cria assinatura nova aqui (fora de escopo deste comando).
- Idempotente por (subscription, due_date): rodar de novo com o mesmo
  par slug+data nao duplica, so' avisa e pula.
- Valor validado pela mesma faixa de billing.py::validate_payment_amount
  (P8 do CORDA) — nunca grava cobranca fora da faixa aceita "pra
  corrigir depois".
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from public_workouts.billing import PublicWorkoutPaymentAmountError, create_payment_with_notice_schedule
from public_workouts.models import PublicWorkoutPayment, PublicWorkoutSubscription


class Command(BaseCommand):
    help = (
        'Cria o proximo PublicWorkoutPayment + regua de 5 avisos pros clientes legados, '
        'a partir de trincas slug:data:valor.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--payment',
            action='append',
            default=[],
            dest='payments',
            help='Trinca slug:AAAA-MM-DD:valor, repetir uma vez por cliente. Ex.: --payment bruno:2026-10-05:97.00',
        )
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        triples = []
        for raw in options['payments']:
            parts = raw.split(':')
            if len(parts) != 3:
                raise CommandError(f'Formato invalido (esperado slug:AAAA-MM-DD:valor): {raw!r}')
            slug, raw_date, raw_amount = (p.strip() for p in parts)
            if not slug:
                raise CommandError(f'slug vazio em: {raw!r}')
            try:
                due_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
            except ValueError as exc:
                raise CommandError(f'data invalida (esperado AAAA-MM-DD) em: {raw!r}') from exc
            try:
                gross_amount = Decimal(raw_amount)
            except InvalidOperation as exc:
                raise CommandError(f'valor invalido em: {raw!r}') from exc
            triples.append((slug.lower(), due_date, gross_amount))

        if not triples:
            raise CommandError('Nenhum --payment informado.')

        for slug, due_date, gross_amount in triples:
            if options['dry_run']:
                self.stdout.write(f'[dry-run] criaria cobranca de {gross_amount} pra {slug}, vencimento {due_date}')
                continue

            subscription = PublicWorkoutSubscription.objects.filter(plan_slug=slug).first()
            if subscription is None:
                raise CommandError(
                    f'{slug}: nenhuma PublicWorkoutSubscription encontrada — '
                    'rode seed_legacy_workout_accounts primeiro.'
                )

            existing = PublicWorkoutPayment.objects.filter(subscription=subscription, due_date=due_date).first()
            if existing is not None:
                self.stdout.write(self.style.WARNING(f'{slug}: ja existe cobranca com vencimento {due_date}, pulando.'))
                continue

            try:
                create_payment_with_notice_schedule(
                    subscription=subscription, due_date=due_date, gross_amount=gross_amount
                )
            except PublicWorkoutPaymentAmountError as exc:
                raise CommandError(f'{slug}: {exc}') from exc

            self.stdout.write(self.style.SUCCESS(f'{slug}: cobranca de {gross_amount} criada, vencimento {due_date}'))
