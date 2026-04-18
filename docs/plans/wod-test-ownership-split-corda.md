<!--
ARQUIVO: C.O.R.D.A. para quebrar a suite monolitica de testes do corredor de WOD.

TIPO DE DOCUMENTO:
- plano arquitetural e operacional de testes
- trilho de refatoracao incremental

AUTORIDADE:
- alta para reorganizacao de ownership da suite de WOD
- media para estrategia de execucao dos testes

DOCUMENTOS PAIS:
- [operations-workspace-views-refactor-corda.md](operations-workspace-views-refactor-corda.md)
- [../reference/operations-wod-ownership-map.md](../reference/operations-wod-ownership-map.md)
- [../reference/reading-guide.md](../reference/reading-guide.md)

QUANDO USAR:
- quando a duvida for como quebrar `tests/test_coach_wod_editor.py` sem perder cobertura
- quando precisarmos alinhar a arquitetura dos testes com o ownership novo de `operations`
- quando uma alteracao no corredor de WOD estiver ficando dificil de validar porque os testes vivem todos no mesmo arquivo

POR QUE ELE EXISTE:
- evita que a refatoracao de codigo fique moderna e a suite continue monolitica
- reduz custo de leitura, revisao e manutencao da cobertura do WOD
- deixa claro qual arquivo de teste sobe para cada corredor real do dominio

O QUE ESTE ARQUIVO FAZ:
1. define o alvo de ownership dos testes do corredor de WOD
2. organiza a separacao por ondas pequenas e verificaveis
3. registra os riscos de fragmentar sem criterio
4. cria criterio de pronto para a suite nova
-->

# C.O.R.D.A. - Split de ownership dos testes de WOD

## C - Contexto

O corredor de WOD ja saiu da fase em que tudo morava em `operations/workspace_views.py`.

Hoje a arquitetura real ja esta separada entre:

1. [operations/workspace_views.py](../../operations/workspace_views.py)
2. [operations/workout_approval_board_context.py](../../operations/workout_approval_board_context.py)
3. [operations/workout_board_builders.py](../../operations/workout_board_builders.py)
4. [operations/workout_published_history.py](../../operations/workout_published_history.py)
5. [operations/workout_action_views.py](../../operations/workout_action_views.py)
6. [operations/workout_support.py](../../operations/workout_support.py)

Mas a rede de seguranca ainda ficou concentrada em um arquivo so:

1. [tests/test_coach_wod_editor.py](../../tests/test_coach_wod_editor.py)

Estado atual observado:

1. a suite tem 1186 linhas
2. existe uma unica classe `CoachWorkoutEditorFlowTests`
3. o arquivo mistura testes de:
   - editor do coach
   - aprovacao
   - filtros da board
   - diff e preview
   - historico publicado
   - alertas pos-publicacao
   - follow-up
   - checkpoint semanal
   - trilha de decisao
   - inline edit e duplicacao

Traducao simples:

1. a arquitetura do predio ja ganhou salas separadas
2. mas o alarme de incendio ainda esta ligado em um unico quadro eletrico

### Contrato atual implicito

Hoje o arquivo monolitico entrega valor, mas cobra um preco:

1. cada leitura demora mais
2. qualquer falha parece maior do que realmente e
3. revisar cobertura por ownership ficou dificil
4. uma pessoa nova precisa entender o corredor inteiro para mexer em um ponto pequeno

## O - Objetivo

Separar a suite do corredor de WOD por ownership tecnico, sem mudar o comportamento testado, para que:

1. cada arquivo de teste reflita um corredor real da aplicacao
2. o debug fique mais rapido
3. a manutencao acompanhe a arquitetura modular que ja existe no codigo
4. a cobertura continue equivalente ou melhor
5. o custo cognitivo caia sem criar um mini-framework de testes desnecessario

### Sucesso significa

1. `tests/test_coach_wod_editor.py` fica focado em coach editor e envio para aprovacao
2. `tests/test_workout_approval_board.py` cobre board, aprovacao, rejeicao, filtros e revisao
3. `tests/test_workout_post_publication_history.py` cobre historico publicado, alertas, follow-up e memoria
4. `tests/test_workout_weekly_governance.py` cobre checkpoint semanal, ritmo, maturidade e governanca leve
5. a suite completa continua verde
6. cada arquivo consegue rodar de forma isolada sem depender de ordem acidental

## R - Riscos

### 1. Fragmentar por assunto errado

Se quebrarmos por ordem cronologica de features em vez de ownership:

