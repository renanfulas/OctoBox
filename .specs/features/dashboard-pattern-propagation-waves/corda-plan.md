# Dashboard Pattern Propagation Waves C.O.R.D.A.

**Status**: Approved
**Created On**: 2026-04-05
**Decision**: North star para a propagacao por ondas dos padroes do dashboard

## Contexto

O dashboard virou a principal vitrine do OctoBox e validou uma combinacao forte de:

1. hero mais premium e mais controlado
2. shell com atmosfera melhor calibrada
3. command workspace com hierarquia clara
4. cards com mais presenca sem perder leitura

Ao mesmo tempo, nem tudo o que existe no dashboard deve ser copiado diretamente.

Em linguagem simples:

1. algumas pecas viraram molde de fabrica
2. outras ainda sao roupa sob medida
3. se copiarmos tudo igual, espalhamos risco

## Objetivo

Organizar a replicacao do dashboard em ondas para que:

1. shared venha antes de local
2. cada familia de paginas receba o que faz sentido para seu papel
3. a identidade Luxo Futurista 2050 avance sem reabrir caos no CSS

## Restricoes

1. nao copiar markup local do dashboard como regra geral
2. nao promover uma tela para escopo premium sem hierarquia madura
3. nao usar glow ou atmosfera como substituto de estrutura
4. toda onda deve respeitar os skills `octobox-design` e `CSS Front end architect`
5. toda pagina tocada deve sair mais facil de manter do que entrou

## Definition of Done

O trabalho estara bem encaminhado quando:

1. houver uma ordem oficial de ondas
2. cada onda tiver escopo, risco e criterio de pronto
3. o shared estiver claramente separado do local
4. a execucao tiver checklist e prompt operacional repetivel
5. o plano estiver espelhado em `docs/plans`

## Auditoria

1. identificar o que no dashboard ja virou host ou variante reutilizavel
2. separar o que ainda e local do dashboard
3. classificar as paginas por familias de migracao
4. validar risco de regressao por onda

## Direcao

### Regra-mestra

**Primeiro promover o que virou componente compartilhado. Depois adaptar cada superficie local.**

### Norte tecnico

1. `tokens.css` manda na tinta
2. hosts canonicos mandam na familia visual
3. variantes oficiais mandam na personalidade recorrente
4. CSS local manda no layout e na composicao

### Norte operacional

1. uma onda nao deve tocar paginas muito diferentes sem necessidade
2. cada onda deve ter uma pagina ancora
3. depois da pagina ancora validada, a familia irma pode receber o mesmo padrao

## Ondas

### Onda 1. Foundation Shared

Objetivo:
promover o que o dashboard revelou como reutilizavel.

### Onda 2. Catalog Core

Objetivo:
aplicar os padroes compartilhados em `students`, `finance`, `finance-plan-form` e `class-grid`.

Status operacional:

1. `students` estabilizada
2. `finance-plan-form` estabilizada
3. `class-grid` estabilizada
4. `finance` reclassificada como pendencia manual

Decisao:

1. a Onda 2 fecha como concluida para o catalogo validado
2. `finance` nao bloqueia a continuidade do rollout
3. futuras decisoes em `finance` devem acontecer em trilha manual propria

### Onda 3. Operations Roles

Objetivo:
aplicar o padrao nas superficies de `manager`, `reception`, `coach` e `dev`.

 Entrada pronta:

 1. usar `owner` como ancora visual oficial da familia operacional
 2. iniciar a execucao por `manager`
 3. revisar hero, leitura inicial e workspace da role antes de replicar
 4. seguir para `reception`, `coach` e `dev` em ordem
 5. registrar qualquer excecao forte como local, nao como shared
 6. `owner` empresta linguagem compartilhada, nao markup cego nem regras de telas isoladas

 Status de fechamento da Onda 3:

 1. `manager` confirmou a entrada da familia operacional
 2. `reception` foi corrigida depois da inspecao visual para voltar ao ritmo de balcao curto
 3. `coach` permaneceu coerente com a familia sem perder a composicao do turno
 4. `dev` foi corrigida depois da inspecao visual para parar de expor payload cru e voltar a leitura humana
 5. `owner` fica oficializada como ancora visual da familia operacional desta onda

### Onda 4. Special Cases

Objetivo:
tratar paginas hibridas, especiais ou mais sensiveis.

Triagem oficial:

1. heranca controlada da familia principal:
   `reports-hub`, `access-overview`
2. isolamento local explicito:
   `whatsapp-placeholder`, `system-map`, `operational-settings`

Regra de execucao:

1. entrar por `reports-hub` como caso especial mais proximo da familia operacional
2. tratar `access-overview` como heranca controlada de governanca
3. tratar `whatsapp-placeholder` como limpeza de placeholder e remocao de inline CSS
4. tratar `system-map` e `operational-settings` como superficies de guia com semantica propria

Primeiro movimento da onda:

1. `reports-hub` foi executado como heranca controlada da familia principal
2. a tela agora usa hero, reading lane e mesa lateral no idioma da `owner`
3. a composicao continua local e preserva o carater de cofre gerencial
4. `access-overview` foi executada como heranca controlada de governanca
5. a tela agora usa hero, reading lane e faixa lateral da familia principal sem virar admin disfarçado
6. `whatsapp-placeholder` foi saneada como placeholder consciente
7. a tela saiu do inline CSS, mas permanece isolada e descartavel

### Onda 5. Polish and Validation

Objetivo:
fechar dark/light, responsividade, limpeza residual e smoke final.
