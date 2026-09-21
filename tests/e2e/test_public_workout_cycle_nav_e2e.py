"""
ARQUIVO: E2E do ciclo Treino/Cardio/Periodizacao do bottom nav (Onda B3,
`templates/public_workouts/workout.html`).

POR QUE EXISTE:
- O botao de ciclo (`data-workout-cycle-nav`, JS inline em workout.html)
  alterna Treino -> Cardio -> Periodizacao -> Treino a cada toque, e volta
  pro estado Treino quando o aluno navega pra outro item da nav e clica de
  novo. Isso e comportamento 100% client-side (JS puro, sem view por tras
  de cada estado) -- os testes Python existentes (test_workout_template.py,
  student_app/tests.py::PublicWorkoutTemplatePreviewViewTests) so verificam
  o HTML gerado pelo servidor (ex.: o atributo `data-cycle-targets` vem com
  a string certa), nunca o clique de verdade. Uma regressao no handler JS
  (ex.: alguem mexendo perto dele por engano numa fatia futura) passaria os
  457 testes da suite normal sem ser detectada.
- Cobre exatamente o fluxo que o Renan pediu pra proteger: clicar Treino ->
  aparece Cardio, clicar de novo -> aparece Periodizacao, clicar de novo ->
  volta pra Treino; e o reset ao navegar pra outro item da nav e voltar.

PONTOS CRITICOS:
- Precisa de PublicWorkoutProgram publicado com `cardio` E `periodization`
  no payload (build_example_payload() do schema.py nao tem nenhum dos
  dois) -- sem isso o ciclo teria so 1 estado (so Treino) e nao testaria
  nada. Ver _publish_program_with_cardio_and_periodization abaixo.
- Executar localmente:
    pytest tests/e2e/test_public_workout_cycle_nav_e2e.py --create-db --migrations --headed
  Em CI: ver .github/workflows/e2e-nightly.yml (so' roda no nightly, como
  todo tests/e2e/ -- ver docs/testing/e2e-guide.md).
"""

import re

import pytest
from django.test import override_settings
from playwright.sync_api import Page, expect


@pytest.fixture(autouse=True)
def _cleanup_published_programs_after_e2e(django_db_blocker):
    """O schema public nao era limpo pelo teardown tenant deste E2E.

    Sem a remocao explicita, uma execucao com --reuse-db fazia os testes
    unitarios seguintes comecarem em v3/v4, produzindo falso negativo.
    """
    yield
    with django_db_blocker.unblock():
        from public_workouts.models import PublicWorkoutProgram

        PublicWorkoutProgram.objects.filter(slug='bruno').delete()


