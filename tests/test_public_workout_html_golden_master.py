"""
ARQUIVO: golden master do HTML de /renan/<slug> (Fase 0 do split dos arquivos grandes).

POR QUE ELE EXISTE:
- docs/plans/split-arquivos-grandes-plano.md, Fase 0, item 2. As fases 1, 2 e 6
  (templatetags, views da Curva e workout.html) so movem codigo; este teste e a
  "foto" que prova que a pagina que o aluno ve continua identica depois de cada
  uma delas.

O QUE ESTE ARQUIVO FAZ:
1. Monta 4 alunos de fixture pelos services de verdade (publish_program,
   record_load, correct_load, start_session/record_set), com data congelada.
2. Faz GET em /renan/<slug> como o navegador do aluno faz.
3. Normaliza o HTML (versao de asset, token CSRF, UUID, indentacao) e compara
   com tests/golden/public_workout_html/<caso>.html.

COMO ATUALIZAR (so para mudanca INTENCIONAL de HTML, fora dos PRs de split):
    OCTOBOX_UPDATE_GOLDEN=1 pytest tests/test_public_workout_html_golden_master.py --create-db --migrations
  e revise no PR o diff dos arquivos em tests/golden/public_workout_html/.
  Num PR de split, NUNCA atualize: diferenca aqui significa que o split mudou
  comportamento.

PONTOS CRITICOS:
- Slugs e movimentos usam o prefixo `gm-` e um movement_pattern proprio para
  nao depender de catalogo semeado por migracao nem dos 10 clientes legados de
  PUBLIC_WORKOUT_LIBRARY (slug fora do dict cai em _synthesize_public_workout_plan).
- Contas com pk explicito: `data-account-scope` vira o id da conta no HTML e a
  sequence do Postgres varia com a ordem da suite (-n 4, pytest-randomly).
- Settings que mudam o HTML por ambiente (versao de asset por mtime, VAPID,
  kill switch de template legado) ficam fixados em override_settings.
- DESCARTAVEL: sai junto com o fim da Fase 6 do plano; a trava de tamanho fica.
"""

from __future__ import annotations

import difflib
import os
import re
from decimal import Decimal
from pathlib import Path

from django.test import TestCase, override_settings
from freezegun import freeze_time

from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutLoadLogSetRole,
    PublicWorkoutMovement,
    PublicWorkoutMovementEquipment,
    PublicWorkoutMovementModality,
    PublicWorkoutMovementStatus,
    PublicWorkoutProgram,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
)
from public_workouts.services import correct_load, publish_program, record_load
from public_workouts.testing import sign_in_public_workout_account
from public_workouts.training_sessions import day_plan, record_set, start_session


GOLDEN_DIR = Path(__file__).resolve().parent / 'golden' / 'public_workout_html'
UPDATE_ENV_VAR = 'OCTOBOX_UPDATE_GOLDEN'

# 13:30 UTC = 10:30 de uma quarta-feira em America/Sao_Paulo, semana 5 do
# programa (started_on 2026-01-05): periodizacao, "hoje" e saudacao fixos.
FROZEN_NOW = '2026-02-04 13:30:00'
TODAY = '2026-02-04'

_MOVEMENTS = (
    # slug, label_pt, movement_pattern, status, equipment_type, logged_weight_includes_bar
    ('gm-agachamento-livre', 'Agachamento livre GM', 'gm-golden-squat',
     PublicWorkoutMovementStatus.ACTIVE, PublicWorkoutMovementEquipment.BARBELL, True),
    ('gm-agachamento-smith', 'Agachamento no Smith GM', 'gm-golden-squat',
     PublicWorkoutMovementStatus.ACTIVE, PublicWorkoutMovementEquipment.MACHINE, False),
    ('gm-leg-press', 'Leg press 45 GM', 'gm-golden-squat',
     PublicWorkoutMovementStatus.ACTIVE, PublicWorkoutMovementEquipment.MACHINE, False),
    ('gm-supino-reto', 'Supino reto GM', 'gm-golden-push',
     PublicWorkoutMovementStatus.ACTIVE, PublicWorkoutMovementEquipment.BARBELL, True),
    ('gm-remada-curvada', 'Remada curvada GM', 'gm-golden-pull',
     PublicWorkoutMovementStatus.ACTIVE, PublicWorkoutMovementEquipment.DUMBBELL, False),
    ('gm-prancha', 'Prancha GM', '',
     PublicWorkoutMovementStatus.PENDING, PublicWorkoutMovementEquipment.OTHER, False),
)