1. o problema volta depois
2. os testes ficam espalhados sem dono tecnico claro

### 2. Criar abstração teatral de testes

Se inventarmos factories, mixins e helpers demais:

1. a leitura piora
2. a suite fica “bonita por fora” e confusa por dentro

Traducao infantil:

1. nao precisamos construir um robo para amarrar o cadarco

### 3. Duplicar setup demais

Se cada arquivo recriar tudo sem nenhum criterio:

1. o custo de manutencao sobe
2. pequenas mudancas exigem varias edicoes iguais

### 4. Acoplar arquivos por ordem de execucao

Esse e o pior bug silencioso da trilha.

Se um teste passar so porque outro rodou antes:

1. a suite fica falsa
2. a confianca despenca

### 5. Perder cobertura de transicao entre corredores

Nem tudo deve virar teste super isolado.

Ainda precisamos manter alguns fluxos ponta a ponta para garantir:

1. coach monta
2. manager ou owner revisa
3. publicado entra no historico certo

## D - Direcao

### Tese central

Quebrar a suite pelo mesmo mapa de ownership do codigo, nao por gosto pessoal.

### Regra-mestra

1. um arquivo de teste deve ter um corredor dominante
2. fixtures e helpers compartilhados so entram quando cortarem repeticao real
3. smoke de integracao continua existindo
4. nomes dos arquivos devem explicar onde mexer primeiro

### Mapa alvo de arquivos

#### 1. Editor do coach

Arquivo:

1. [tests/test_coach_wod_editor.py](../../tests/test_coach_wod_editor.py)

Ownership alvo:

1. abrir o editor
2. criar treino
3. editar bloco e movimento inline
4. duplicar treino para outra aula
5. submeter para aprovacao

### 2. Board de aprovacao

Arquivo novo:

1. `tests/test_workout_approval_board.py`

Ownership alvo:

1. aprovar
2. rejeitar
3. confirmar mudancas sensiveis
4. filtros
5. resumo rico de revisao
6. diff da revisao
7. trilha de decisao

### 3. Historico publicado e pos-publicacao

Arquivo novo:

1. `tests/test_workout_post_publication_history.py`

Ownership alvo:

1. historico executivo publicado
2. filtros do historico publicado
3. alertas operacionais pos-publicacao
4. follow-up de acoes sugeridas
5. memoria operacional curta

### 4. Governanca semanal

Arquivo novo:

1. `tests/test_workout_weekly_governance.py`

Ownership alvo:

1. checkpoint semanal
2. historico de checkpoint
3. mudanca de ritmo
4. maturidade operacional
5. acao de governanca e leitura executiva semanal

### Contrato de cobertura minima

No alvo final, a suite precisa manter pelo menos:

1. um fluxo ponta a ponta coach -> aprovacao -> publicado
2. um fluxo ponta a ponta alerta -> acao sugerida -> resultado registrado
3. um fluxo ponta a ponta checkpoint -> historico -> leitura de ritmo

## A - Acoes por ondas

## Onda 0 - Inventario e contrato dos testes

### Objetivo

Congelar o mapa atual antes de mover qualquer metodo.

### Acoes

1. listar os testes atuais por ownership
2. marcar quais sao integracao ponta a ponta e quais sao leitura da board
3. definir o arquivo destino de cada teste existente
4. registrar os comandos de baseline:
   - `python manage.py test tests.test_coach_wod_editor`
   - `python manage.py check`

### Mapa inicial recomendado

Mover para `tests/test_coach_wod_editor.py`:

1. `test_coach_workspace_shows_wod_action_for_session`
2. `test_coach_can_create_submit_block_and_movement`
3. `test_coach_can_update_block_and_movement_inline`
4. `test_coach_can_duplicate_workout_to_another_session_as_draft`

Mover para `tests/test_workout_approval_board.py`:

1. `test_manager_can_approve_pending_workout`
2. `test_manager_can_approve_with_optional_decision_reason`
3. `test_manager_must_confirm_sensitive_changes_before_approving`
4. `test_owner_can_reject_pending_workout_with_reason`
5. `test_approval_board_renders_richer_review_summary`
6. `test_approval_board_renders_diff_against_last_published_revision`
7. `test_approval_board_renders_decision_trail_in_timeline`
8. `test_approval_board_filters_sensitive_today_and_coach`

Mover para `tests/test_workout_post_publication_history.py`:

1. `test_approval_board_renders_post_publication_executive_history`
2. `test_approval_board_filters_post_publication_history_by_reason`
3. `test_approval_board_surfaces_post_publication_operational_alerts`
4. `test_manager_can_register_follow_up_result_for_suggested_action`