def _publish_program_with_cardio_and_periodization(slug: str) -> None:
    from public_workouts.services import publish_program

    payload = {
        'schema_version': 1,
        'program_id': f'{slug}-e2e-cycle-nav',
        'program_label': 'Programa E2E ciclo',
        'started_on': '2026-01-05',
        'weeks': 2,
        'accent_variant': None,
        'days': [
            {
                'day_id': 'seg',
                'label': 'Segunda',
                'blocks': [
                    {
                        'movements': [
                            {
                                'movement_slug': 'agachamento-livre',
                                'reps_spec': '3x8-10',
                                'rir_spec': 'RIR 2',
                                'is_tracked': True,
                                'load_type': 'percentage_of_rm',
                                'load_value': 75.0,
                                'reference_url': None,
                            },
                        ],
                    },
                ],
            },
        ],
        'cardio': {
            'sessions': [
                {
                    'title': 'Corrida leve E2E',
                    'badge': '20 min',
                    'note': 'Ritmo confortavel, zona 2.',
                    'details': [{'label': 'Duração', 'value': '20 min'}],
                },
            ],
        },
        'periodization': {
            'weeks_table': [
                {'week': 'S1', 'focus': 'Adaptação E2E', 'reps': '8-10', 'guidance': 'RIR 3'},
                {'week': 'S2', 'focus': 'Build E2E', 'reps': '6-8', 'guidance': 'RIR 2'},
            ],
            'volume_table': [],
            'note': 'Nota de periodizacao E2E.',
            'chart': [
                {
                    'label': 'S1', 'focus': 'Adaptação E2E', 'reps': '8-10',
                    'color': '#111111', 'bg': '#222222', 'fg': '#ffffff', 'h': 50,
                },
            ],
        },
    }
    publish_program(slug=slug, payload=payload)


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_bottom_nav_cycles_treino_cardio_periodizacao_and_back(page: Page, live_server):
    """
    Clicar repetido no botao de ciclo do bottom nav deve percorrer
    Treino -> Cardio -> Periodizacao -> Treino, mostrando SO' o painel da
    vez (os outros dois escondidos) e atualizando o rotulo do botao.
    """
    _publish_program_with_cardio_and_periodization('bruno')

    page.goto(f'{live_server.url}/renan/bruno/preview-b3')

    inicio_panel = page.locator('#workout-panel-inicio')
    treino_panel = page.locator('#workout-panel-treino')
    cardio_panel = page.locator('#workout-panel-cardio')
    periodizacao_panel = page.locator('#workout-panel-periodizacao')
    cycle_button = page.locator('[data-workout-cycle-nav]')
    cycle_label = page.locator('[data-cycle-label]')

    # ── Estado inicial (page load, nenhum clique ainda): o painel padrao
    # servido pelo Django e' Inicio (class="is-tab-active" cravada no HTML
    # de workout.html, nao Treino) -- o botao de ciclo comeca INATIVO, com
    # o rotulo default "Treino" so' de enfeite (span estatico do template).
    expect(inicio_panel).to_be_visible()
    expect(treino_panel).not_to_be_visible()
    expect(cardio_panel).not_to_be_visible()
    expect(periodizacao_panel).not_to_be_visible()
    expect(cycle_label).to_have_text('Treino')
    expect(cycle_button).not_to_have_class(re.compile(r'\bis-active\b'))

    # ── 1o clique: chegando de OUTRO botao (Inicio) -- sempre ATERRISSA em
    # Treino, nunca avanca direto pra Cardio (so' avanca quando o proprio
    # botao de ciclo ja estava ativo, ver comentario em workout.html).
    cycle_button.click()

    expect(cycle_label).to_have_text('Treino')
    expect(treino_panel).to_be_visible()
    expect(inicio_panel).not_to_be_visible()
    expect(cardio_panel).not_to_be_visible()
    expect(periodizacao_panel).not_to_be_visible()

    # ── 2o clique (botao ja ativo): Treino -> Cardio ─────────────────────
    cycle_button.click()

    expect(cycle_label).to_have_text('Cardio')
    expect(cardio_panel).to_be_visible()
    expect(cardio_panel).to_contain_text('Corrida leve E2E')
    expect(treino_panel).not_to_be_visible()
    expect(periodizacao_panel).not_to_be_visible()

    # ── 3o clique: Cardio -> Periodizacao ────────────────────────────────
    cycle_button.click()

    expect(cycle_label).to_have_text('Periodização')
    expect(periodizacao_panel).to_be_visible()
    expect(periodizacao_panel).to_contain_text('Adaptação E2E')
    expect(cardio_panel).not_to_be_visible()
    expect(treino_panel).not_to_be_visible()

    # ── 4o clique: Periodizacao -> volta pra Treino ──────────────────────
    cycle_button.click()

    expect(cycle_label).to_have_text('Treino')
    expect(treino_panel).to_be_visible()
    expect(cardio_panel).not_to_be_visible()
    expect(periodizacao_panel).not_to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_bottom_nav_cycle_resets_to_treino_after_navigating_away(page: Page, live_server):
    """
    Sair do ciclo pra outro item da nav (ex.: Inicio) e depois clicar de
    novo no botao de ciclo deve ATERRISSAR em Treino, nunca continuar de
    onde parou -- so' avanca o ciclo quando o proprio botao ja esta ativo
    (ver comentario em workout.html sobre resetCycleToTreino)."""
    _publish_program_with_cardio_and_periodization('bruno')

    page.goto(f'{live_server.url}/renan/bruno/preview-b3')

    cycle_button = page.locator('[data-workout-cycle-nav]')
    cycle_label = page.locator('[data-cycle-label]')
    inicio_button = page.locator('[data-workout-tab-target="workout-panel-inicio"]')
    treino_panel = page.locator('#workout-panel-treino')
    cardio_panel = page.locator('#workout-panel-cardio')

    # 1o clique: chegando de Inicio (padrao da pagina), aterrissa em Treino.
    cycle_button.click()
    expect(cycle_label).to_have_text('Treino')
    expect(treino_panel).to_be_visible()

    # 2o clique (botao ja ativo): avanca pro estado Cardio.
    cycle_button.click()
    expect(cycle_label).to_have_text('Cardio')
    expect(cardio_panel).to_be_visible()

    # Navega pra outro item da nav -- o botao de ciclo perde o estado "ativo".
    inicio_button.click()
    expect(page.locator('#workout-panel-inicio')).to_be_visible()
    expect(cardio_panel).not_to_be_visible()

    # Clicar no botao de ciclo de novo deve resetar pra Treino, NAO avancar
    # pra Periodizacao (o que aconteceria se o indice interno do ciclo
    # continuasse de onde parou).
    cycle_button.click()

    expect(cycle_label).to_have_text('Treino')
    expect(treino_panel).to_be_visible()
    expect(cardio_panel).not_to_be_visible()
    expect(page.locator('#workout-panel-periodizacao')).not_to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_bottom_nav_cycle_only_treino_when_program_has_no_cardio_or_periodization(
    page: Page, live_server,
):
    """Programa sem cardio/periodization (a maioria dos 10 legados, antes
    do PR #249): o botao de ciclo so' tem Treino -- clicar nele repetido
    nunca deve fazer aparecer um painel vazio ou travar o rotulo."""
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    publish_program(slug='bruno', payload=build_example_payload())

    page.goto(f'{live_server.url}/renan/bruno/preview-b3')

    cycle_button = page.locator('[data-workout-cycle-nav]')
    cycle_label = page.locator('[data-cycle-label]')
    treino_panel = page.locator('#workout-panel-treino')

    # 1o clique (chegando de Inicio): aterrissa em Treino -- unico alvo do
    # ciclo quando o programa nao tem cardio/periodization.
    cycle_button.click()
    expect(cycle_label).to_have_text('Treino')
    expect(treino_panel).to_be_visible()

    # Cliques seguintes (botao ja ativo, so' 1 alvo no ciclo): permanece em
    # Treino -- nunca deveria mostrar um painel vazio nem travar o rotulo.
    cycle_button.click()
    cycle_button.click()

    expect(cycle_label).to_have_text('Treino')
    expect(treino_panel).to_be_visible()
