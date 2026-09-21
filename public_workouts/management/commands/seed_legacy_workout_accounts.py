"""
COMANDO: seed_legacy_workout_accounts

POR QUE EXISTE:
- Achado ao planejar o corte de `/renan/<slug>` para `workout.html`
  (Entrega 4, docs/plans/public-workouts-produtizacao-corda.md): os 10
  clientes legados nunca passaram pelo fluxo de checkout/login (Onda B1/B2)
  porque foram onboardados manualmente antes dele existir. Sem
  `PublicWorkoutAccount`/`PublicWorkoutSubscription`, `account_id` nunca
  resolve pra esses slugs — a aba Cargas, a revisão semanal e o registro de
  carga ficariam vazios/401 pra quem já paga, o oposto do que o corte
  deveria entregar.
- E-mail de cliente é PII. Por isso este comando NUNCA recebe e-mail
  hardcoded em código versionado — só como argumento de linha de comando,
  no momento em que roda. Não fica em nenhum arquivo do repositório.

USO:
    python manage.py seed_legacy_workout_accounts --dry-run \
        --account bruno:brunofulas@hotmail.com --account juliana:julianaalves_o@hotmail.com
    python manage.py seed_legacy_workout_accounts \
        --account bruno:brunofulas@hotmail.com

PONTOS CRÍTICOS:
- Idempotente: `get_or_create` por email (conta) e por account+plan_slug
  (assinatura) — rodar de novo com os mesmos pares nunca duplica, mesmo
  espírito de `upgrade_periodization_model`.
- `status` da assinatura fica no default do model (`ACTIVE`) — são clientes
  pagantes reais hoje, só que fora do fluxo de checkout Stripe deste
  corredor; isto não liga nenhuma cobrança nova, só identidade/sessão.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription


class Command(BaseCommand):
    help = 'Cria PublicWorkoutAccount + PublicWorkoutSubscription pros clientes legados, a partir de pares slug:email.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--account',
            action='append',
            default=[],
            dest='accounts',
            help='Par slug:email, repetir uma vez por cliente. Ex.: --account bruno:brunofulas@hotmail.com',
        )
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        pairs = []
        for raw in options['accounts']:
            if ':' not in raw:
                raise CommandError(f'Formato invalido (esperado slug:email): {raw!r}')
            slug, email = raw.split(':', 1)
            slug = slug.strip().lower()
            email = email.strip().lower()
            if not slug or not email:
                raise CommandError(f'slug/email vazio em: {raw!r}')
            pairs.append((slug, email))

        if not pairs:
            raise CommandError('Nenhum --account informado.')

        for slug, email in pairs:
            if options['dry_run']:
                self.stdout.write(f'[dry-run] criaria/confirmaria conta <-> {slug}')
                continue

            account, account_created = PublicWorkoutAccount.objects.get_or_create(email=email)
            subscription, sub_created = PublicWorkoutSubscription.objects.get_or_create(
                account=account,
                defaults={'plan_slug': slug},
            )
            self.stdout.write(self.style.SUCCESS(
                f'{slug}: conta {"criada" if account_created else "ja existia"}, '
                f'assinatura {"criada" if sub_created else "ja existia"}'
            ))