Mover para `tests/test_workout_weekly_governance.py`:

1. `test_approval_board_surfaces_light_management_alert_for_consistent_improvement`
2. `test_manager_can_register_weekly_management_checkpoint`
3. `test_weekly_checkpoint_history_surfaces_rhythm_changes`

### Check de pronto

1. todo teste atual tem destino definido
2. o time consegue prever onde um teste novo deve nascer

## Onda 1 - Extrair fixture base minima

### Objetivo

Evitar copia cega de setup sem cair em overengineering.

### Direcao

Se a repeticao entre os quatro arquivos for real, extrair somente o minimo para:

1. criacao do box
2. criacao do coach, manager, owner e recepcao quando necessario
3. criacao da aula e da sessao
4. login helper curto

### Regra

So extrair se isso reduzir ruido de verdade.

Se a extracao esconder a leitura:

1. nao extrair

### Check de pronto

1. fixtures compartilhadas sao poucas e legiveis
2. cada teste ainda pode ser lido de cima para baixo sem caca ao tesouro

## Onda 2 - Split do editor e da board

### Objetivo

Separar primeiro a parte mais nitida entre montagem do treino e aprovacao do treino.

### Acoes

1. manter no arquivo original apenas testes de coach editor
2. criar `tests/test_workout_approval_board.py`
3. mover os testes de aprovacao, rejeicao, diff, filtro e revisao
4. garantir que os imports continuam estaveis e sem dependencia circular de helpers

### Check de pronto

1. editar treino nao exige abrir o arquivo da board
2. aprovar treino nao exige abrir o arquivo do editor
3. ambos os arquivos passam sozinhos

## Onda 3 - Split do historico publicado

### Objetivo

Criar o corredor de validacao do que acontece depois da publicacao.

### Acoes

1. criar `tests/test_workout_post_publication_history.py`
2. mover testes de historico, alertas e follow-up
3. manter um smoke integrado que garanta que uma aprovacao realmente gera estado publicado valido

### Check de pronto

1. o historico publicado passa a ter dono tecnico proprio
2. um bug pos-publicacao nao obriga ler o arquivo inteiro do coach

## Onda 4 - Split da governanca semanal

### Objetivo

Separar o corredor executivo semanal da operacao diaria da board.

### Acoes

1. criar `tests/test_workout_weekly_governance.py`
2. mover checkpoint, historico, ritmo e maturidade
3. revisar se o teste de alerta gerencial leve mora melhor aqui ou no historico, conforme o ownership final observado

### Check de pronto

1. governanca semanal vira um assunto proprio
2. a leitura executiva nao fica misturada ao clique de aprovar WOD

## Onda 5 - Higiene final e docs

### Objetivo

Fechar a trilha sem deixar a casa arrumada so pela metade.

### Acoes

1. rodar a suite completa dos quatro arquivos
2. rodar `python manage.py check`
3. atualizar docs de leitura e ownership
4. registrar no topo de cada arquivo qual corredor ele protege

### Check de pronto

1. a arquitetura do codigo e a arquitetura dos testes batem
2. pessoa nova consegue descobrir onde adicionar cobertura sem perguntar

## Critério de aceite

O split so deve ser considerado pronto quando:

1. todos os testes migrarem com comportamento preservado
2. nao existir dependencia de ordem entre arquivos
3. a nomenclatura refletir ownership real e nao moda
4. existir pelo menos um fluxo integrado cobrindo a travessia entre corredores

## Checks de falha

Se qualquer um destes sinais aparecer, a trilha precisa parar e ajustar:

1. um helper compartilhado ficou maior do que varios testes
2. dois arquivos diferentes precisam ser alterados para adicionar um teste simples
3. o mesmo setup complexo foi copiado tres vezes
4. um teste passa sozinho e falha na suite completa, ou o contrario

## Ordem recomendada

1. Onda 0
2. Onda 1
3. Onda 2
4. pausa curta e validacao
5. Onda 3
6. Onda 4
7. Onda 5

## Resumo executivo

Hoje o codigo do WOD ja esta dividido em salas.

Agora precisamos dividir o mapa dos bombeiros tambem.

Em termos tecnicos:

1. a suite monolitica precisa acompanhar o ownership modular
2. a quebra deve ser pequena, reversivel e guiada por comportamento
3. o ganho certo aqui nao e “mais arquivos”
4. o ganho certo e localizar bugs, escrever testes novos e manter confianca com menos atrito
