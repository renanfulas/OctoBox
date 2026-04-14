<!--
ARQUIVO: sistema operacional de GitHub do OctoBox.

TIPO DE DOCUMENTO:
- guia operacional de repositorio

AUTORIDADE:
- alta para branches, commits, PRs, merge e limpeza de repositorio

DOCUMENTO PAI:
- [../../README.md](../../README.md)

DOCUMENTOS IRMAOS:
- [reading-guide.md](reading-guide.md)
- [../plans/scale-transition-20-100-open-multitenancy-plan.md](../plans/scale-transition-20-100-open-multitenancy-plan.md)
- [../rollout/first-box-production-execution-checklist.md](../rollout/first-box-production-execution-checklist.md)

QUANDO USAR:
- quando a duvida for como abrir branch, commitar, abrir PR, mergear e limpar o repositorio
- quando o time estiver se perdendo em branch velha, PR grande e historico confuso

PONTOS CRITICOS:
- este documento deve ficar simples o bastante para ser seguido sob pressao
- se ele ficar bonito demais e impraticavel, vira enfeite e nao sistema operacional
-->

# GitHub Operating System do OctoBox

## Objetivo

Dar ao OctoBox uma forma simples, repetivel e segura de trabalhar no GitHub sem se perder em:

1. branch fantasma
2. commit sem contexto
3. PR monstro
4. merge barulhento
5. sujeira de bancada

Em linguagem simples: este documento e a regra da oficina. Cada ferramenta volta para o lugar depois de ser usada.

## Filosofia oficial

O OctoBox deve operar com:

1. `main` protegida
2. branches curtas
3. PRs pequenas
4. merge rapido
5. delete imediato da branch depois do merge

Modelo recomendado:

1. `trunk-based development`
2. nao usar `git flow` pesado

## Regra 1 - a main e sagrada

Na `main`:

1. nao trabalhar direto
2. nao empilhar experimento
3. nao deixar check quebrado
4. nao fazer push bruto sem necessidade real

## Convencao oficial de branch

Usar prefixos curtos e explicitos:

1. `feat/`
2. `fix/`
3. `docs/`
4. `ops/`
5. `refactor/`
6. `chore/`
7. `codex/` para trabalho guiado pelo agente quando isso fizer sentido

Formato recomendado:

1. `tipo/area-resumo-curto`

Exemplos:

1. `feat/owner-workspace-kpi`
2. `fix/reception-payment-fragment`
3. `docs/phase1-endorfina-onboarding`
4. `ops/ci-postgres15`

## Regra 2 - 1 branch = 1 assunto

Toda branch deve nascer para um objetivo unico.

Exemplos ruins:

1. `melhorias-gerais`
2. `ajustes-finais`
3. branch que mistura UI, infra, docs e cleanup ao mesmo tempo

## Regra 3 - branch curta ou branch errada

Meta de duracao:

1. ideal: `1 a 2 dias`
2. aceitavel: `3 a 5 dias`
3. acima disso: revisar, quebrar ou rebasear

Meta de tamanho:

1. ideal: `5 a 20 arquivos`
2. aceitavel: pequena o suficiente para revisao humana em poucos minutos

## Convencao oficial de commit

Usar commits claros e orientados a objetivo.

Formato recomendado:

1. `feat: ...`
2. `fix: ...`
3. `docs: ...`
4. `ops: ...`
5. `refactor: ...`
6. `test: ...`
7. `chore: ...`

## Regra 4 - toda PR precisa caber na cabeca

Toda PR deve responder:

1. o que muda
2. por que muda
3. como foi validado
4. qual e o risco

## Tipos oficiais de PR

Classificar cada PR principalmente como:

1. `feature`
2. `fix`
3. `ops`
4. `docs`
5. `refactor`

E opcionalmente marcar trilha principal:

1. `frontend`
2. `backend`
3. `infra`
4. `rollout`

## Regra 5 - validacao minima antes de abrir PR

Sempre que couber, rodar localmente:

1. `py manage.py check`
2. testes do circuito alterado
3. smoke do fluxo principal, se mexeu em UI critica
4. evidencias ou runbook, se mexeu em rollout ou infra

## Regra 6 - merge padrao

Padrao recomendado:

1. `squash merge` para PR comum
2. `merge commit` so quando houver valor real em preservar a historia da branch

Objetivo:

1. a `main` precisa parecer um livro
2. nao um grupo de chat com 17 mensagens nervosas

## Regra 7 - delete automatico da branch

Depois do merge:

1. apagar branch local
2. apagar branch remota
3. nao deixar branch fantasma na prateleira

## Regra 8 - branch de bancada nao e branch de entrega

Branches como:

1. `integration-*`
2. `merge-prep-*`
3. `rollback-drill-*`
4. `clean-*`

devem ser lidas como:

1. bancada
2. ensaio
3. oficina

## Regra 9 - o que nao pode entrar no Git por acidente

Evitar commitar:

1. `tmp/`
2. screenshot solta
3. dump
4. `.env`
5. backup local
6. arquivo de debug temporario
7. relatorio gerado so para investigacao curta

## Regra 10 - limpar toda semana

Ritual semanal curto:

1. revisar branches locais
2. revisar branches remotas
3. apagar branch ja absorvida
4. apagar branch de bancada encerrada
5. verificar worktrees esquecidas
6. verificar arquivos nao rastreados fora de tarefa ativa

## Fluxo semanal recomendado

### Segunda

1. alinhar prioridades da semana
2. decidir quais mudancas viram branch

### Durante a semana

1. abrir branch curta
2. implementar 1 assunto
3. validar localmente
4. abrir PR
5. revisar e mergear rapido

### Sexta

1. limpar branch ja absorvida
2. revisar worktrees
3. revisar arquivos soltos
4. deixar `main` limpa para a proxima semana

## Labels recomendadas

Poucas e fortes:

1. `feature`
2. `fix`
3. `ops`
4. `docs`
5. `frontend`
6. `backend`
7. `infra`
8. `risk:low`
9. `risk:medium`
10. `risk:high`
11. `size:S`
12. `size:M`
13. `size:L`

## Formula curta

O GitHub do OctoBox deve funcionar assim:

1. abrir pouco
2. fechar rapido
3. documentar o suficiente
4. limpar sempre

Porque repositorio complexo sem metodo vira garagem com ferramenta no chao: da para andar por um tempo, ate alguem tropeçar.
