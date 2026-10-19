"""L4: aluno real usa o guia e o servidor confirma a sessão."""

import os
import json
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import Page, expect

from tests.e2e.curva_login import enter_with_magic_link


_EMAIL = 'curva-guided-e2e@example.test'
_OTHER_EMAIL = 'curva-guided-other-e2e@example.test'
_MOVEMENT_SLUG = 'curva-guided-e2e-squat'
_SECOND_MOVEMENT_SLUG = 'curva-guided-e2e-row'
_THIRD_MOVEMENT_SLUG = 'curva-guided-e2e-press'
# Conta quantas vezes a página abre o banco local do guia (guided-outbox.js).
_COUNT_OUTBOX_OPENS = """
(() => {
  const open = IDBFactory.prototype.open;
  window.__curvaOutboxOpens = 0;
  IDBFactory.prototype.open = function (name) {
    if (String(name).startsWith('curva-guided:')) window.__curvaOutboxOpens += 1;
    return open.apply(this, arguments);
  };
})();
"""


# Anota a frequência de cada bipe do modo foco e quantas vezes o áudio é religado.
_SPY_AUDIO = """
(() => {
  window.__curvaBeeps = [];
  window.__curvaAudioResumes = 0;
  const Real = window.AudioContext;
  window.AudioContext = class extends Real {
    resume() { window.__curvaAudioResumes += 1; return super.resume(); }
    createOscillator() {
      const osc = super.createOscillator();
      const start = osc.start.bind(osc);
      osc.start = (...args) => { window.__curvaBeeps.push(Math.round(osc.frequency.value)); return start(...args); };
      return osc;
    }
  };
})();
"""


@pytest.fixture(autouse=True)
def _cleanup_guided_e2e(django_db_blocker):
    def cleanup():
        with django_db_blocker.unblock():
            from public_workouts.models import (
                PublicWorkoutAccount, PublicWorkoutMovement, PublicWorkoutOutboxMessage,
                PublicWorkoutProgram, PublicWorkoutTrainingSession,
            )

            program_ids = PublicWorkoutProgram.objects.filter(slug='bruno', program_id='guided-e2e-2026').values_list('pk', flat=True)
            session_ids = PublicWorkoutTrainingSession.objects.filter(
                account__email__in=(_EMAIL, _OTHER_EMAIL),
            ).values_list('pk', flat=True)
            PublicWorkoutOutboxMessage.objects.filter(
                aggregate_type='program', aggregate_id__in=[str(pk) for pk in program_ids],
            ).delete()
            PublicWorkoutOutboxMessage.objects.filter(
                aggregate_type='training_session', aggregate_id__in=[str(pk) for pk in session_ids],
            ).delete()
            PublicWorkoutAccount.objects.filter(email=_EMAIL).delete()
            PublicWorkoutAccount.objects.filter(email=_OTHER_EMAIL).delete()
            PublicWorkoutProgram.objects.filter(slug='bruno', program_id='guided-e2e-2026').delete()
            PublicWorkoutMovement.objects.filter(slug=_MOVEMENT_SLUG).delete()
            PublicWorkoutMovement.objects.filter(slug=_SECOND_MOVEMENT_SLUG).delete()
            PublicWorkoutMovement.objects.filter(slug=_THIRD_MOVEMENT_SLUG).delete()

    cleanup()
    yield
    cleanup()


def _prepare_guided_student(stages=None, *, freeform_count=0):
    from public_workouts.models import (
        PublicWorkoutAccount, PublicWorkoutLoadLog, PublicWorkoutLoginToken,
        PublicWorkoutSubscription,
    )
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    payload = build_example_payload()
    payload['program_id'] = 'guided-e2e-2026'
    payload['days'][0]['blocks'][0]['movements'][0]['movement_slug'] = _MOVEMENT_SLUG
    payload['days'][0]['blocks'][0]['movements'][0]['guided_prescription'] = {
        'version': 1, 'stages': [
            {'stage_id': 'top', 'role': 'top_set', 'min_sets': 1, 'max_sets': 2,
             'reps_min': 6, 'reps_max': 8, 'rest_seconds': 30,
             'load_rule': {'kind': 'manual'}},
        ] if stages is None else stages,
    }
    if freeform_count:
        first = payload['days'][0]['blocks'][0]['movements'][0]
        first.pop('guided_prescription')
        first['reps_spec'] = ''
        for slug in (_SECOND_MOVEMENT_SLUG, _THIRD_MOVEMENT_SLUG)[:freeform_count - 1]:
            extra = deepcopy(first)
            extra['movement_slug'] = slug
            payload['days'][0]['blocks'][0]['movements'].append(extra)
    publish_program(slug='bruno', payload=payload)
    account = PublicWorkoutAccount.objects.create(
        email=_EMAIL, onboarding_completed_at=timezone.now(),
    )
    PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')
    token = PublicWorkoutLoginToken.objects.create(account=account, expires_at=timezone.now() + timedelta(hours=1))
    return account, token


