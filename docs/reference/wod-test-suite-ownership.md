<!--
ARQUIVO: ownership final da suite de testes do corredor de WOD.

TIPO DE DOCUMENTO:
- referencia tecnica de testes
- mapa final de ownership

AUTORIDADE:
- alta para localizar onde cada teste do corredor de WOD deve nascer

DOCUMENTOS PAIS:
- [operations-wod-ownership-map.md](operations-wod-ownership-map.md)
- [../plans/wod-test-ownership-split-corda.md](../plans/wod-test-ownership-split-corda.md)
- [../plans/wod-test-ownership-wave0-inventory.md](../plans/wod-test-ownership-wave0-inventory.md)

QUANDO USAR:
- quando a duvida for em qual arquivo colocar um teste novo de WOD
- quando um PR tocar o corredor de WOD e precisarmos saber qual suite subir
- quando alguem novo no projeto quiser ler a cobertura sem abrir arquivos aleatorios

POR QUE ELE EXISTE:
- encerra a trilha de split da suite com um mapa curto e estavel
- evita que os testes voltem a se concentrar por conveniencia
- deixa claro o contrato entre ownership de codigo e ownership de cobertura
-->

# Ownership final da suite de WOD

## Tese curta

Hoje a suite de WOD nao mora mais em um arquivo monolitico.

Ela acompanha os corredores reais do codigo:

1. coach editor
2. aprovacao
3. pos-publicacao
4. governanca semanal

Em linguagem simples:

1. cada sala do predio agora tem seu proprio detector de incendio

## Mapa final

### 1. Editor do coach

Arquivo:

1. [tests/test_coach_wod_editor.py](../../tests/test_coach_wod_editor.py)

Ownership:

1. abrir o editor do WOD
2. criar treino e submeter para aprovacao
3. editar bloco e movimento inline
4. duplicar treino para outra aula

Suba primeiro este arquivo quando:

1. o coach nao conseguir montar ou editar treino
2. o fluxo HTTP do editor quebrar
3. a duplicacao ou o submit falharem

### 2. Board de aprovacao

Arquivo:

1. [tests/test_workout_approval_board.py](../../tests/test_workout_approval_board.py)

Ownership:

1. aprovar
2. rejeitar
3. exigir confirmacao de mudanca sensivel
4. renderizar diff, resumo e trilha de decisao
5. filtrar a fila de aprovacao

Suba primeiro este arquivo quando:

1. a fila pendente estiver errada
2. a aprovacao ou rejeicao falharem
3. o diff da revisao ficar inconsistente

### 3. Historico publicado e pos-publicacao

Arquivo:

1. [tests/test_workout_post_publication_history.py](../../tests/test_workout_post_publication_history.py)

Ownership:

1. historico executivo publicado
2. filtro do historico por motivo
3. alertas pos-publicacao
4. follow-up de acao sugerida
5. memoria operacional curta

Suba primeiro este arquivo quando:

1. o historico publicado vier errado
2. os alertas operacionais divergirem
3. follow-up ou memoria nao forem registrados como esperado

### 4. Governanca semanal

Arquivo:

1. [tests/test_workout_weekly_governance.py](../../tests/test_workout_weekly_governance.py)

Ownership:

1. checkpoint semanal
2. mudanca de ritmo
3. maturidade operacional
4. alerta leve de gestao

Suba primeiro este arquivo quando:

1. a leitura executiva semanal ficar estranha
2. o checkpoint nao salvar
3. o ritmo ou a maturidade vierem incoerentes

## Ordem de leitura por problema

### Bug no editor do coach

Leia:

1. [tests/test_coach_wod_editor.py](../../tests/test_coach_wod_editor.py)
2. [operations/workspace_views.py](../../operations/workspace_views.py)
3. [operations/workout_support.py](../../operations/workout_support.py)

### Bug na aprovacao

Leia:

1. [tests/test_workout_approval_board.py](../../tests/test_workout_approval_board.py)
2. [operations/workout_action_views.py](../../operations/workout_action_views.py)
3. [operations/workout_approval_board_context.py](../../operations/workout_approval_board_context.py)

### Bug no historico ou follow-up

Leia:

1. [tests/test_workout_post_publication_history.py](../../tests/test_workout_post_publication_history.py)
2. [operations/workout_published_history.py](../../operations/workout_published_history.py)
3. [operations/workout_board_builders.py](../../operations/workout_board_builders.py)

### Bug na governanca semanal

Leia:

1. [tests/test_workout_weekly_governance.py](../../tests/test_workout_weekly_governance.py)
2. [operations/workout_board_builders.py](../../operations/workout_board_builders.py)
3. [operations/workout_action_views.py](../../operations/workout_action_views.py)

## Guardrails

1. teste novo deve nascer no corredor dominante, nao no arquivo mais conveniente
2. helper de teste deve reduzir repeticao real sem esconder a historia do teste
3. fluxo integrado entre corredores ainda pode existir, mas sem recolonizar um arquivo monolitico
4. se um teste novo tocar dois corredores, escolha onde mora a regra principal e documente a excecao

## Smoke minimo por PR de WOD

1. `python manage.py test tests.test_coach_wod_editor`
2. `python manage.py test tests.test_workout_approval_board`
3. `python manage.py test tests.test_workout_post_publication_history`
4. `python manage.py test tests.test_workout_weekly_governance`
5. `python manage.py check`

## Resumo infantil

Pense na suite como uma escola organizada:

1. o caderno do coach fica com aula do coach
2. o caderno da aprovacao fica com carimbo e revisao
3. o caderno do historico fica com o que aconteceu depois
4. o caderno da governanca fica com a reuniao da semana

Quando cada assunto fica no seu caderno, estudar e corrigir fica muito mais facil.
