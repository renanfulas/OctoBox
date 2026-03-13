<!--
ARQUIVO: baseline honesto da Fase 0 da Recepcao dentro da trilha de prontidao do Vertical Sky Beam.

POR QUE ELE EXISTE:
- registra a fotografia fria da Recepcao antes da fase de convergencia estrutural.
- evita que a evolucao da capacidade seja guiada por impressao vaga em vez de diagnostico verificavel.

O QUE ESTE ARQUIVO FAZ:
1. mapeia a capacidade Recepcao na borda visivel e nos corredores tecnicos.
2. aponta descompassos de front e UX.
3. identifica bypasses fora do CENTER e residuos historicos de boxcore.
4. organiza o backlog curto da Fase 1.

TIPO DE DOCUMENTO:
- diagnostico operacional

AUTORIDADE:
- media, subordinada ao contrato da capacidade

DOCUMENTO PAI:
- [reception-module-plan.md](reception-module-plan.md)

QUANDO USAR:
- quando a duvida for onde a Recepcao ainda esta quebrando, o que esta forte e qual backlog curto precisa nascer agora

PONTOS CRITICOS:
- este documento nao existe para provar grandeza; ele existe para revelar onde ainda ha atrito.
- se o baseline for romantizado, a trilha do Beam perde valor e vira apenas narrativa.
-->

# Baseline da Fase 0 da Recepcao

## Regra de autoridade deste documento

1. este baseline mede a Recepcao contra o contrato definido em [reception-module-plan.md](reception-module-plan.md)
2. ele nao cria nova tese para a capacidade
3. se houver conflito entre diagnostico e contrato, o contrato vence e o baseline deve ser atualizado

## Objetivo

Registrar a fotografia fria da Recepcao como capacidade piloto da convergencia entre:

1. front visivel
2. UX de atendimento
3. corredor oficial pelo CENTER
4. reducao de residuos historicos

## Leitura geral

Diagnostico consolidado de hoje:

1. a Recepcao ja existe como capacidade oficial real, nao como preview escondido
2. a superficie principal do balcao esta boa e coerente
3. a jornada completa ainda nao conversa como um unico organismo
4. a capacidade continua espalhada entre workspace, dashboard e catalogo com linguagens diferentes
5. o resíduo publico de `boxcore` dentro da Recepcao e pequeno, mas o resíduo de atalhos e hardcodes ainda e relevante

Resumo curto:

1. a Recepcao ja nasceu
2. ela ainda nao convergiu por inteiro

## Mapa atual da capacidade

### Superficies visiveis

Hoje a Recepcao atravessa estas superficies principais:

1. shell global com navegacao e chips de alerta
2. dashboard adaptado ao papel Recepcao
3. workspace oficial do balcao
4. diretorio de alunos
5. formulario rapido de cadastro e edicao
6. grade de aulas em leitura

Arquivos centrais desta capacidade hoje:

1. [access/context_processors.py](../../access/context_processors.py)
2. [dashboard/dashboard_views.py](../../dashboard/dashboard_views.py)
3. [dashboard/dashboard_snapshot_queries.py](../../dashboard/dashboard_snapshot_queries.py)
4. [templates/dashboard/index.html](../../templates/dashboard/index.html)
5. [operations/workspace_views.py](../../operations/workspace_views.py)
6. [operations/queries.py](../../operations/queries.py)
7. [templates/operations/reception.html](../../templates/operations/reception.html)
8. [operations/action_views.py](../../operations/action_views.py)
9. [catalog/views/student_views.py](../../catalog/views/student_views.py)
10. [templates/catalog/students.html](../../templates/catalog/students.html)
11. [templates/catalog/student-form.html](../../templates/catalog/student-form.html)
12. [catalog/views/class_grid_views.py](../../catalog/views/class_grid_views.py)
13. [templates/catalog/class-grid.html](../../templates/catalog/class-grid.html)

### Corredores tecnicos ativos

Leitura do caminho principal hoje:

1. shell e dashboard ainda entram pela casca HTTP propria de cada modulo
2. workspace da Recepcao entra por `operations/workspace_views.py` e usa facade publica de operations
3. mutacao de pagamento curto entra por `operations/action_views.py`
4. alunos e grade continuam entrando pelas views do catalogo

Conclusao:

1. a Recepcao ja tem um corredor oficial forte no workspace
2. a capacidade inteira ainda nao tem um corredor unico por capacidade

## O que ja esta forte

### 1. Workspace oficial bom

O workspace da Recepcao em [templates/operations/reception.html](../../templates/operations/reception.html) ja sustenta bem a tese do modulo.

Pontos fortes:

