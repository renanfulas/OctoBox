<!--
ARQUIVO: C.O.R.D.A. da refatoracao estrutural do student_app por corredores de view, leitura e escrita.

TIPO DE DOCUMENTO:
- plano arquitetural de refatoracao
- guia operacional por ondas
- contrato curto de prompting para execucao da frente

AUTORIDADE:
- alta para a trilha de refatoracao do student_app

DOCUMENTOS PAIS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [student-access-invite-switch-corda.md](student-access-invite-switch-corda.md)
- [student-app-grade-wod-rm-corda.md](student-app-grade-wod-rm-corda.md)

QUANDO USAR:
- quando a duvida for como desacoplar `student_app/views.py` sem quebrar o runtime
- quando precisarmos organizar home, grade, WOD, RM, onboarding e PWA em corredores mais claros
- quando quisermos executar a refatoracao por ondas pequenas com testes e sem teatro arquitetural

POR QUE ELE EXISTE:
- evita que o app do aluno cresca como um arquivo unico cada vez mais caro de manter
- protege a direcao oficial do projeto: `views` finas, leitura e escrita separadas, fronteiras claras por capacidade
- cria um trilho unico para arquitetura, front-end e performance trabalharem na mesma lingua

O QUE ESTE ARQUIVO FAZ:
1. registra a fotografia atual do `student_app`
2. define a arquitetura-alvo de views por corredor
3. organiza a migracao por ondas pequenas
4. documenta guardrails de performance e ownership visual
5. entrega um contrato de prompt para executar a frente sem ruido

PONTOS CRITICOS:
- essa frente nao e reescrita; e evolucao controlada
- a compatibilidade de URLs precisa ser preservada durante a transicao
- `public workouts` nao devem continuar contaminando a fronteira do app autenticado por muito tempo
- `views` nao devem virar novo deposito de regra que deveria morar em queries, workflows ou use cases
-->

# C.O.R.D.A. - Refatoracao estrutural do `student_app`

## C - Contexto

Hoje o `student_app` ja saiu da fase de prototipo.

Ele ja carrega:

1. identidade propria do aluno
2. convite contextual por box
3. membership por box
4. `primary_box`
5. `active_box`
6. `switch box`
7. grade, WOD, RM e configuracoes
8. onboarding do aluno
9. PWA online-first
10. `manifest`, `sw.js`, `offline`
11. links publicos de treino

O problema estrutural e que boa parte disso ainda passa por um unico arquivo:

1. [student_app/views.py](../../student_app/views.py)

Fotografia atual:

1. o arquivo tem mais de 1000 linhas
2. mistura superfices autenticadas e superfices publicas
3. mistura onboarding e uso recorrente do app
4. mistura concerns de tela, runtime de sessao e concerns de PWA
5. dificulta ownership tecnico, revisao e tuning de performance

Em linguagem simples:

1. a casa do aluno cresceu
2. mas ainda tem cozinha, oficina, recepcao e caixa d'agua no mesmo comodo

### Leitura arquitetural oficial aplicada aqui

Pelos docs-mae do projeto:

1. o OctoBox deve crescer como `modular monolith`
2. a interface web deve ser fina
3. o core conceitual deve viver em capacidades, casos de uso, facades e snapshots
4. a borda HTTP nao deve concentrar regra mutavel demais

Traducao pratica para esta frente:

1. `student_app/views.py` nao precisa ser demolido
2. mas precisa deixar de ser o corredor central de quase tudo

## O - Objetivo

Refatorar o `student_app` para uma arquitetura por corredores, mantendo comportamento identico no runtime e abrindo espaco seguro para crescimento futuro.

### Sucesso significa

1. `views` do aluno ficam separadas por responsabilidade real
2. `urls` continuam estaveis durante a transicao
3. onboarding, shell autenticado e PWA deixam de disputar o mesmo arquivo
4. o custo de adicionar novas features cai
5. o tuning de performance por corredor fica mais obvio
6. o front-end do aluno ganha ownership visual mais limpo
7. `public workouts` ficam mais proximos de uma superficie propria

### Nao e objetivo desta frente

1. reescrever o app do aluno do zero
2. migrar modelos de forma agressiva
3. trocar a experiencia do usuario nesta mesma onda
4. inventar microservices
5. formalizar CQRS completo onde ainda nao ha necessidade

## R - Riscos

### 1. Risco de mover bagunca de lugar

Se apenas quebrarmos um arquivo grande em varios arquivos sem regra de ownership:

1. o projeto fica com mais pastas
2. mas com a mesma confusao

### 2. Risco de criar arquitetura teatral

Se introduzirmos `queries`, `workflows` e `adapters` em todo lugar antes da hora:

1. o time ganha cerimônia
2. sem ganhar clareza real

### 3. Risco de quebrar URLs durante a obra

Se rotas forem alteradas cedo demais:

1. testes e links internos podem quebrar
2. o rollout da refatoracao fica mais caro que o ganho

### 4. Risco de misturar app autenticado e conteudo publico

Se `public workouts` continuarem crescendo dentro da mesma fronteira do app autenticado:

