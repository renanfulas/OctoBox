"""Abertura do app sem internet chega ao painel do treinador (/treinos/coach)
quando a conexão volta, com o horário em que o aluno abriu."""

from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import Page

from tests.e2e.curva_login import enter_with_magic_link
from tests.e2e.curva_offline import visit_once_under_service_worker

_EMAIL = 'curva-app-open-e2e@example.test'


@pytest.fixture(autouse=True)
def _cleanup(django_db_blocker):
    def cleanup():
        with django_db_blocker.unblock():
            from public_workouts.models import PublicWorkoutAccount, PublicWorkoutProgram

            PublicWorkoutAccount.objects.filter(email=_EMAIL).delete()
            PublicWorkoutProgram.objects.filter(slug='bruno').delete()

    cleanup()
    yield
    cleanup()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_offline_open_reaches_the_server_with_the_time_it_happened(page: Page, live_server):
    from public_workouts.models import (
        PublicWorkoutAccount, PublicWorkoutLoginToken, PublicWorkoutProgramOpen, PublicWorkoutSubscription,
    )
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    publish_program(slug='bruno', payload=build_example_payload())
    account = PublicWorkoutAccount.objects.create(email=_EMAIL, onboarding_completed_at=timezone.now())
    PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')
    token = PublicWorkoutLoginToken.objects.create(account=account, expires_at=timezone.now() + timedelta(hours=1))
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.wait_for_url('**/renan/bruno**')
    visit_once_under_service_worker(page)
    # As visitas online já contaram; o que interessa aqui é a aberta sem rede.
    PublicWorkoutProgramOpen.objects.filter(account=account).delete()

    page.context.set_offline(True)
    page.reload()
    opened_offline_at = page.evaluate('Number(document.body.dataset.offlineSnapshot) && Date.now()')
    assert opened_offline_at, 'não abriu da cópia salva'
    page.wait_for_timeout(500)
    assert not PublicWorkoutProgramOpen.objects.filter(account=account).exists()

    page.context.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    for _ in range(100):
        if PublicWorkoutProgramOpen.objects.filter(account=account).exists():
            break
        page.wait_for_timeout(100)
    row = PublicWorkoutProgramOpen.objects.get(account=account)
    assert row.plan_slug == 'bruno'
    assert abs(row.opened_at.timestamp() * 1000 - opened_offline_at) < 5000
