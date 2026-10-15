"""L4: aluno real usa o guia e o servidor confirma a sessão."""

import os
import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import Page, expect


_EMAIL = 'curva-guided-e2e@example.test'
_OTHER_EMAIL = 'curva-guided-other-e2e@example.test'
_MOVEMENT_SLUG = 'curva-guided-e2e-squat'


@pytest.fixture(autouse=True)
def _cleanup_guided_e2e(django_db_blocker):
    def cleanup():
        with django_db_blocker.unblock():
            from public_workouts.models import PublicWorkoutAccount, PublicWorkoutMovement, PublicWorkoutProgram

            PublicWorkoutAccount.objects.filter(email=_EMAIL).delete()
            PublicWorkoutAccount.objects.filter(email=_OTHER_EMAIL).delete()
            PublicWorkoutProgram.objects.filter(slug='bruno', program_id='guided-e2e-2026').delete()
            PublicWorkoutMovement.objects.filter(slug=_MOVEMENT_SLUG).delete()

    cleanup()
    yield
    cleanup()


def _prepare_guided_student():
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
        ],
    }
    publish_program(slug='bruno', payload=payload)
    account = PublicWorkoutAccount.objects.create(email=_EMAIL)
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
    page.goto(f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
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

    page.goto(f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
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
def test_guided_start_and_set_sync_after_network_returns(page: Page, live_server):
    from public_workouts.models import PublicWorkoutTrainingSession

    account, token = _prepare_guided_student()
    page.goto(f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
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
def test_guided_reopens_from_offline_shell_and_sends_in_order(page: Page, live_server):
    from public_workouts.models import PublicWorkoutTrainingSession

    account, token = _prepare_guided_student()
    page.goto(f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
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
    page.goto(f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
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
    expect(page.locator('[data-workout-guided-conflict]')).to_be_visible()
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
    page.goto(f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
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
    page.goto(f'{live_server.url}/treinos/login?token={replacement.token}&next=/renan/bruno')
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
    page.goto(f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
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
    page.goto(f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
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