def _movement(slug, reps_spec, *, rir_spec='', load_type='free', load_value=None, **extra):
    movement = {
        'movement_slug': slug,
        'reps_spec': reps_spec,
        'rir_spec': rir_spec,
        'is_tracked': True,
        'load_type': load_type,
        'load_value': load_value,
        'reference_url': None,
    }
    movement.update(extra)
    return movement


def _payload(*, program_id='gm-programa', label='Programa golden', periodization=False, cardio=False):
    payload = {
        'schema_version': 1,
        'program_id': program_id,
        'program_label': label,
        'started_on': '2026-01-05',
        'weeks': 6,
        'accent_variant': None,
        'days': [
            {
                'day_id': 'seg',
                'label': 'Segunda',
                'display_title': 'Inferiores',
                'focus_description': 'Quadriceps e posterior de coxa',
                'blocks': [
                    {'movements': [
                        _movement(
                            'gm-agachamento-livre', '2× Prep → 1× Feeder → 2× Top (6-8)',
                            rir_spec='RIR 1-2', load_type='percentage_of_rm', load_value=75.0,
                            name='Agachamento livre',
                            reference_url='https://example.test/agachamento',
                            variations=[{'label': 'No Smith', 'reference_url': 'https://example.test/smith'}],
                        ),
                        _movement(
                            'gm-leg-press', '3× Top (10-12)', rir_spec='RIR 2', load_type='fixed_kg', load_value=120,
                        ),
                    ]},
                ],
            },
            {
                'day_id': 'qua',
                'label': 'Quarta',
                'display_title': 'Superiores',
                'blocks': [
                    {'movements': [
                        _movement('gm-supino-reto', '2x8 aquecimento + 1x6-8 Top', rir_spec='RIR 1'),
                        _movement('gm-remada-curvada', '3× Top (8-10)', rir_spec='RIR 2'),
                    ]},
                    {'movements': [
                        _movement('gm-prancha', 'texto aberto', allow_load_registration=False, is_tracked=False),
                    ]},
                ],
            },
        ],
    }
    if periodization:
        payload['periodization'] = {
            'weeks': [
                {'week_number': 1, 'phase_type': 'adaptation', 'note': 'Tecnica primeiro'},
                {'week_number': 2, 'phase_type': 'volume'},
                {'week_number': 3, 'phase_type': 'strength_hypertrophy'},
                {'week_number': 4, 'phase_type': 'intensity'},
                {'week_number': 5, 'phase_type': 'peak'},
                {'week_number': 6, 'phase_type': 'deload'},
            ],
            'volume_table': [
                {'muscle_group': 'Quadriceps', 'sets_per_week': '10', 'frequency': '2x', 'where': 'Seg e Qui'},
                {'muscle_group': 'Peitoral', 'sets_per_week': '8', 'frequency': '1x', 'where': 'Qua'},
            ],
            'note': 'Mesociclo de 6 semanas com deload no fim.',
        }
    if cardio:
        payload['cardio'] = {
            'sessions': [
                {
                    'title': 'Caminhada inclinada',
                    'badge': 'Zona 2',
                    'note': 'Depois do treino de pernas',
                    'details': [{'label': 'Duracao', 'value': '30 min'}],
                },
            ],
        }
    return payload


def _create_catalog():
    for slug, label, pattern, status, equipment, includes_bar in _MOVEMENTS:
        PublicWorkoutMovement.objects.create(
            slug=slug,
            label_pt=label,
            modality=PublicWorkoutMovementModality.STRENGTH,
            movement_pattern=pattern,
            status=status,
            equipment_type=equipment,
            logged_weight_includes_bar=includes_bar,
        )


def _create_student(*, pk, slug, tier=PublicWorkoutTier.ESSENCIAL,
                    status=PublicWorkoutSubscriptionStatus.ACTIVE, onboarded=True, **subscription_fields):
    account = PublicWorkoutAccount.objects.create(
        pk=pk,
        email=f'{slug}@golden.example.test',
        onboarding_completed_at='2026-01-06T12:00:00Z' if onboarded else None,
    )
    PublicWorkoutSubscription.objects.create(
        account=account, plan_slug=slug, tier=tier, status=status, **subscription_fields,
    )
    return account


