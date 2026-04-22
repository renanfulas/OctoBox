# Financial Design-System Residual Cleanup C.O.R.D.A.

**Status**: Approved
**Created On**: 2026-03-30
**Approved On**: 2026-03-30
**Decision**: Official north star for the next targeted finance cleanup mountain

## Contexto

O OctoBOX ja consolidou o tema canonico e limpou as ilhas premium mais gritantes.

Depois disso, a vistoria curta mostrou que o centro do problema nao esta mais nas grandes fachadas. O ponto vivo restante esta concentrado no design-system financeiro legado que ainda alimenta partes do workspace financeiro do aluno.

Os dois sinais mais importantes foram:

1. [financial_overview_topbar.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/student_form/financial/financial_overview_topbar.html) ainda usa classes `elite-*`
2. [financial.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/financial.css) ainda usa `var(--elite-accent)` e nomes de classe de uma dinastia visual anterior

Em linguagem simples:

- a casa principal ja usa o novo quadro de energia
- mas um painel tecnico do escritorio ainda esta ligado no quadro antigo

## Objetivo

Limpar o residual vivo do design-system financeiro para que:

1. o workspace financeiro do aluno nao dependa mais de naming `elite-*`
2. `financial.css` deixe de carregar semantica visual de tema paralelo
3. topbar, busca, pills e avatar do contexto financeiro falem a mesma lingua do tema canonico
4. a manutencao futura do financeiro nao herde um mapa visual quebrado

## Riscos

### 1. Risco de mexer em uma peca viva da ficha

O topbar financeiro nao e decoracao.
Ele mistura:

1. leitura contextual
2. busca
3. acoes
4. sinalizacao de status

Se entrarmos sem mapa, podemos deixar a mesa mais bonita e quebrar a gaveta.

### 2. Risco de apagar presenca demais

O financeiro precisa continuar passando seriedade e prioridade.
Se achatarmos tudo, perde-se contraste de importancia.

### 3. Risco de virar refactor infinito

O alvo e residual vivo.
Nao vale abrir agora o financeiro inteiro como se tudo ainda estivesse em crise.

## Direcao

### Regra-mestra

**Absorver o design-system financeiro residual no tema canonico sem matar sua semantica local.**

Traducao pratica:

1. manter host e tokens canonicos
2. trocar naming `elite-*` por semantica local financeira clara
3. preservar a hierarquia da peca
4. deixar o premium como acabamento, nao como idioma-base

### Norte visual

O resultado deve soar como:

1. dark premium aberto
2. painel financeiro serio, mas respiravel
3. cockpit consistente com o restante da ficha

### Norte tecnico

1. reduzir naming legado vivo
2. remover `--elite-*` do residual financeiro tocado
3. aproximar `financial.css` do canon do `css-guide.md`
4. manter HTML, CSS e comportamento previsiveis

## Acoes

## Onda 1. Mapear o residual vivo

Objetivo:
confirmar exatamente quais classes e tokens de `financial.css` ainda alimentam o runtime real.

Inclui:

1. mapear `financial_overview_topbar.html`
2. mapear referencias vivas em `financial.css`
3. separar o que e usado hoje do que ja e codigo morto

## Onda 2. Renomear o host financeiro residual

Objetivo:
tirar o comando principal do workspace financeiro do naming `elite-*`.

Inclui:

1. criar naming semantico local
2. migrar topbar, busca, notificacoes e avatar
3. manter a leitura e densidade operacional

## Onda 3. Retirar pigmento `elite-*` do design-system financeiro

Objetivo:
substituir `--elite-*` residuais e aproximar `financial.css` da semantica canonica.

Inclui:

1. trocar tokens residuais
2. revisar comentarios e cabecalho do arquivo
3. garantir que premium sobreviva apenas como acento

## Onda 4. Passada final de consistencia

Objetivo:
fechar a montanha com um laudo simples e travar o proximo residual, se houver.

Inclui:

1. revisar naming tocado
2. revisar semantica visual
3. classificar o que ficou resolvido e o que sobra
