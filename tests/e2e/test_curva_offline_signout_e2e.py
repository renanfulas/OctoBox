"""F3 offline-first (docs/plans/curva-offline-first-estrategia.md): "Sair da
conta" num aparelho compartilhado apaga tudo o que o app guardou da conta, e
avisa antes quando ainda há registro não enviado — que se perderia."""

from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import Page, expect

from tests.e2e.curva_login import enter_with_magic_link
from tests.e2e.curva_offline import visit_once_under_service_worker

_EMAIL = 'curva-signout-e2e@example.test'

_LOCAL_DATABASES = """async () => (await indexedDB.databases()).map((db) => db.name)"""

_SAVED_PAGE = """(slug) => new Promise((resolve) => {
  const request = indexedDB.open('curva-offline-pages', 1);
  request.onupgradeneeded = () => request.result.createObjectStore('pages', { keyPath: 'slug' });
  request.onsuccess = () => {
    const db = request.result;
    const read = db.transaction('pages').objectStore('pages').get(slug);
    read.onsuccess = () => { db.close(); resolve(Boolean(read.result)); };
  };
})"""


@pytest.fixture(autouse=True)
def _cleanup(django_db_blocker):
    def cleanup():
        with django_db_blocker.unblock():
            from public_workouts.models import PublicWorkoutAccount, PublicWorkoutAssessment, PublicWorkoutProgram

            PublicWorkoutAccount.objects.filter(email=_EMAIL).delete()
            PublicWorkoutAssessment.objects.filter(plan_slug='bruno').delete()
            PublicWorkoutProgram.objects.filter(slug='bruno').delete()

    cleanup()
    yield
    cleanup()


def _prepare_student():
    from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoginToken, PublicWorkoutSubscription
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    publish_program(slug='bruno', payload=build_example_payload())
    account = PublicWorkoutAccount.objects.create(email=_EMAIL, onboarding_completed_at=timezone.now())
    PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')
    token = PublicWorkoutLoginToken.objects.create(account=account, expires_at=timezone.now() + timedelta(hours=1))
    return account, token


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_sign_out_warns_about_unsent_records_and_wipes_the_device(page: Page, live_server):
    from public_workouts.models import PublicWorkoutAssessment

    account, token = _prepare_student()
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.wait_for_url('**/renan/bruno**')
    visit_once_under_service_worker(page)

    # Sem conexão não dá para sair: só o servidor encerra a sessão.
    dialogs = []
    answer = {'accept': False}

    def on_dialog(dialog):
        dialogs.append(dialog.message)
        if answer['accept']:
            dialog.accept()
        else:
            dialog.dismiss()

    page.on('dialog', on_dialog)
    page.locator('[data-workout-tab-target="workout-panel-perfil"]').click()
    page.context.set_offline(True)
    page.locator('[data-workout-signout]').click()
    page.wait_for_timeout(300)
    assert dialogs[-1] == 'Sem conexão. Conecte-se à internet para sair da conta.'
    page.context.set_offline(False)

    # Uma avaliação que não consegue subir (servidor fora) fica no aparelho.
    page.route('**/renan/bruno/avaliacoes', lambda route: route.abort('failed'))
    page.locator('[data-workout-cycle-nav][data-cycle-key="avaliacao"]').click()
    page.locator('#assess-f-weight').fill('81.2')
    page.locator('.assess-form-submit').click()
    expect(page.locator('#assess-f-feedback')).to_contain_text('Salva neste aparelho')
    badge = page.locator('[data-sync-badge]')
    expect(badge).to_have_text('1 registro a enviar')
    badge.click()
    panel = page.locator('[data-sync-panel]')
    expect(panel).to_be_visible()
    expect(panel).to_contain_text('Avaliações: 1 avaliação')
    expect(panel).to_contain_text('Mais antigo: agora há pouco')

    # Cancelar o aviso mantém a conta e o registro.
    page.locator('[data-workout-tab-target="workout-panel-perfil"]').click()
    page.locator('[data-workout-signout]').click()
    page.wait_for_timeout(300)
    assert dialogs[-1].startswith('Há 1 registro deste aparelho ainda não enviado ao servidor.'), dialogs[-1]
    assert '/renan/bruno' in page.url
    expect(badge).to_have_text('1 registro a enviar')

    # Confirmar: sai e apaga tudo da conta neste aparelho.
    answer['accept'] = True
    page.locator('[data-workout-signout]').click()
    page.wait_for_url('**/renan/offline/**')
    names = page.evaluate(_LOCAL_DATABASES)
    for name in (f'curva-guided:{account.pk}:bruno', f'public-workout-outbox:account:{account.pk}',
                 f'curva-offline-data:{account.pk}'):
        assert name not in names, (name, names)
    assert page.evaluate("() => localStorage.getItem('curva-guided-scope:bruno')") is None
    assert page.evaluate(_SAVED_PAGE, 'bruno') is False
    assert not PublicWorkoutAssessment.objects.filter(plan_slug='bruno').exists()
    from student_identity.public_workout_session import PUBLIC_WORKOUT_SESSION_COOKIE_NAME

    session_cookies = [cookie for cookie in page.context.cookies() if cookie['name'] == PUBLIC_WORKOUT_SESSION_COOKIE_NAME]
    assert not session_cookies or not session_cookies[0]['value'], 'a sessão do servidor também terminou'