def _record_history(account):
    """Cinco semanas de carga em dois movimentos: progressao, recorde,
    aquecimento, uma correcao (registro errado fica inativo) e carga de hoje."""
    history = (
        ('gm-agachamento-livre', '2026-01-07', '80', 8, '2', PublicWorkoutLoadLogSetRole.TOP_SET),
        ('gm-agachamento-livre', '2026-01-14', '82.5', 8, '2', PublicWorkoutLoadLogSetRole.TOP_SET),
        ('gm-agachamento-livre', '2026-01-21', '85', 7, '1', PublicWorkoutLoadLogSetRole.TOP_SET),
        ('gm-agachamento-livre', '2026-01-28', '87.5', 6, '1', PublicWorkoutLoadLogSetRole.TOP_SET),
        ('gm-agachamento-livre', '2026-01-28', '60', 10, None, PublicWorkoutLoadLogSetRole.WARMUP),
        ('gm-supino-reto', '2026-01-07', '60', 8, '2', PublicWorkoutLoadLogSetRole.TOP_SET),
        ('gm-supino-reto', '2026-01-21', '62.5', 8, '1', PublicWorkoutLoadLogSetRole.TOP_SET),
        ('gm-supino-reto', TODAY, '165', 6, '1', PublicWorkoutLoadLogSetRole.TOP_SET),
        ('gm-supino-reto', TODAY, '40', 8, None, PublicWorkoutLoadLogSetRole.WARMUP),
    )
    for index, (slug, performed_on, weight, reps, rir, role) in enumerate(history):
        record_load(
            account_id=account.pk, movement_slug=slug, weight_kg=Decimal(weight), reps=reps,
            rir=Decimal(rir) if rir is not None else None, performed_on=performed_on,
            program_id='gm-programa', set_role=role, idempotency_key=f'gm-carga-{index}',
        )
    # 165 foi digitado por engano de 65: a correcao desativa o registro errado.
    correct_load(
        account_id=account.pk, supersedes_idempotency_key='gm-carga-7',
        idempotency_key='gm-carga-7-correcao', weight_kg=Decimal('65'), reps=6, rir=Decimal('1'),
    )


def _record_guided_top_set(account, *, slug, day_id):
    session = start_session(account_id=account.pk, plan_slug=slug, day_id=day_id, start_key='gm-inicio')
    program = PublicWorkoutProgram.objects.get(slug=slug, is_active=True)
    for movement_index, movement in enumerate(day_plan(program, day_id)):
        for set_number, series in enumerate(movement['series'], start=1):
            if series['role'] != 'top_set':
                continue
            record_set(
                account_id=account.pk, plan_slug=slug, session_id=session.pk,
                movement_index=movement_index, set_number=set_number,
                movement_slug=movement['slug'], role='top_set',
                weight=Decimal('70'), reps=series['reps'] or 8, rir=Decimal('2'),
            )
            return session
    raise AssertionError('fixture do guiado sem serie top_set')


_UUID_RE = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)
_ASSET_VERSION_RE = re.compile(r'([?&]v=)[^"\'&\s<>]+')
_CSRF_PATTERNS = (
    re.compile(r'(name="csrfmiddlewaretoken" value=")[^"]*(")'),
    re.compile(r'(name="csrf-token" content=")[^"]*(")'),
    re.compile(r'(data-csrf-token=")[^"]*(")'),
)


def normalize_html(html: str, *, csrf_token: str | None = None) -> str:
    """Tira do HTML o que muda sem o comportamento mudar: versao de asset
    (`?v=`), token CSRF, UUID gerado no banco e indentacao/linhas vazias
    (o split do workout.html em parciais muda espacos, nunca conteudo)."""
    if csrf_token:
        html = html.replace(csrf_token, '<csrf>')
    for pattern in _CSRF_PATTERNS:
        html = pattern.sub(r'\1<csrf>\2', html)
    html = _ASSET_VERSION_RE.sub(r'\1<asset>', html)
    html = _UUID_RE.sub('<uuid>', html)
    lines = (line.strip() for line in html.splitlines())
    return '\n'.join(line for line in lines if line) + '\n'