1. foco claro em chegada, caixa curto e grade em leitura
2. fronteira funcional visivel
3. linguagem consistente de balcao
4. papel oficial bem marcado

### 2. Papel e navegacao coerentes

O shell global em [access/context_processors.py](../../access/context_processors.py) ja respeita a fronteira principal do papel.

Pontos fortes:

1. Recepcao nao ganha link para o financeiro completo
2. chip financeiro do topo aponta para a fila curta certa
3. dashboard ganha page compass proprio

### 3. Residuo publico de boxcore relativamente baixo

Na capacidade Recepcao, o problema principal ja nao e dependencia difusa de `boxcore` no runtime visivel.

Leitura atual:

1. o modulo ja usa `students.models`, `finance.models` e `operations.models`
2. o corredor do workspace ja passa por [operations/facade/workspace.py](../../operations/facade/workspace.py)
3. o residuo mais forte de `boxcore` continua estrutural e global, nao concentrado na Recepcao

## Onde a capacidade ainda quebra a conversa unica

### 1. A jornada da Recepcao muda de idioma ao sair do workspace

O workspace fala claramente a lingua do balcao.

Mas quando a Recepcao entra em alunos e grade, a experiencia volta a misturar linguagens de atendimento, gerencia e operacao ampla.

Exemplos:

1. [templates/catalog/students.html](../../templates/catalog/students.html) ainda divide fortemente a tela entre recepcao e gerencia no mesmo bloco mental
2. [templates/catalog/student-form.html](../../templates/catalog/student-form.html) continua com linguagem comercial ampla, boa para o sistema, mas nao ainda afinada como fluxo proprio da Recepcao
3. [templates/catalog/class-grid.html](../../templates/catalog/class-grid.html) continua falando em pressao da agenda, recorrencia e admin completo, mesmo quando o papel esta em leitura apenas

Diagnostico:

1. a capacidade tem boa tela principal
2. a jornada completa ainda nao tem um unico idioma

### 2. A capacidade esta espalhada entre tres centros de gravidade

Hoje a Recepcao depende ao mesmo tempo de:

1. dashboard
2. operations
3. catalogo

Isso nao e errado por si so.

O problema e que a capacidade ainda nao tem uma costura suficientemente dominante entre esses pontos.

Sintoma:

1. o usuario sente modulo
2. o codigo ainda sente blocos separados

### 3. Hardcodes de rota ainda estao espalhados

Boa parte da jornada da Recepcao ainda usa caminhos literais em vez de nomes de rota.

Exemplos fortes:

1. [templates/operations/reception.html](../../templates/operations/reception.html)
2. [templates/dashboard/index.html](../../templates/dashboard/index.html)
3. [dashboard/dashboard_views.py](../../dashboard/dashboard_views.py)

Impacto:

1. mexer em rota ou reorganizar superficie custa mais do que deveria
2. a borda depende de strings repetidas em vez de contratos nomeados

### 4. O dashboard da Recepcao esta funcional, mas disperso demais

A adaptacao da Recepcao no dashboard ficou boa para o usuario, mas esta distribuida demais para manutencao barata.

Hoje a logica da capacidade aparece ao mesmo tempo em:

1. [access/context_processors.py](../../access/context_processors.py)
2. [dashboard/dashboard_views.py](../../dashboard/dashboard_views.py)
3. [dashboard/dashboard_snapshot_queries.py](../../dashboard/dashboard_snapshot_queries.py)
4. [templates/dashboard/index.html](../../templates/dashboard/index.html)

Impacto:

1. copy, foco e navegação da Recepcao no dashboard ficaram corretos
2. futuras mudancas ainda vao pedir ida e volta demais entre arquivos

## Bypasses fora do CENTER

### 1. Mutacao de pagamento curto ainda cruza modules direto

Em [operations/action_views.py](../../operations/action_views.py), a acao da Recepcao usa diretamente:

1. `catalog.forms.PaymentManagementForm`
2. `catalog.services.student_payment_actions.handle_student_payment_action`

Diagnostico:

1. a rota e de operations
2. a mutacao ainda depende diretamente de formulario e service do catalogo
3. isso e um bypass aceitavel de transicao, mas ainda nao e o corredor ideal por capacidade

### 2. Dashboard da Recepcao nao entra por uma facade propria da capacidade

O dashboard usa [dashboard/dashboard_views.py](../../dashboard/dashboard_views.py) e [dashboard/dashboard_snapshot_queries.py](../../dashboard/dashboard_snapshot_queries.py) diretamente.

Diagnostico:

1. a experiencia esta boa
2. mas a capacidade Recepcao ainda nao tem entrada publica coesa que una dashboard e workspace num corredor mais claro

### 3. Catalogo ainda serve a Recepcao por compartilhamento, nao por costura dedicada

Em [catalog/views/student_views.py](../../catalog/views/student_views.py) e [catalog/views/class_grid_views.py](../../catalog/views/class_grid_views.py), a Recepcao entrou por ampliacao de permissao e contexto.

Diagnostico:

1. isso resolveu produto rapido com baixo risco
2. ainda nao representa um corredor realmente reancorado pela capacidade Recepcao

## Residuos de boxcore no contexto da Recepcao

### O que pesa pouco hoje

No fluxo principal da Recepcao, nao apareceu dependencia publica forte de `boxcore.models`.

Isso e uma forca do baseline atual.

### O que ainda existe

1. comentarios e cabecalhos antigos ainda citam caminhos historicos em alguns templates do catalogo
2. o admin completo da grade e do cadastro ainda aponta para namespace historico de `boxcore` quando a permissao permite
3. o estado estrutural do Django continua ancorado em `boxcore`, como ja registrado em [../architecture/boxcore-model-state-plan.md](../architecture/boxcore-model-state-plan.md) e [../architecture/boxcore-state-residue-inventory.md](../architecture/boxcore-state-residue-inventory.md)

Diagnostico:

1. na Recepcao, o problema principal ja nao e `boxcore`
2. o problema principal agora e convergencia incompleta entre borda, UX e corredor oficial

## Semaforo da Fase 0

### Front Display Wall da Recepcao

Estado:

1. amarelo forte

Leitura:

1. workspace muito bom
2. jornada completa ainda heterogenea

### UX como regra unica

Estado:

1. amarelo

Leitura:

1. prioridade da tela principal esta clara
2. a logica mental ainda muda demais ao entrar em alunos e grade

### CENTER por capacidade

Estado:

1. amarelo

Leitura:

1. operations esta melhor resolvido
2. dashboard e catalogo ainda entram por costuras menos unificadas

### Esvaziamento de boxcore na capacidade

Estado:

1. verde claro

Leitura:

1. a capacidade ja nao sofre de acoplamento publico bruto a `boxcore`
2. o residuo remanescente e mais estrutural do projeto do que da Recepcao em si

### Manutencao barata

Estado:

1. amarelo forte

Leitura:

1. corrigir a tela principal e relativamente barato
2. corrigir a jornada completa ainda exige tocar modulos demais

## Metricas simples de prontidao

Metricas de baseline propostas para acompanhar a convergencia:

1. numero de arquivos diferentes tocados para uma mudanca simples de copy da Recepcao
2. numero de URLs hardcoded atravessando a jornada da capacidade
3. numero de bypasses diretos fora do corredor oficial da capacidade
4. numero de telas da jornada com linguagem explicitamente afinada ao papel Recepcao
5. tempo medio para corrigir um ajuste pequeno entre dashboard, workspace e catalogo

Leitura inicial qualitativa:

1. arquivos por mudanca simples: ainda acima do ideal
2. hardcodes: ainda acima do ideal
3. bypasses diretos: poucos, mas relevantes
4. telas afinadas ao papel: workspace forte, dashboard bom, catalogo parcial
5. custo de ajuste pequeno: medio

## Backlog curto da Fase 1

### Prioridade 1

1. fechar o contrato de pagina da Recepcao entre dashboard, workspace e catalogo
2. alinhar alunos e grade a uma leitura mais explicitamente orientada ao balcao quando o papel for Recepcao

### Prioridade 2

1. substituir hardcodes principais da jornada da Recepcao por nomes de rota e reverses
2. reduzir a dispersao da logica da Recepcao no dashboard

### Prioridade 3

1. criar um corredor mais limpo para mutacao de pagamento curto sem cruzar operations e catalog por acoplamento direto
2. registrar explicitamente quais bypasses ainda sao transitorios e qual sera o criterio de remocao

### Prioridade 4

1. limpar residuos documentais de caminhos historicos em templates usados pela Recepcao
2. manter o inventario de `boxcore` separado entre estrutural e acoplamento evitavel

## Conclusao fria

A Recepcao ja e uma boa prova de entendimento do negocio e ja sustenta uma superficie oficial digna.

Mas ela ainda nao e a prova de convergencia que o Beam de consagracao exigiria.

Hoje a leitura correta e esta:

1. a capacidade esta viva
2. a tela principal esta forte
3. a jornada completa ainda nao respira como um so organismo
4. a Fase 1 deve atacar unificacao de linguagem, reducao de hardcodes e costura mais clara pelo CENTER