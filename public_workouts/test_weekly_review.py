"""
ARQUIVO: testes de build_weekly_review (Onda A3 do CORDA —
docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- build_weekly_review so agrega os SINAIS ja calculados (tendencia de
  1RM) — nunca chama IA nem le check-in/anamnese (nenhum dos dois tem
  coleta ainda). Os testes provam esse limite: o dict devolvido e so
  sinal, nunca texto gerado.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoadLog, PublicWorkoutLoadLogSetRole
from public_workouts.services import build_weekly_review


def _make_account(email='atleta@example.com') -> PublicWorkoutAccount:
    return PublicWorkoutAccount.objects.create(email=email)


def _log(account, *, movement_slug, weight_kg, reps, performed_on):
    return PublicWorkoutLoadLog.objects.create(
        account=account,
        movement_slug=movement_slug,
        weight_kg=Decimal(str(weight_kg)),
        reps=reps,
        performed_on=performed_on,
        idempotency_key=f'{movement_slug}-{performed_on.isoformat()}-{weight_kg}',
        set_role=PublicWorkoutLoadLogSetRole.TOP_SET,
    )


class BuildWeeklyReviewTests(TestCase):
    def test_empty_when_no_load_logged_yet(self):
        account = _make_account()

        review = build_weekly_review(account_id=account.pk, as_of=date(2026, 1, 19))

        self.assertEqual(review, {'trends_by_movement': {}, 'declining_movements': [], 'plateaued_movements': []})

    def test_movement_with_insufficient_data_is_left_out(self):
        # So 1 semana de registro -- detect_one_rep_max_trend devolve
        # insufficient_data, que build_weekly_review nao inclui no sinal
        # (nao e um sinal ainda, e ausencia de sinal).
        account = _make_account()
        _log(account, movement_slug='agachamento-livre', weight_kg=100, reps=5, performed_on=date(2026, 1, 5))

        review = build_weekly_review(account_id=account.pk, as_of=date(2026, 1, 19))

        self.assertEqual(review['trends_by_movement'], {})

    def test_declining_movement_is_flagged(self):
        account = _make_account()
        for week_offset, weight in ((0, 110), (7, 108), (14, 95)):
            _log(
                account,
                movement_slug='agachamento-livre',
                weight_kg=weight,
                reps=5,
                performed_on=date(2026, 1, 5) + timedelta(days=week_offset),
            )

        review = build_weekly_review(account_id=account.pk, as_of=date(2026, 1, 19))

        self.assertEqual(review['declining_movements'], ['agachamento-livre'])
        self.assertEqual(review['plateaued_movements'], [])
        self.assertEqual(review['trends_by_movement']['agachamento-livre']['label'], 'declining')

    def test_plateaued_movement_is_flagged(self):
        account = _make_account()
        for week_offset in (0, 7, 14):
            _log(
                account,
                movement_slug='supino-reto',
                weight_kg=60,
                reps=5,
                performed_on=date(2026, 1, 5) + timedelta(days=week_offset),
            )

        review = build_weekly_review(account_id=account.pk, as_of=date(2026, 1, 19))

        self.assertEqual(review['plateaued_movements'], ['supino-reto'])
        self.assertEqual(review['declining_movements'], [])

    def test_improving_movement_appears_in_trends_but_not_in_either_flag_list(self):
        account = _make_account()
        for week_offset, weight in ((0, 90), (7, 100), (14, 112)):
            _log(
                account,
                movement_slug='agachamento-livre',
                weight_kg=weight,
                reps=5,
                performed_on=date(2026, 1, 5) + timedelta(days=week_offset),
            )

        review = build_weekly_review(account_id=account.pk, as_of=date(2026, 1, 19))

        self.assertEqual(review['trends_by_movement']['agachamento-livre']['label'], 'improving')
        self.assertEqual(review['declining_movements'], [])
        self.assertEqual(review['plateaued_movements'], [])

    def test_covers_every_movement_the_account_has_logged(self):
        account = _make_account()
        for week_offset in (0, 7, 14):
            _log(
                account,
                movement_slug='agachamento-livre',
                weight_kg=100,
                reps=5,
                performed_on=date(2026, 1, 5) + timedelta(days=week_offset),
            )
            _log(
                account,
                movement_slug='supino-reto',
                weight_kg=60,
                reps=5,
                performed_on=date(2026, 1, 5) + timedelta(days=week_offset),
            )

        review = build_weekly_review(account_id=account.pk, as_of=date(2026, 1, 19))

        self.assertEqual(set(review['trends_by_movement']), {'agachamento-livre', 'supino-reto'})

    def test_does_not_leak_between_accounts(self):
        account_a = _make_account(email='a@example.com')
        account_b = _make_account(email='b@example.com')
        for week_offset in (0, 7, 14):
            _log(
                account_a,
                movement_slug='agachamento-livre',
                weight_kg=100,
                reps=5,
                performed_on=date(2026, 1, 5) + timedelta(days=week_offset),
            )

        review_b = build_weekly_review(account_id=account_b.pk, as_of=date(2026, 1, 19))

        self.assertEqual(review_b['trends_by_movement'], {})

    def test_never_calls_an_ai_provider(self):
        # Guardrail de escopo: build_weekly_review e so a parte
        # deterministica (D4 do plano) -- nunca deve importar stripe,
        # anthropic ou qualquer cliente de IA. Checagem estatica igual
        # ao teste de fronteira tenant/public deste app.
        import ast
        import pathlib

        source = pathlib.Path('public_workouts/services.py').read_text(encoding='utf-8')
        tree = ast.parse(source, filename='public_workouts/services.py')
        forbidden_prefixes = ('anthropic', 'openai')
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(forbidden_prefixes):
                offenders.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(forbidden_prefixes):
                        offenders.append(alias.name)

        self.assertEqual(offenders, [])
