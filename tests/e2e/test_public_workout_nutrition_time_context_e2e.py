"""
ARQUIVO: E2E da aba Dieta sendo CONTEXTUAL por horario (pedido do Renan,
`static/js/public_workouts/nutrition.js`).

POR QUE EXISTE:
- a logica de "Agora"/"Proxima refeicao" (pickCurrentAndNext/groupMealsByTime
  em nutrition.js) decide o que mostrar com base em `new Date()` do
  DISPOSITIVO DO ALUNO -- e' exatamente o tipo de comportamento que os
  testes Python de template (test_workout_template.py) NAO cobrem, porque
  eles so verificam o HTML estatico gerado pelo servidor, nunca o relogio
  do navegador rodando o JS de verdade. Sem um E2E com o relogio travado
  (`page.clock`), uma regressao em pickCurrentAndNext (ex.: trocar `<=` por
  `<`, ou inverter a ordem do sort) passaria a suite inteira sem ser
  detectada.
- Cobre os 3 estados de horario que a logica trata de forma diferente:
  entre duas refeicoes (Agora + Proxima), antes da primeira (so' Proxima,
  com aviso) e depois da ultima (so' Agora, com aviso de "ultima do dia").

PONTOS CRITICOS:
- `page.clock.install(time=...)` TEM que rodar antes de `page.goto` -- a
  aba Dieta busca o cardapio automaticamente ao carregar a pagina (sem
  botao "Ver plano alimentar", ver nutrition.js), entao `new Date()` ja
  roda durante o load inicial. Instalar o relogio depois do goto chegaria
  tarde demais pro primeiro render.
- O plano alimentar e' SEMPRE privado (nunca por slug publico, ver D.6 em
  public_workouts/models.py::PublicWorkoutMealPlan) -- precisa de sessao
  de verdade. Reusa o MESMO fluxo de login por token magico que o aluno
  real usa (`/treinos/login?token=...`), nunca um atalho de sessao de
  teste, pra testar o caminho que o aluno realmente percorre.
- Executar localmente:
    pytest tests/e2e/test_public_workout_nutrition_time_context_e2e.py \\
        --create-db --migrations --headed
"""

from __future__ import annotations

import datetime

import pytest
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import Page, expect

_TEST_EMAIL = 'nutricao-e2e@octoboxfit.test'


@pytest.fixture(autouse=True)
def _cleanup_after_e2e(django_db_blocker):
    """Mesmo motivo do fixture irmao em test_public_workout_cycle_nav_e2e.py:
    sem limpeza explicita, uma execucao com --reuse-db deixa residuo
    (conta/assinatura/plano de teste, versao de programa) que vaza pros
    proximos testes desta mesma suite."""
    yield
    with django_db_blocker.unblock():
        from public_workouts.models import (
            PublicWorkoutAccount,
            PublicWorkoutProgram,
        )

        PublicWorkoutProgram.objects.filter(slug='bruno').delete()
        PublicWorkoutAccount.objects.filter(email=_TEST_EMAIL).delete()


def _publish_minimal_program(slug: str) -> None:
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    publish_program(slug=slug, payload=build_example_payload())


def _login_token_for_unlocked_account_with_meal_plan(slug: str) -> str:
    """Cria conta com tier Completo (libera nutricao), publica um plano de
    3 refeicoes em horarios bem separados (07:00/12:00/19:00 -- folga
    grande o bastante pra nenhum teste cair numa borda por acidente) e
    devolve um token de login valido por 1h."""
    from public_workouts.models import (
        PublicWorkoutAccount,
        PublicWorkoutLoginToken,
        PublicWorkoutProfessional,
        PublicWorkoutSubscription,
        PublicWorkoutTier,
    )
    from public_workouts.services import publish_meal_plan

    account, _ = PublicWorkoutAccount.objects.get_or_create(email=_TEST_EMAIL)
    PublicWorkoutSubscription.objects.update_or_create(
        account=account,
        defaults={'plan_slug': slug, 'tier': PublicWorkoutTier.COMPLETO},
    )
    nutricionista = PublicWorkoutProfessional.objects.get(role='nutricao')

    payload = {
        'schema_version': 1,
        'daily_targets': {'kcal': 2000, 'protein_g': 150, 'carbs_g': 200, 'fat_g': 60},
        'meals': [
            {
                'meal_id': 'cafe-e2e',
                'label': 'Café da manhã E2E',
                'time': '07:00',
                'items': [{'food': 'Ovo', 'quantity': '2 unidades'}],
            },
            {
                'meal_id': 'almoco-e2e',
                'label': 'Almoço E2E',
                'time': '12:00',
                'items': [{'food': 'Arroz', 'quantity': '150g'}],
            },
            {
                'meal_id': 'jantar-e2e',
                'label': 'Jantar E2E',
                'time': '19:00',
                'items': [{'food': 'Frango', 'quantity': '150g'}],
            },
        ],
    }
    publish_meal_plan(account_id=account.pk, payload=payload, authored_by=nutricionista)

    login_token = PublicWorkoutLoginToken.objects.create(
        account=account, expires_at=timezone.now() + datetime.timedelta(hours=1),
    )
    return str(login_token.token)


