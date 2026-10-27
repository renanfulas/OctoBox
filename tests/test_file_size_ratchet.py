"""
ARQUIVO: trava de tamanho (ratchet) dos arquivos de codigo.

POR QUE ELE EXISTE:
- docs/plans/split-arquivos-grandes-plano.md, ADR-4. Sem trava, os arquivos
  divididos voltam a crescer em poucos meses e os que ainda nao foram divididos
  so pioram.

REGRAS:
1. Arquivo grande listado em LINE_CEILINGS pode encolher, nunca crescer alem do
   teto (o tamanho dele no main de 21/10/2026).
2. Qualquer outro arquivo Python de producao tem no maximo 600 linhas. Vale
   para arquivo novo e para os que ja estao abaixo disso.
3. Entrada que sobrou (arquivo apagado, renomeado ou .py que ja cabe em 600
   linhas) falha ate ser removida: assim o teto nunca afrouxa a regra geral.

FORA DA REGRA:
- Testes (tests.py, test_*.py, *_tests.py, pastas tests/, helpers `_test_`) e
  migracoes: crescem por natureza e nao sao o problema que o plano ataca.
- Templates e JS so entram quando listados abaixo (os dois do plano).

COMO MANTER:
- Encolheu? Nao precisa mexer aqui; abaixar o teto e opcional (e evita conflito
  entre PRs paralelos, que era justamente um dos problemas).
- Precisa crescer? Divida o arquivo. Subir teto so com justificativa no PR.
"""

from __future__ import annotations

from tests.source_tree_test_support import REPO_ROOT, count_lines, is_test_file, iter_python_files


NEW_PYTHON_FILE_LIMIT = 600

# Medido no main f2778059 (21/10/2026). O #360 e o #358 entraram antes da trava
# e fizeram crescer use_cases.py, workout_board_views.py, operations/forms.py e
# workout-guided.js: os tetos deles sao o tamanho depois desses merges, nao uma
# excecao.
LINE_CEILINGS = {
    # Arquivos do plano de split (auditoria, secao 2).
    # +1 no #357: campo PublicWorkoutTrainingSet.duration_seconds (isometria). Mover
    # model de arquivo dentro de um PR de feature é mais arriscado que 1 linha; o
    # split de models é a Fase 5 do plano.
    'public_workouts/models.py': 1540,
    'public_workouts/services.py': 1534,
    'student_app/views/public_workout_views.py': 1332,
    'student_identity/public_workout_views.py': 1200,
    'catalog/views/student_views.py': 1077,
    'public_workouts/templatetags/public_workouts_extras.py': 988,
    'templates/public_workouts/workout.html': 772,
    'static/js/public_workouts/workout-guided.js': 1026,
    # Demais arquivos Python de producao que ja passavam de 600 linhas.
    'operations/manager_workspace_queries.py': 933,
    'student_app/application/use_cases.py': 915,
    'operations/workout_board_views.py': 909,
    'config/settings/base.py': 818,  # +3 P03: instala o middleware depois da resolução tenant.
    'public_workouts/notifications.py': 813,
    'boxcore/management/commands/seed_south_sp_box.py': 780,  # +2 P03: aplica o fence ao seed tenant.
    'public_workouts/admin.py': 765,
    'dashboard/presentation.py': 761,
    'control/services.py': 732,
    'integrations/stripe/router.py': 731,  # +21 P03: resolve Box e mantém webhook sob o write fence.
    'dashboard/dashboard_snapshot_queries.py': 684,
    'student_app/models.py': 682,
    'operations/workout_editor_actions.py': 670,
    'student_identity/models.py': 668,
}


def test_large_files_never_grow_past_their_ceiling():
    grown = []
    stale = []
    for relative, ceiling in sorted(LINE_CEILINGS.items()):
        path = REPO_ROOT / relative
        if not path.exists():
            stale.append(f'{relative}: nao existe mais')
            continue
        lines = count_lines(path)
        if lines > ceiling:
            grown.append(f'{relative}: {lines} linhas (teto {ceiling})')
        elif relative.endswith('.py') and lines <= NEW_PYTHON_FILE_LIMIT:
            stale.append(f'{relative}: {lines} linhas, ja cabe no limite de {NEW_PYTHON_FILE_LIMIT}')

    assert not grown, (
        'arquivo grande cresceu; divida em modulos menores em vez de subir o teto '
        '(docs/plans/split-arquivos-grandes-plano.md):\n' + '\n'.join(grown)
    )
    assert not stale, 'remova estas entradas de LINE_CEILINGS:\n' + '\n'.join(stale)


def test_other_python_files_stay_under_the_limit():
    too_big = []
    for path in iter_python_files(skip_migrations=True):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative in LINE_CEILINGS or is_test_file(path):
            continue
        lines = count_lines(path)
        if lines > NEW_PYTHON_FILE_LIMIT:
            too_big.append(f'{relative}: {lines} linhas')

    assert not too_big, (
        f'arquivo Python de producao acima de {NEW_PYTHON_FILE_LIMIT} linhas; divida por assunto '
        '(docs/plans/split-arquivos-grandes-plano.md, ADR-4):\n' + '\n'.join(too_big)
    )