def _start_guided(page: Page):
    page.locator('[data-workout-guided-start]').click()
    # A contagem 3-2-1 do modo foco aceita um toque para começar na hora.
    page.locator('[data-guided-countdown-skip]').click()


def _wait_for_offline_scope(page: Page):
    # wait_for_function com string avalia via eval na página e a CSP (sem
    # 'unsafe-eval') bloqueia; page.evaluate passa pelo protocolo do navegador.
    from playwright.sync_api import Error as PlaywrightError

    page.wait_for_url('**/renan/bruno**')
    for _ in range(100):
        try:
            if page.evaluate("() => !!localStorage.getItem('curva-guided-scope:bruno')"):
                return
        except PlaywrightError:
            pass  # o login ainda pode estar redirecionando
        page.wait_for_timeout(100)
    raise AssertionError('o guia não salvou a ficha offline neste aparelho')


def _finish_from_summary(page: Page):
    # "Finalizar" mora no resumo; "Ver treino todo" leva até ele a qualquer momento.
    page.locator('[data-guided-open-sheet]').click()
    page.locator('[data-guided-open-summary]').click()
    page.locator('[data-workout-guided-finish]').click()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_freeform_summary_requires_each_exercise_and_records_partial(page: Page, live_server):
    from public_workouts.models import PublicWorkoutTrainingSession

    account, token = _prepare_guided_student(freeform_count=3)
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    _start_guided(page)
    page.locator('[data-workout-guided-weight]').fill('50')
    page.locator('[data-workout-guided-reps]').fill('8')
    page.locator('[data-workout-guided-set]').click()
    expect(page.locator('[data-guided-receipt-status]')).to_have_text('✓ Salvo')
    page.locator('[data-guided-open-sheet]').click()
    page.locator('[data-guided-open-summary]').click()
    summary = page.locator('[data-guided-screen="summary"]')
    expect(summary.locator('[data-guided-title]')).to_have_text('Faltam 2 exercícios sem registro para finalizar')
    expect(summary.locator('[data-workout-guided-finish]')).to_be_hidden()
    expect(summary.locator('[data-workout-guided-partial]')).to_be_visible()
    summary.locator('[data-workout-guided-partial]').click()
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('parcial')
    session = PublicWorkoutTrainingSession.objects.get(account=account)
    assert session.outcome == 'partial'
    assert session.completed_set_count == 1


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_offline_freeform_finish_requires_each_exercise(page: Page, live_server):
    _, token = _prepare_guided_student(freeform_count=2)
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    _wait_for_offline_scope(page)
    page.evaluate("async () => { await navigator.serviceWorker.ready; }")
    page.context.set_offline(True)
    page.reload()
    page.locator('[data-offline-open]').click()
    page.locator('[data-offline-start]').click()
    expect(page.locator('[data-offline-status]')).to_contain_text('Início salvo')
    page.locator('[data-offline-weight]').fill('50')
    page.locator('[data-offline-reps]').fill('8')
    page.locator('[data-offline-set]').click()
    expect(page.locator('[data-offline-status]')).to_contain_text('Série salva')
    expect(page.locator('[data-offline-finish]')).to_be_hidden()
    expect(page.locator('[data-offline-partial]')).to_be_visible()
    page.locator('[data-offline-weight]').fill('45')
    page.locator('[data-offline-reps]').fill('8')
    page.locator('[data-offline-set]').click()
    expect(page.locator('[data-offline-finish]')).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_student_top_target_guides_ramp_and_survives_reload(page: Page, live_server):
    from public_workouts.models import PublicWorkoutTrainingSession

    page.set_viewport_size({'width': 390, 'height': 844})
    stages = [
        {'stage_id': 'prep', 'role': 'warmup', 'min_sets': 1, 'max_sets': 1,
         'reps_min': 8, 'reps_max': 8, 'rest_seconds': 0,
         'load_rule': {'kind': 'percent_of_top', 'start_percent': 40, 'end_percent': 40}},
        {'stage_id': 'feeder', 'role': 'feeder', 'min_sets': 1, 'max_sets': 1,
         'reps_min': 6, 'reps_max': 6, 'rest_seconds': 0,
         'load_rule': {'kind': 'percent_of_top', 'start_percent': 70, 'end_percent': 70}},
        {'stage_id': 'top', 'role': 'top_set', 'min_sets': 1, 'max_sets': 1,
         'reps_min': 6, 'reps_max': 6, 'rest_seconds': 0,
         'load_rule': {'kind': 'suggested_top'}},
    ]
    account, token = _prepare_guided_student(stages)
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    _start_guided(page)

    target = page.locator('[data-workout-guided-top-target]')
    expect(target).to_be_visible()
    target.locator('[data-workout-guided-top-input]').fill('100')
    target.locator('[data-workout-guided-top-apply]').click()
    expect(page.locator('[data-workout-guided-weight]')).to_have_value('40')
    expect(page.locator('[data-guided-weight-source]')).to_contain_text('Top alvo')
    if screenshot_path := os.environ.get('CURVA_LOAD_SCREENSHOT'):
        page.screenshot(path=screenshot_path, full_page=True)
    page.locator('[data-workout-guided-reps]').fill('8')
    page.locator('[data-workout-guided-set]').click()

    # O modo foco reabre sozinho (#treino-guiado) e o alvo vem do aparelho.
    page.reload()
    expect(page.locator('[data-workout-guided-weight]')).to_have_value('70')
    page.locator('[data-workout-guided-weight]').fill('65')
    page.locator('[data-workout-guided-reps]').fill('6')
    page.locator('[data-workout-guided-set]').click()
    expect(page.locator('[data-workout-guided-weight]')).to_have_value('100')
    page.locator('[data-workout-guided-weight]').fill('95')
    page.locator('[data-workout-guided-reps]').fill('6')
    page.locator('[data-workout-guided-set]').click()
    page.locator('[data-workout-guided-finish]').click()
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('Treino concluído')

    session = PublicWorkoutTrainingSession.objects.get(account=account)
    assert session.outcome == 'completed'
    assert list(session.sets.order_by('set_number').values_list('weight_kg', flat=True)) == [
        Decimal('40'), Decimal('65'), Decimal('95'),
    ]


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_load_conflict_keeps_values_and_reapplies_after_confirmation(page: Page, live_server):
    _, token = _prepare_guided_student()
    sent = []

    def respond_load(route):
        sent.append(route.request.post_data_json)
        if len(sent) == 1:
            route.fulfill(status=409, content_type='application/json', body=json.dumps({
                'error': 'Este registro já foi corrigido.',
                'active_record': {
                    'idempotency_key': 'servidor-atual', 'movement_slug': _MOVEMENT_SLUG,
                    'weight_kg': 45, 'reps': 8, 'rir': 2,
                },
            }))
        else:
            route.fulfill(status=200, content_type='application/json', body='{}')

    page.route('**/renan/bruno/carga', respond_load)
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    page.locator('[data-workout-load-toggle]').click()
    widget = page.locator(f'[data-workout-load-input][data-movement-slug="{_MOVEMENT_SLUG}"]').first
    widget.locator('[data-workout-load-field]').fill('50')
    widget.locator('[data-workout-reps-field]').fill('8')
    widget.locator('[data-workout-load-save]').click()

    notice = page.locator('[data-workout-load-sync-notice]')
    expect(notice).to_be_visible()
    expect(notice).to_contain_text('50 kg')
    expect(notice).to_contain_text('45 kg')
    page.once('dialog', lambda dialog: dialog.accept())
    notice.locator('[data-load-sync-reapply]').click()
    expect(notice).to_be_hidden()
    expect(widget.locator('[data-workout-load-status]')).to_contain_text('Registro sincronizado')
    assert len(sent) == 2
    assert sent[1]['supersedes_idempotency_key'] == 'servidor-atual'


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_guided_top_set_finishes_and_survives_reload(page: Page, live_server):
    from public_workouts.models import PublicWorkoutLoadLog, PublicWorkoutTrainingSession

    if os.environ.get('CURVA_GUIDED_VIEWPORT') == 'mobile':
        page.set_viewport_size({'width': 390, 'height': 844})
    account, token = _prepare_guided_student()

    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    expect(page.locator('[data-workout-guided-start]')).to_be_visible()
    page.locator('[data-workout-guided-start]').click()
    expect(page.locator('[data-workout-guided-active]')).to_be_visible()
    # Contagem completa: 3, 2, 1, GO e a tela do exercício.
    expect(page.locator('[data-guided-screen="exercise"]')).to_be_visible(timeout=8000)
    if screenshot_path := os.environ.get('CURVA_GUIDED_SCREENSHOT'):
        page.screenshot(path=screenshot_path, full_page=True)
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    newer = build_example_payload()
    newer['program_id'] = 'guided-e2e-2026'
    newer['days'][0]['blocks'][0]['movements'][0]['movement_slug'] = _MOVEMENT_SLUG
    newer['days'][0]['blocks'][0]['movements'][0]['guided_prescription'] = {
        'version': 1, 'stages': [
            {'stage_id': 'new-top', 'role': 'top_set', 'min_sets': 1, 'max_sets': 1,
             'reps_min': 12, 'reps_max': 12, 'rest_seconds': 45,
             'load_rule': {'kind': 'manual'}},
        ],
    }
    publish_program(slug='bruno', payload=newer)
    # Recarregar com o modo foco aberto (#treino-guiado) volta direto ao exercício,
    # na versão do programa em que a sessão começou.
    page.reload()
    expect(page.locator('[data-guided-screen="exercise"]')).to_be_visible()
    expect(page.locator('[data-guided-meta]')).to_contain_text('6–8 reps')
    page.locator('[data-workout-guided-weight]').fill('50')
    page.locator('[data-workout-guided-reps]').fill('7')
    # O GET de atualização pode chegar enquanto o aluno digita. O mesmo
    # passo não deve apagar a carga nem as repetições antes do envio.
    with page.expect_response(lambda response: response.request.method == 'GET' and '/sessao' in response.url):
        page.evaluate("window.dispatchEvent(new Event('online'))")
    expect(page.locator('[data-workout-guided-weight]')).to_have_value('50')
    expect(page.locator('[data-workout-guided-reps]')).to_have_value('7')
    page.locator('[data-workout-guided-set]').click()
    expect(page.locator('[data-workout-guided-timer]')).to_contain_text('Descanso')
    expect(page.locator('[data-guided-receipt]')).to_contain_text('50 kg')

    page.reload()
    expect(page.locator('[data-workout-guided-active]')).to_be_visible()
    expect(page.locator('[data-guided-screen="rest"]')).to_be_visible()
    _finish_from_summary(page)
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('Treino concluído')
    expect(page.locator('[data-guided-screen="finished"]')).to_contain_text('Treino registrado no Curva')

    session = PublicWorkoutTrainingSession.objects.get(account=account)
    assert session.outcome == 'completed'
    assert session.completed_set_count == 1
    assert PublicWorkoutLoadLog.objects.get(account=account, is_active=True).weight_kg == Decimal('50.00')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_last_week_guided_load_fills_this_week_suggestion(page: Page, live_server):
    """100 kg na Top da semana 1 aparece, sem digitar, como 107,5 kg na semana 2."""
    from public_workouts.models import (
        PublicWorkoutAccount, PublicWorkoutLoginToken, PublicWorkoutSubscription, PublicWorkoutTrainingSession,
    )
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program
    from public_workouts.training_sessions import finish_session, record_set, start_session

    today = timezone.localdate()
    payload = build_example_payload()
    payload['program_id'] = 'guided-e2e-2026'
    # Começou há uma semana: hoje é a semana 2 (força-hipertrofia) e o registro foi na 1 (volume).
    payload['started_on'] = (today - timedelta(days=7)).isoformat()
    payload['periodization'] = {'weeks': [
        {'week_number': 1, 'phase_type': 'volume'},
        {'week_number': 2, 'phase_type': 'strength_hypertrophy'},
    ], 'volume_table': [], 'note': ''}
    movement = payload['days'][0]['blocks'][0]['movements'][0]
    movement.update({
        'movement_slug': _MOVEMENT_SLUG, 'load_type': 'free', 'load_value': None,
        'reps_spec': '2x8 aquecimento + 1x6-8 Top', 'rir_spec': 'RIR 2',
        'guided_prescription': {'version': 1, 'stages': [
            {'stage_id': 'aquecimento', 'role': 'warmup', 'min_sets': 2, 'max_sets': 2,
             'reps_min': 8, 'reps_max': 8, 'rest_seconds': 30,
             'load_rule': {'kind': 'percent_of_top', 'start_percent': 40, 'end_percent': 55}},
            {'stage_id': 'top', 'role': 'top_set', 'min_sets': 1, 'max_sets': 1,
             'reps_min': 6, 'reps_max': 8, 'rest_seconds': 30, 'load_rule': {'kind': 'suggested_top'}},
        ]},
    })
    publish_program(slug='bruno', payload=payload)
    account = PublicWorkoutAccount.objects.create(email=_EMAIL, onboarding_completed_at=timezone.now())
    PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')
    last_week = start_session(account_id=account.pk, plan_slug='bruno', day_id='seg')
    PublicWorkoutTrainingSession.objects.filter(pk=last_week.pk).update(started_at=timezone.now() - timedelta(days=7))
    record_set(
        account_id=account.pk, plan_slug='bruno', session_id=last_week.pk, movement_index=0, set_number=3,
        movement_slug=_MOVEMENT_SLUG, role='top_set', weight=Decimal('100.00'), reps=8, rir=Decimal('2.0'),
    )
    finish_session(account_id=account.pk, plan_slug='bruno', session_id=last_week.pk, partial=True)
    token = PublicWorkoutLoginToken.objects.create(account=account, expires_at=timezone.now() + timedelta(hours=1))

    page.goto(f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    _start_guided(page)
    weight = page.locator('[data-workout-guided-weight]')
    # Aquecimento 1 = 40% da Top sugerida (107,5) -> 42,5 kg, já preenchido.
    expect(weight).to_have_value('42,5')
    expect(page.locator('[data-guided-weight-source]')).to_contain_text('ajuste se precisar')
    for _ in range(2):
        page.locator('[data-workout-guided-skip]').click()
        if page.locator('[data-guided-skip-rest]').is_visible():
            page.locator('[data-guided-skip-rest]').click()
    # Top: 100 x 76/67 = 113,4, teto 80% do 1RM estimado (133,3) = 106,7 -> 107,5 kg.
    expect(weight).to_have_value('107,5')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_guided_online_set_is_one_request_with_local_receipt(page: Page, live_server):
    from public_workouts.models import PublicWorkoutTrainingSession

    account, token = _prepare_guided_student()
    page.add_init_script(_COUNT_OUTBOX_OPENS)
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    _start_guided(page)
    expect(page.locator('[data-guided-screen="exercise"]')).to_be_visible()
    sent = []
    page.on('request', lambda request: sent.append(request.method) if request.url.endswith('/renan/bruno/sessao') else None)
    page.locator('[data-workout-guided-weight]').fill('50')
    page.locator('[data-workout-guided-reps]').fill('7')
    page.locator('[data-workout-guided-set]').click()
    # Gravação local primeiro; o ✓ só chega com a resposta daquela série.
    expect(page.locator('[data-guided-receipt-status]')).to_have_text('✓ Salvo')
    page.wait_for_timeout(600)
    assert sent == ['POST'], 'série online: 1 POST e nenhum GET /sessao depois'
    # As ~9 transações da série (fila, lease, lista, envio, remoção...) reaproveitam a conexão.
    assert page.evaluate('() => window.__curvaOutboxOpens') == 1, 'o banco local abre uma vez por página'
    session = PublicWorkoutTrainingSession.objects.get(account=account)
    assert session.sets.get().weight_kg == Decimal('50.00')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_rest_end_beeps_by_default_and_student_can_mute(page: Page, live_server):
    _account, token = _prepare_guided_student([
        {'stage_id': 'top', 'role': 'top_set', 'min_sets': 2, 'max_sets': 2,
         'reps_min': 6, 'reps_max': 8, 'rest_seconds': 4, 'load_rule': {'kind': 'manual'}},
    ])
    page.add_init_script(_SPY_AUDIO)
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    _start_guided(page)
    expect(page.locator('[data-guided-screen="exercise"]')).to_be_visible()
    # Aluno que nunca mexeu no painel: som ligado, e o toque em "Iniciar" já religou o áudio.
    assert page.locator('[data-guided-sound]').get_attribute('aria-checked') == 'true'
    assert page.evaluate('() => window.__curvaAudioResumes') >= 1

    page.evaluate('() => { window.__curvaBeeps = []; }')
    page.locator('[data-workout-guided-weight]').fill('50')
    page.locator('[data-workout-guided-reps]').fill('7')
    page.locator('[data-workout-guided-set]').click()
    expect(page.locator('[data-guided-screen="rest"]')).to_be_visible()
    # Descanso de 4 s: bipes curtos no 3-2-1 e o tom de "Valendo" no fim.
    expect(page.locator('[data-guided-screen="exercise"]')).to_be_visible(timeout=10_000)
    beeps = page.evaluate('() => window.__curvaBeeps')
    assert 660 in beeps and beeps[-1] == 990, beeps

    page.locator('[data-guided-open-sheet]').click()
    page.locator('[data-guided-sound]').click()
    assert page.locator('[data-guided-sound]').get_attribute('aria-checked') == 'false'
    assert page.evaluate("() => localStorage.getItem('curva-guided-sound')") == '0'


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_guided_set_survives_tab_closed_before_post_returns(page: Page, live_server):
    from public_workouts.models import PublicWorkoutTrainingSession

    account, token = _prepare_guided_student()
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    _start_guided(page)
    expect(page.locator('[data-guided-screen="exercise"]')).to_be_visible()

    def hold_set(route):
        # O POST da série nunca sai: a aba fecha antes da resposta.
        if route.request.method == 'POST' and (route.request.post_data_json or {}).get('action') == 'set':
            return
        route.continue_()

    page.route('**/renan/bruno/sessao', hold_set)
    page.locator('[data-workout-guided-weight]').fill('57.5')
    page.locator('[data-workout-guided-reps]').fill('7')
    page.locator('[data-workout-guided-set]').click()
    expect(page.locator('[data-guided-receipt-status]')).to_have_text('Salvo no aparelho')
    context = page.context
    page.close()
    assert not PublicWorkoutTrainingSession.objects.get(account=account).sets.exists()

    reopened = context.new_page()
    reopened.goto(f'{live_server.url}/renan/bruno')
    # O lease da aba morta expira (~12 s) e a nova aba envia a série da fila.
    expect(reopened.locator('[data-workout-guided-status]')).to_contain_text('Tudo enviado', timeout=30000)
    session = PublicWorkoutTrainingSession.objects.get(account=account)
    assert session.sets.get().weight_kg == Decimal('57.50')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_guided_start_and_set_sync_after_network_returns(page: Page, live_server):
    from public_workouts.models import PublicWorkoutTrainingSession

    account, token = _prepare_guided_student()
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    page.context.set_offline(True)
    _start_guided(page)
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('iniciado neste aparelho')
    page.locator('[data-workout-guided-weight]').fill('52.5')
    page.locator('[data-workout-guided-reps]').fill('7')
    page.locator('[data-workout-guided-set]').click()
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('salva neste aparelho')
    expect(page.locator('[data-guided-receipt-status]')).to_contain_text('Salvo no aparelho')

    page.context.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('Tudo enviado', timeout=15000)
    _finish_from_summary(page)
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('Treino concluído')
    session = PublicWorkoutTrainingSession.objects.get(account=account)
    assert session.outcome == 'completed'
    assert session.sets.get().weight_kg == Decimal('52.50')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_reconnecting_does_not_erase_a_set_being_typed(page: Page, live_server):
    from public_workouts.models import PublicWorkoutTrainingSession

    account, token = _prepare_guided_student()
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    page.context.set_offline(True)
    _start_guided(page)
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('iniciado neste aparelho')
    page.locator('[data-workout-guided-weight]').fill('61.5')
    page.locator('[data-workout-guided-reps]').fill('7')

    page.context.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('Tudo enviado', timeout=15000)
    expect(page.locator('[data-workout-guided-weight]')).to_have_value('61.5')
    expect(page.locator('[data-workout-guided-reps]')).to_have_value('7')
    page.locator('[data-workout-guided-set]').click()
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('Série registrada')
    assert PublicWorkoutTrainingSession.objects.get(account=account).sets.get().weight_kg == Decimal('61.50')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_guided_reopens_from_offline_shell_and_sends_in_order(page: Page, live_server):
    from public_workouts.models import PublicWorkoutTrainingSession

    account, token = _prepare_guided_student()
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    _wait_for_offline_scope(page)
    page.evaluate("async () => { await navigator.serviceWorker.ready; }")
    page.context.set_offline(True)
    page.reload()
    expect(page.locator('[data-offline-open]')).to_be_visible()
    page.locator('[data-offline-open]').click()
    expect(page.locator('[data-offline-guide]')).to_be_visible()
    if screenshot_path := os.environ.get('CURVA_OFFLINE_SCREENSHOT'):
        page.screenshot(path=screenshot_path, full_page=True)
    page.locator('[data-offline-start]').click()
    expect(page.locator('[data-offline-status]')).to_contain_text('Início salvo')
    page.locator('[data-offline-weight]').fill('55')
    page.locator('[data-offline-reps]').fill('7')
    page.locator('[data-offline-set]').click()
    expect(page.locator('[data-offline-status]')).to_contain_text('Série salva')
    page.goto(f'{live_server.url}/renan/bruno?offline-reopen=2')
    if page.locator('[data-offline-open]').count():
        page.locator('[data-offline-open]').click()
        expect(page.locator('[data-offline-finish]')).to_be_visible()
        page.locator('[data-offline-finish]').click()
        expect(page.locator('[data-offline-status]')).to_contain_text('Encerramento guardado')
    else:
        # Chromium pode devolver a página já aberta do cache HTTP durante a
        # segunda navegação offline; o guia deve restaurar o mesmo rascunho.
        page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
        page.locator('[data-guided-resume]').click()
        expect(page.locator('[data-workout-guided-active]')).to_be_visible()
        _finish_from_summary(page)
        expect(page.locator('[data-workout-guided-status]')).to_contain_text('pendente de envio')
    page.context.set_offline(False)
    page.reload()
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('Tudo enviado', timeout=15000)
    session = PublicWorkoutTrainingSession.objects.get(account=account)
    assert session.outcome == 'completed'
    assert session.sets.get().weight_kg == Decimal('55.00')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_offline_start_conflict_preserves_export_and_opens_new_program(page: Page, live_server):
    from public_workouts.models import PublicWorkoutTrainingSession
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    account, token = _prepare_guided_student()
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    page.context.set_offline(True)
    _start_guided(page)
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('iniciado neste aparelho')
    page.locator('[data-workout-guided-weight]').fill('47.5')
    page.locator('[data-workout-guided-reps]').fill('7')
    page.locator('[data-workout-guided-set]').click()
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('salva neste aparelho')

    newer = build_example_payload()
    newer['program_id'] = 'guided-e2e-2026'
    newer['days'][0]['blocks'][0]['movements'][0]['movement_slug'] = _MOVEMENT_SLUG
    newer['days'][0]['blocks'][0]['movements'][0]['guided_prescription'] = {
        'version': 1, 'stages': [
            {'stage_id': 'new-top', 'role': 'top_set', 'min_sets': 1, 'max_sets': 1,
             'reps_min': 12, 'reps_max': 12, 'rest_seconds': 45,
             'load_rule': {'kind': 'manual'}},
        ],
    }
    publish_program(slug='bruno', payload=newer)
    page.context.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    # Com o modo foco aberto, o conflito chega como aviso fixo que leva à ficha.
    page.locator('[data-guided-toast-action]').click(timeout=15000)
    expect(page.locator('[data-workout-guided-conflict]')).to_be_visible(timeout=15000)
    # A visita à ficha nova não pode apagar a versão necessária para retomar
    # ou exportar o treino que ainda está na fila local.
    old_plan_version = page.evaluate("""async () => {
        const scope = localStorage.getItem('curva-guided-scope:bruno');
        return (await window.CurvaGuidedOutbox.restorePlan(scope)).program_version;
    }""")
    page.reload()
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    expect(page.locator('[data-workout-guided-conflict]')).to_be_visible(timeout=15000)
    preserved = page.evaluate("""async () => {
        const scope = localStorage.getItem('curva-guided-scope:bruno');
        return {
            plan: await window.CurvaGuidedOutbox.restorePlan(scope),
            pending: await window.CurvaGuidedOutbox.list(scope),
            current: document.querySelector('[data-workout-guided]').dataset.programVersion,
        };
    }""")
    assert preserved['plan']['program_version'] == old_plan_version
    assert str(preserved['current']) != str(old_plan_version)
    assert preserved['pending']
    with page.expect_download() as download:
        page.locator('[data-workout-guided-conflict-export]').click()
    assert download.value.suggested_filename == 'curva-treino-pendente.json'
    page.on('dialog', lambda dialog: dialog.accept())
    with page.expect_navigation(wait_until='domcontentloaded'):
        page.locator('[data-workout-guided-conflict-server]').click()
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    expect(page.locator('[data-workout-guided-start]')).to_be_visible(timeout=15000)
    assert not PublicWorkoutTrainingSession.objects.filter(account=account).exists()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_queued_training_waits_for_same_account_login(page: Page, live_server):
    from public_workouts.models import PublicWorkoutLoginToken, PublicWorkoutTrainingSession
    from student_identity.public_workout_session import PUBLIC_WORKOUT_SESSION_COOKIE_NAME

    account, token = _prepare_guided_student()
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    page.context.set_offline(True)
    _start_guided(page)
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('iniciado neste aparelho')
    page.locator('[data-workout-guided-weight]').fill('57.5')
    page.locator('[data-workout-guided-reps]').fill('7')
    page.locator('[data-workout-guided-set]').click()
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('salva neste aparelho')
    page.context.add_cookies([{
        'name': PUBLIC_WORKOUT_SESSION_COOKIE_NAME, 'value': 'expired',
        'domain': 'localhost', 'path': '/',
    }])
    page.context.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('Entre novamente', timeout=15000)
    assert not PublicWorkoutTrainingSession.objects.filter(account=account).exists()

    replacement = PublicWorkoutLoginToken.objects.create(
        account=account, expires_at=timezone.now() + timedelta(hours=1),
    )
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={replacement.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('Tudo enviado', timeout=15000)
    session = PublicWorkoutTrainingSession.objects.get(account=account)
    assert session.sets.get().weight_kg == Decimal('57.50')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_two_tabs_drain_one_local_queue_without_duplicate_top(page: Page, live_server):
    from public_workouts.models import PublicWorkoutLoadLog, PublicWorkoutTrainingSession

    account, token = _prepare_guided_student()
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    second = page.context.new_page()
    second.goto(f'{live_server.url}/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    page.context.set_offline(True)
    _start_guided(page)
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('iniciado neste aparelho')
    page.locator('[data-workout-guided-weight]').fill('60')
    page.locator('[data-workout-guided-reps]').fill('7')
    page.locator('[data-workout-guided-set]').click()
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('salva neste aparelho')

    page.context.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    second.evaluate("window.dispatchEvent(new Event('online'))")
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('Tudo enviado', timeout=20000)
    session = PublicWorkoutTrainingSession.objects.get(account=account)
    assert session.sets.count() == 1
    assert PublicWorkoutLoadLog.objects.filter(account=account, is_active=True).count() == 1
    second.close()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_account_switch_does_not_send_queued_sets_to_another_student(page: Page, live_server):
    from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription, PublicWorkoutTrainingSession
    from student_identity.public_workout_session import (
        PUBLIC_WORKOUT_SESSION_COOKIE_NAME, build_public_workout_session_value,
    )

    account, token = _prepare_guided_student()
    other = PublicWorkoutAccount.objects.create(email=_OTHER_EMAIL)
    PublicWorkoutSubscription.objects.create(account=other, plan_slug='bruno')
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    page.context.set_offline(True)
    _start_guided(page)
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('iniciado neste aparelho')
    page.locator('[data-workout-guided-weight]').fill('62.5')
    page.locator('[data-workout-guided-reps]').fill('7')
    page.locator('[data-workout-guided-set]').click()
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('salva neste aparelho')

    page.context.add_cookies([{
        'name': PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
        'value': build_public_workout_session_value(account_id=other.pk),
        'domain': 'localhost', 'path': '/',
    }])
    page.context.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('mesma conta', timeout=15000)
    assert not PublicWorkoutTrainingSession.objects.filter(account__in=[account, other]).exists()

    page.context.add_cookies([{
        'name': PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
        'value': build_public_workout_session_value(account_id=account.pk),
        'domain': 'localhost', 'path': '/',
    }])
    page.evaluate("window.dispatchEvent(new Event('online'))")
    expect(page.locator('[data-workout-guided-status]')).to_contain_text('Tudo enviado', timeout=15000)
    assert PublicWorkoutTrainingSession.objects.filter(account=account).count() == 1
    assert not PublicWorkoutTrainingSession.objects.filter(account=other).exists()