def _open_dieta_tab(page: Page, live_server, fixed_time: datetime.datetime, token: str) -> None:
    # Instala o relogio ANTES do goto -- ver docstring do modulo.
    page.clock.install(time=fixed_time)
    page.goto(f'{live_server.url}/treinos/login?token={token}')

    avaliacao_cycle = page.locator('[data-workout-cycle-nav][data-cycle-key="avaliacao"]')
    avaliacao_cycle.click()  # Inicio -> Avaliacao (1o estado do ciclo)
    avaliacao_cycle.click()  # Avaliacao -> Dieta (2o estado do ciclo)

    # Contas E2E novas podem iniciar o wizard de onboarding. O backdrop cobre
    # a página e intercepta cliques mesmo fora do fluxo que este teste valida.
    onboarding_backdrop = page.locator('[data-onboarding-dismiss]')
    if onboarding_backdrop.is_visible():
        onboarding_backdrop.click()
        expect(onboarding_backdrop).to_be_hidden()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_dieta_shows_current_and_next_meal_between_two_meal_times(page: Page, live_server):
    """09:30, entre o café (07:00) e o almoço (12:00): Agora = café,
    Próxima = almoço, jantar nem deveria aparecer ainda."""
    _publish_minimal_program('bruno')
    token = _login_token_for_unlocked_account_with_meal_plan('bruno')

    _open_dieta_tab(page, live_server, datetime.datetime(2026, 1, 5, 9, 30), token)

    content = page.locator('[data-workout-nutrition-content]')
    expect(content.get_by_text('Agora')).to_be_visible()
    expect(content).to_contain_text('Café da manhã E2E')
    expect(content.get_by_text('Próxima refeição')).to_be_visible()
    expect(content).to_contain_text('Almoço E2E')
    expect(content).not_to_contain_text('Jantar E2E')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_dieta_shows_only_next_meal_before_the_first_meal_time(page: Page, live_server):
    """05:00, antes do café (07:00): ainda não existe refeição "em
    andamento" — só a próxima aparece, com o aviso de que a primeira
    refeição ainda não chegou."""
    _publish_minimal_program('bruno')
    token = _login_token_for_unlocked_account_with_meal_plan('bruno')

    _open_dieta_tab(page, live_server, datetime.datetime(2026, 1, 5, 5, 0), token)

    content = page.locator('[data-workout-nutrition-content]')
    expect(content).to_contain_text('Sua primeira refeição do dia ainda não chegou')
    expect(content.get_by_text('Próxima refeição')).to_be_visible()
    expect(content).to_contain_text('Café da manhã E2E')
    expect(content).not_to_contain_text('Almoço E2E')
    expect(content).not_to_contain_text('Jantar E2E')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_dieta_shows_only_current_meal_after_the_last_meal_time(page: Page, live_server):
    """21:00, depois do jantar (19:00): Agora = jantar, e o aviso de que
    foi a última refeição prevista pra hoje — sem seção "Próxima"."""
    _publish_minimal_program('bruno')
    token = _login_token_for_unlocked_account_with_meal_plan('bruno')

    _open_dieta_tab(page, live_server, datetime.datetime(2026, 1, 5, 21, 0), token)

    content = page.locator('[data-workout-nutrition-content]')
    expect(content.get_by_text('Agora')).to_be_visible()
    expect(content).to_contain_text('Jantar E2E')
    expect(content).to_contain_text('Essa foi a última refeição prevista pra hoje')
    expect(content.get_by_text('Próxima refeição')).not_to_be_visible()
    expect(content).not_to_contain_text('Café da manhã E2E')
    expect(content).not_to_contain_text('Almoço E2E')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_ver_dieta_completa_toggle_shows_all_meals_and_back_button_returns_to_contextual(page: Page, live_server):
    """O botão "Ver dieta completa" continua disponível em qualquer horário
    pra quem quiser rolar o cardápio inteiro, e "Ver só o horário de agora"
    volta pro recorte contextual."""
    _publish_minimal_program('bruno')
    token = _login_token_for_unlocked_account_with_meal_plan('bruno')

    _open_dieta_tab(page, live_server, datetime.datetime(2026, 1, 5, 9, 30), token)

    content = page.locator('[data-workout-nutrition-content]')
    expect(content).not_to_contain_text('Jantar E2E')

    content.get_by_role('button', name='Ver dieta completa').click()
    expect(content).to_contain_text('Café da manhã E2E')
    expect(content).to_contain_text('Almoço E2E')
    expect(content).to_contain_text('Jantar E2E')

    content.get_by_role('button', name='Ver só o horário de agora').click()
    expect(content).to_contain_text('Almoço E2E')
    expect(content).not_to_contain_text('Jantar E2E')