@override_settings(
    STATIC_ASSET_VERSION='golden',
    PUBLIC_WORKOUT_LEGACY_TEMPLATE_SLUGS=frozenset(),
    STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY='golden-vapid-public-key',
    STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY='golden-vapid-private-key',
    STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT='mailto:golden@example.test',
    PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS='push.example.test',
)
class CurvaWorkoutGoldenMasterTests(TestCase):
    maxDiff = None

    def _get_page(self, slug):
        # Mesmo caminho do aluno real: sessao de login verificada do dono.
        sign_in_public_workout_account(self.client, PublicWorkoutSubscription.objects.get(plan_slug=slug).account)
        response = self.client.get(f'/renan/{slug}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        csrf_cookie = response.cookies.get('csrftoken')
        return normalize_html(
            response.content.decode('utf-8'),
            csrf_token=csrf_cookie.value if csrf_cookie else None,
        )

    def _assert_golden(self, case, html):
        path = GOLDEN_DIR / f'{case}.html'
        if os.environ.get(UPDATE_ENV_VAR) == '1':
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html, encoding='utf-8', newline='\n')
            return
        self.assertTrue(
            path.exists(),
            f'golden ausente: {path}. Gere com {UPDATE_ENV_VAR}=1 (ver docstring do arquivo).',
        )
        expected = path.read_text(encoding='utf-8')
        if html == expected:
            return
        diff = ''.join(difflib.unified_diff(
            expected.splitlines(keepends=True), html.splitlines(keepends=True),
            fromfile=f'golden/{case}.html', tofile=f'renderizado/{case}.html', n=2,
        ))
        if len(diff) > 6000:
            diff = diff[:6000] + '\n... (diff truncado)\n'
        self.fail(
            f'HTML de /renan/<slug> mudou no caso {case!r}.\n'
            'Num PR de split isto e regressao: o split nao pode mudar o HTML.\n'
            f'Mudanca intencional fora do split: rode com {UPDATE_ENV_VAR}=1 e revise o diff.\n\n{diff}'
        )

    def test_student_without_history(self):
        # Primeiro acesso: wizard de onboarding, aba Cargas vazia, pagamento
        # ainda nao configurado (sem Stripe e sem valor personalizado).
        with freeze_time(FROZEN_NOW):
            _create_catalog()
            _create_student(pk=990001, slug='gm-ana', onboarded=False)
            publish_program(slug='gm-ana', payload=_payload())
            html = self._get_page('gm-ana')

        self._assert_golden('sem_historico', html)

    def test_student_with_loads_and_periodization(self):
        # Tier com nutricao, Customer Portal, periodizacao canonica e cardio,
        # historico com recorde, aquecimento, correcao e carga de hoje.
        with freeze_time(FROZEN_NOW):
            _create_catalog()
            account = _create_student(
                pk=990002, slug='gm-bia', tier=PublicWorkoutTier.PREMIUM, stripe_customer_id='cus_golden_bia',
            )
            publish_program(slug='gm-bia', payload=_payload(periodization=True, cardio=True))
            _record_history(account)
            html = self._get_page('gm-bia')

        self._assert_golden('carga_periodizacao', html)

    def test_student_with_guided_session_in_progress(self):
        # Sessao guiada aberta na versao 1; a versao 2 publicada depois nao
        # pode trocar a ficha em andamento. Checkout com valor personalizado.
        with freeze_time(FROZEN_NOW):
            _create_catalog()
            account = _create_student(
                pk=990003, slug='gm-caio', tier=PublicWorkoutTier.COMPLETO, custom_monthly_price=Decimal('149.90'),
            )
            publish_program(slug='gm-caio', payload=_payload(periodization=True))
            _record_guided_top_set(account, slug='gm-caio', day_id='qua')
            publish_program(slug='gm-caio', payload=_payload(label='Programa golden v2'))
            html = self._get_page('gm-caio')

        self._assert_golden('guiado_em_andamento', html)

    def test_student_with_blocked_payment(self):
        # Assinatura em atraso: tela dedicada de pagamento pendente, nao o treino.
        with freeze_time(FROZEN_NOW):
            _create_catalog()
            _create_student(
                pk=990004, slug='gm-davi', status=PublicWorkoutSubscriptionStatus.PAST_DUE,
                stripe_customer_id='cus_golden_davi',
            )
            publish_program(slug='gm-davi', payload=_payload())
            html = self._get_page('gm-davi')

        self._assert_golden('pagamento_bloqueado', html)