1. PWA publico e PWA autenticado ficam acoplados
2. a explicacao do dominio fica confusa

### 5. Risco de performance piorar com a refatoracao

Se a obra gerar recomposicao repetida de contexto ou mais queries por tela:

1. a arquitetura fica mais bonita
2. mas o produto fica mais lento

Regra oficial do predio:

1. se ficar mais bonito e mais lento, piorou

## D - Direcao

### Tese central

O `student_app` deve crescer como um conjunto de corredores explicitamente separados:

1. shell autenticado do aluno
2. onboarding
3. membership e estados excepcionais
4. PWA
5. conteudo publico de treino

### Frases de arquitetura

1. `views` devem ser finas e organizadas por capacidade.
2. `queries` entram quando a leitura ficar densa ou repetida.
3. `workflows` entram quando a escrita ganhar regra, side effect ou auditoria.
4. `public workout` nao deve disputar ownership com o shell autenticado do aluno.
5. compatibilidade primeiro; embelezamento depois.

### Estrutura-alvo

```text
student_app/
  views/
    __init__.py
    base.py
    shell_views.py
    onboarding_views.py
    membership_views.py
    pwa_views.py
    public_workout_views.py
  queries/
    __init__.py
    student_shell_queries.py
    student_membership_queries.py
    student_rm_queries.py
  workflows/
    __init__.py
    attendance_workflows.py
    onboarding_workflows.py
    student_rm_workflows.py
```

### Ownership-alvo por corredor

#### `views/base.py`

Responsavel por:

1. mixins de identidade do aluno
2. leitura de sessao/cookie
3. shell context compartilhado

Nao deveria carregar:

1. regras de onboarding
2. logica de PWA
3. HTML publico de treino

#### `views/shell_views.py`

Responsavel por:

1. `StudentHomeView`
2. `StudentGradeView`
3. `StudentWodView`
4. `StudentRmView`
5. `StudentSettingsView`
6. `StudentConfirmAttendanceView`

#### `views/onboarding_views.py`

Responsavel por:

1. `StudentOnboardingWizardView`
2. helpers de conclusao do onboarding

#### `views/membership_views.py`

Responsavel por:

1. `StudentInviteEntryView`
2. `StudentSwitchBoxView`
3. `StudentMembershipPendingView`
4. `StudentSuspendedFinancialView`
5. `StudentNoActiveBoxView`

#### `views/pwa_views.py`

Responsavel por:

1. `StudentManifestView`
2. `StudentServiceWorkerView`
3. `StudentOfflineView`

#### `views/public_workout_views.py`

Responsavel por:

1. `PUBLIC_WORKOUT_LIBRARY`
2. `manifest` e `offline` publicos do treino se continuarem no mesmo app
3. renderizacao dos links `/renan/...`

### Queries e workflows

#### Introduzir agora

1. apenas onde a regra ja estiver ficando repetida ou densa
2. sem fanatismo de pattern

#### Candidatos naturais

1. `attendance_workflows.py`
   - confirmar presenca
   - reativar reserva cancelada/ausente
2. `onboarding_workflows.py`
   - completar onboarding importado
   - completar onboarding em massa
3. `student_shell_queries.py`
   - montar shell/runtime leve do aluno quando a leitura comecar a repetir

#### Nao introduzir cedo demais

1. abstractions vazias
2. classes de service so para “parecer arquitetura”

### Direcao de front-end e CSS

Pela lente de front-end:

1. cada corredor de view deve apontar para templates e assets mais legiveis
2. onboarding, shell do aluno e superficie publica nao devem compartilhar CSS sem contrato
3. a fronteira visual deve seguir o ownership da experiencia

Traducao pratica:

1. `student_app/rm.html` e telas do shell autenticado continuam no mesmo eixo visual
2. telas publicas e PWA de treino podem ter assets separados quando o custo justificar

### Direcao de performance

Pela lente de performance:

1. a refatoracao nao pode aumentar o numero de queries
2. mixins de base nao devem recomputar runtime de sessao varias vezes por request
3. leituras densas devem caminhar para `queries/`
4. PWA publico e app autenticado devem ficar mais faceis de otimizar separadamente

Metas qualitativas:

1. nenhuma regressao de query count nos fluxos cobertos
2. nenhum aumento visivel de latencia na home, grade ou WOD
3. menos atrito para cachear por superficie no futuro

## A - Acoes

### Onda 0 - Inventario e cinturão de segurança

Objetivo:

1. preparar a obra sem mover parede estrutural cedo demais

Acoes:

1. mapear as views atuais do `student_app`
2. mapear rotas e templates usados por cada uma
3. identificar testes existentes que cobrem esses circuitos
4. adicionar smoke tests ausentes antes de mover codigo sensivel

Criterio de pronto:

1. sabemos exatamente o que cada grupo de views faz hoje
2. temos cobertura minima dos fluxos criticos

### Onda 1 - Extrair base

Objetivo:

1. tirar do arquivo central o que e fundamento compartilhado

Acoes:

1. criar `student_app/views/base.py`
2. mover mixins e helpers de sessao/identidade
3. manter imports de compatibilidade temporarios

Criterio de pronto:

1. nenhuma rota muda
2. nenhum comportamento muda
3. o arquivo central fica menor sem deslocar regra para lugar errado

### Onda 2 - Extrair shell autenticado

Objetivo:

1. separar o uso recorrente do aluno do resto da obra

Acoes:

1. mover `Home`, `Grade`, `WOD`, `RM`, `Settings` e `ConfirmAttendance`
2. ajustar `student_app/urls.py` para importar do novo corredor
3. preservar nomes das rotas

Criterio de pronto:

1. o shell autenticado vive em corredor proprio
2. URLs e templates continuam respondendo igual

### Onda 3 - Extrair onboarding e membership states

Objetivo:

1. separar entrada do aluno de uso recorrente do app

Acoes:

1. mover onboarding para `onboarding_views.py`
2. mover pending/suspended/no_active_box/invite/switch para `membership_views.py`

Criterio de pronto:

1. quem entra no app e quem usa o app nao disputam mais o mesmo arquivo

### Onda 4 - Extrair PWA

Objetivo:

1. separar concerns de entrega offline da experiencia autenticada

Acoes:

1. mover `manifest`, `sw.js` e `offline`
2. manter URLs identicas

Criterio de pronto:

1. concerns de PWA saem do corredor do produto autenticado

### Onda 5 - Separar superficie publica de treino

Objetivo:

1. deixar explicito que treino publico e um corredor proprio

Acoes:

1. mover helpers e views de `/renan/...` para `public_workout_views.py`
2. manter `public_urls.py` ou rota dedicada se ajudar a leitura

Criterio de pronto:

1. o shell autenticado do aluno nao carrega mais ownership direto da superficie publica

### Onda 6 - Queries e workflows onde fizer sentido

Objetivo:

1. reduzir densidade de regra nas views sem dogmatismo

Acoes:

1. extrair `attendance_workflows.py`
2. extrair `onboarding_workflows.py`
3. extrair queries apenas se a leitura de shell/runtime repetir ou ficar pesada

Criterio de pronto:

1. a separacao melhora clareza e testabilidade
2. nao introduz ceremony sem ganho real

## Contrato de execucao

### Regra de ouro

1. refatorar sem quebrar contrato publico
2. mover comportamento antes de redesenhar comportamento
3. medir antes e depois

### Ordem de validacao por onda

1. testes do circuito
2. smoke manual de rota
3. revisao de imports
4. revisao de templates e assets tocados
5. revisao de query count nas telas quentes quando aplicavel

## Prompt Spec da frente

### Objetivo

Refatorar o `student_app` por corredores de responsabilidade mantendo comportamento identico durante a transicao.

### Inputs

1. runtime atual
2. docs canonicos de arquitetura
3. testes existentes
4. este C.O.R.D.A.

### Nao objetivos

1. reescrever UX
2. mudar models
3. trocar rotas publicas
4. criar camadas abstratas sem necessidade

### Constraints

1. manter compatibilidade
2. preferir evolucao incremental
3. nao aumentar acoplamento invisivel
4. nao piorar performance

### Output contract

Cada onda deve entregar:

1. arquivos criados/movidos
2. comportamento preservado
3. risco principal da onda
4. validacao executada

## Prompt operacional reutilizavel

Use este prompt nas proximas ondas desta frente:

```md
Voce esta executando a frente `student-app-views-refactor-corda`.

Objetivo:
Refatorar o `student_app` por corredores de responsabilidade, preservando comportamento, URLs e experiencia atual.

Contexto:
- O projeto segue a tese de `modular monolith`.
- `views` devem ser finas e organizadas por capacidade.
- O arquivo `student_app/views.py` esta centralizado demais.
- Esta onda deve seguir o C.O.R.D.A. `docs/plans/student-app-views-refactor-corda.md`.

Escopo desta execucao:
- [descreva aqui a onda atual]

Constraints:
- nao reescrever do zero
- nao mudar rotas publicas sem necessidade explicitamente aprovada
- nao criar abstractions vazias
- nao piorar query count ou latencia de forma perceptivel
- manter foco em compatibilidade

Entrega obrigatoria:
1. mudancas de codigo
2. riscos da onda
3. validacao executada
4. observacoes de debito tecnico evitado ou criado
```

## Failure checks da frente

Antes de considerar uma onda pronta, verificar:

1. a mudanca apenas espalhou codigo ou criou ownership real?
2. alguma rota mudou sem necessidade?
3. alguma tela ficou mais lenta?
4. onboarding e shell continuam separados?
5. concerns publicos continuam contaminando o autenticado?
6. algum novo arquivo virou deposito central de regra?

## Criterio final de sucesso

Ao final da frente:

1. `student_app/views.py` deixa de ser o corredor central de tudo
2. o time consegue localizar ownership por capacidade em poucos segundos
3. futuras features do aluno entram no corredor certo com menos risco
4. a base fica mais pronta para evolucao mobile, API e tuning de performance
