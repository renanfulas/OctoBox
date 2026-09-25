<!--
ARQUIVO: plano cirúrgico pra corrigir hierarquia visual e comparabilidade do
gráfico de evolução de carga da Curva, antes das 3 frentes seguintes (visão
de ciclo, celebração de PR, card compartilhável).

TIPO:
- plano de produto e UI, recorte pequeno e sequencial

STATUS:
- aprovado para implementação (Revisão 8). Revisão 8 caçou regressões
  reais (o que o plano QUEBRA que hoje funciona, não só o que ele corrige)
  e achou duas: (a) `record_load()` virando obrigatório pra `set_role`
  quebraria ~30 chamadas diretas de teste existentes que não têm nada a
  ver com o assunto — resolvido com default só na função (nunca no model,
  nunca na view, que sempre passa valor explícito); (b) os 10 alunos reais,
  tendo todo histórico como `legacy_unknown`, perdem a sugestão de carga
  mais personalizada e a aba de recorde fica vazia no dia do deploy —
  efeito colateral real e temporário (autolimitado, some assim que cada
  aluno registrar de novo), documentado como aviso operacional pro Renan/
  Giovanna antes do PR 2, não como bug a esconder ou corrigir escondendo a
  classificação `legacy_unknown`. Revisão 7 é auto-revisão (sem
  input externo) caçando especificamente o MESMO tipo de gap que as
  rodadas anteriores corrigiram — outro consumidor escondido, ou duas
  computações "gêmeas" podendo divergir. Achou: (a) `todays_logged_weight`
  tinha sido classificado errado nas Revisões 4-6 como precisando do fix
  de elegibilidade — leitura completa do corpo da função mostrou que isso
  causaria regressão de UX real (mostraria valor diferente do que o aluno
  acabou de salvar); reclassificado pra fora de escopo. (b) `week_overview`
  (`public_workouts_extras.py:93`) é um consumidor real de `load_history`
  que nenhuma rodada anterior tinha listado — confirmado como
  corretamente fora de escopo (sinal de presença, não progresso), mas
  precisava estar documentado, não só assumido. (c) `weekly_review_ai.py`
  foi verificado por leitura completa (não suposição) e confirmado
  genuinamente livre de contaminação. Revisão 5 foi auto-revisão que
  achou um bug de sequenciamento e completou especificidade vaga. Revisão 6
  incorpora uma 4ª revisão externa que achou o **bug residual mais grave
  do plano até aqui**: `movement_load_display` tinha uma segunda busca de
  log bruto (`_last_log_for_movement`, linha 599) alimentando o caminho de
  sugestão de carga MAIS comum (fase canônica ativa) — não se corrigia "de
  graça" como a Revisão 4 afirmava. Também corrigiu: dedup por dia
  duplicada divergindo entre curva e tendência semanal (unificada em
  `effective_top_sets_by_day`, compartilhada); um `raise` que relançava a
  exceção errada dentro de except aninhado; sequenciamento que deixava
  `NULL` invisível se acumular entre PR 1 e PR 2 (escritor compatível
  movido pro PR 1); contagem real de migrations (3, com `CheckConstraint`
  intermediário) e preservação do índice existente; `progress_snapshot.py`
  virou batch por conta (evita N+1 numa tela com múltiplos movimentos) com
  DTO neutro (evita import circular com `services.py`); janela de 90 dias
  aplicada também ao histórico legado no gráfico (não só na curva); escala
  vertical com padding pra série plana; tendência exigindo frescor, não só
  consecutividade. §9 ganhou `training_session_id`/`captured_at_client`
  como a sofisticação futura mais valiosa (não Window function).

  Histórico: Revisão 2 incorporou correção externa que expôs contaminação
  real já existente hoje em produção (não
  hipotética) e dois problemas de honestidade visual que a Revisão 1 não
  cobria (eixo temporal, escala por gráfico). Revisão 3 incorporou 5
  ajustes (enum de `set_role`, política por finalidade, protocolo de
  payload sem `set_role`, tratamento visual do histórico legado, escopo do
  agrupamento por dia). Revisão 4 incorpora uma 3ª revisão externa que
  expandiu o mapa de consumidores de 2 para 7 pontos reais
  (`build_student_package`/badge de `workout.html`, `personal_record`,
  `todays_logged_weight`, sugestão de carga), corrigiu a regra de
  agrupamento (mais recente por `created_at`, não maior peso — preservava
  erro de correção), separou `progress_eligibility.py` (predicado puro) de
  `progress_snapshot.py` (única leitura de ORM), corrigiu a sequência de
  migration (nunca `default=` no field), fechou um mascaramento de erro em
  `record_load`, exigiu semanas consecutivas na tendência, e adicionou o
  bump de `PUBLIC_WORKOUT_CACHE_EPOCH` ao rollout do PWA.

AUTORIDADE:
- alta para este recorte específico (gráfico de carga do corredor Curva)

DOCUMENTOS RELACIONADOS:
- docs/plans/public-workouts-go-to-market-plan.md (o gráfico como ativo de marca)
- docs/plans/curva-grafico-hierarquia-e-set-role-overview.md (estado implementado, revisão, riscos e próximos passos para continuidade)
- branch local codex/curva-carga-real-plan, arquivo
  docs/plans/curva-carga-real-product-architecture.md — regras de
  comparabilidade (§4.3) e critério de PR (§5.3) usadas aqui; a arquitetura
  de app `curva/` paralelo dessa branch NÃO é adotada — ver nota no §0.

REGRA DE FRONTEIRA:
- Este plano estende `public_workouts.PublicWorkoutLoadLog` e os
  consumidores já existentes (`load_chart_points`, `one_rep_max.py`). Não
  cria modelo, app ou auth paralelos.
-->

# Curva — hierarquia visual do gráfico + separação por set_role

## Decisão em uma frase

O número que prova evolução precisa ser o elemento mais confiante da tela, a
linha do gráfico só pode comparar séries do mesmo tipo e no mesmo ritmo real
de tempo, e **essa regra de elegibilidade só pode existir em um lugar do
domínio** — nunca duplicada por consumidor.

## 0. Por que este recorte vem antes dos outros três

As tasks de visão de ciclo, celebração de PR e card compartilhável (ver
tracker desta sessão) todas leem o mesmo dado de carga. Se a linha continuar
misturando aquecimento com série principal, qualquer "resumo de evolução",
"recorde" ou "card pra compartilhar" construído em cima disso carrega o
mesmo erro pra frente. Corrigir aqui primeiro é mais barato que corrigir
três vezes depois.

## 1. Problema 1 — hierarquia visual (só CSS/HTML, sem mudança de dado)

Hoje, em [`workout-shell.css:737`](../../static/css/public_workouts/workout-shell.css):

```css
.workout-load-chart-current strong {
    font-size: 1.05rem;
    color: var(--brand);
}
```

O peso atual — o número que representa "eu evoluí desde o início" — tem o
mesmo peso visual que qualquer legenda secundária da tela. No mesmo cabeçalho
([`workout.html:384-408`](../../templates/public_workouts/workout.html))
competem, com destaque parecido: nome do movimento, peso atual + tendência,
badge de 1RM estimado, badge de sinal (platô/evolução/queda). Nada domina.

### Mudança proposta

1. `.workout-load-chart-current strong` sobe pra escala responsiva grande
   (~2.2-2.6rem como ponto de partida, ajustar contra tela real de 360px),
   peso 700+, "kg" tratado como unidade claramente secundária (menor, ao
   lado, não competindo em tamanho com o número).
2. Badge de 1RM e badge de sinal descem de posição visual — viram uma linha
   secundária, menor, abaixo do número hero, não mais no mesmo eixo dele.
   Ganham rótulo de ação ("Ver detalhes") em vez de aparecer como dado
   pronto, deixando claro que são contexto, não o fato principal.
3. `workout-load-chart-siblings` (pills de variação de exercício) — hoje
   sempre visível — passa a ficar colapsado por padrão (toggle "Ver
   variações"), porque é ação secundária competindo com o momento principal.
4. Uma frase curta e determinística entre o número e o gráfico bruto (ex.:
   "Sua série principal está evoluindo com consistência") — só pode ser
   gerada a partir do MESMO sinal de tendência centralizado do §2.2, nunca
   uma string calculada em separado só pra esse lugar.
5. Nenhuma mudança de estrutura de dado nos itens 1-3; é reordenação/
   retipografia do que já existe.

## 2. Problema 2 — nenhuma comparabilidade real, e a contaminação já está em produção hoje

### 2.1 A linha mistura séries não-comparáveis

`load_chart_points` ([`public_workouts_extras.py:374`](../../public_workouts/templatetags/public_workouts_extras.py:374)):

```python
weighted = [entry for entry in entries if entry.get('weight_kg') is not None]
```

Todo registro com peso preenchido entra na mesma linha — aquecimento, feeder
set e série principal ficam indistinguíveis. `PublicWorkoutLoadLog`
([`models.py:1121`](../../public_workouts/models.py:1121)) não tem nenhum
campo que diga qual dos três um registro é.

### 2.2 A contaminação não é hipotética — já existe, hoje, sem eu mudar nada

`one_rep_max.py::_weekly_best_estimates` (linha 161) lê **todo** registro do
movimento sem filtro de tipo e pega o maior 1RM estimado da semana:

```python
logs = PublicWorkoutLoadLog.objects.filter(account_id=account_id, movement_slug=movement_slug).order_by('performed_on')
for log in logs:
    estimate = estimate_one_rep_max(weight_kg=log.weight_kg, reps=log.reps, rir=log.rir)
    if estimate.value_kg > best_by_week[week]:
        best_by_week[week] = estimate.value_kg
```

Um aquecimento leve com RIR alto pode facilmente estimar (via Brzycki) um
1RM mais alto que a série principal fatigada da mesma semana. Esse número
contaminado é exatamente o que alimenta o badge "1RM est." e o sinal
"Em evolução / Platô / Em queda" (`trends_by_movement`) — hoje, em produção,
para os alunos reais. **Corrigir só `load_chart_points` deixaria o gráfico
limpo e o badge do lado dele continuando a mentir.**

### Mudança proposta — dois módulos: predicado puro + montagem do snapshot

**Por que dois módulos, não um.** `load_chart_points` e `personal_record`
(ver mapa completo abaixo) recebem **dicts serializados**
(`services.py::_serialize_load_log`), não objetos ORM. Uma
função de elegibilidade que lê `log.set_role` funciona quando chamada a
partir de código que tem o objeto (`one_rep_max.py`, que já consulta o ORM
direto) e **quebra silenciosamente** quando chamada a partir de um
template tag que só recebeu o dict — se o dict não tiver a chave, o filtro
não erra, só devolve sempre falso ou sempre verdadeiro, dependendo de como
for escrito, e ninguém percebe até o dado sair errado. Por isso:

1. **`public_workouts/progress_eligibility.py`** — predicados puros, só
   leem `set_role`, funcionam em objeto ORM OU dict (`obj.set_role`
   fallback `obj.get('set_role')`):

   | Finalidade | Regra |
   |---|---|
   | `eligible_for_progress_curve` | `set_role == top_set` |
   | `eligible_for_weekly_trend` | `set_role == top_set` |
   | `eligible_for_personal_record` | `set_role in (top_set, max_set)` |

   `legacy_unknown` nunca satisfaz nenhuma das três.

2. **`public_workouts/progress_snapshot.py`** (novo) — o único lugar que
   consulta `PublicWorkoutLoadLog` (ORM, com `set_role` de verdade) pra
   montar a leitura de progresso pronta pra usar. **Assinatura em LOTE, não
   por movimento** (correção da Revisão 6 — ver §7.5 pro motivo, N+1 real):
   `build_progress_snapshots(*, account_id, as_of=None) -> dict[str, ProgressSnapshot]`,
   uma entrada por `movement_slug`. Cada `ProgressSnapshot` (dataclass, não
   dict — ver §7.5) tem `latest_top_set`, `curve_points` (90 dias),
   `legacy_points` (90 dias — mesma janela do eixo, um ponto de 6 meses
   atrás não cabe no SVG atual), `has_legacy_history` (histórico completo,
   SEM filtro de janela — o aluno vê "seu histórico está salvo" mesmo que
   nada caiba visualmente na janela corrente), `y_scale`, `trend_signal`,
   `one_rep_max`.
   **Tudo que hoje decide "o que é verdade sobre progresso" passa a chamar
   este módulo — nenhum consumidor volta a escanear `PublicWorkoutLoadLog`
   bruto por conta própria.**

3. **Mapa completo de consumidores atingidos** (achado da 3ª revisão
   externa — a lista original só cobria 2 dos 7 pontos reais; achado da 4ª
   revisão — o item de sugestão de carga tinha um SEGUNDO ponto de leitura
   bruta que a 3ª revisão não pegou):

   | Consumidor | Hoje | Depois |
   |---|---|---|
   | `load_chart_points` | escaneia dict bruto | lê `progress_snapshots[movement_slug]` |
   | `one_rep_max.py::_weekly_best_estimates` | escaneia ORM bruto, sem dedup por dia | usa `effective_top_sets_by_day` (§2.4) — MESMA dedup da curva, nunca reimplementada |
   | `services.py::build_student_package` (`services.py:876`) | 1RM a partir do ÚLTIMO log bruto, sem filtro | 1RM a partir de `progress_snapshots` |
   | `public_workouts_extras.py::personal_record` (linha 442) | `max(weighted, key=peso)` sem filtro | chama `eligible_for_personal_record` |
   | **`movement_load_display` → `_last_log_for_movement(load_history, movement_slug)` (linha 599), usado por `suggest_progressive_load_kg`** | **busca de log bruto PRÓPRIA, independente do 1RM — não se corrige ao corrigir `build_student_package`** | recebe `latest_top_set` de `progress_snapshots[movement_slug]` em vez de chamar `_last_log_for_movement` sobre `load_history` bruto — **bug real achado na Revisão 6, não estava coberto** |
   | `services.py::_serialize_load_log` (linha 846) | não expõe `set_role` | passa a incluir, só pra a TABELA/histórico completo mostrar o contexto |

4. **O que NÃO passa por nenhum dos dois módulos** (fica como está, de
   propósito) — todos verificados linha a linha nesta rodada, não por
   suposição:
   - a dica "Última vez: X kg" do `load_tracker.js` — conveniência de
     preenchimento, não afirmação de progresso;
   - **`public_workouts_extras.py::todays_logged_weight` (linha 531) —
     reclassificado nesta revisão.** Eu tinha proposto "priorizar `top_set`
     do dia" aqui. Errado: essa função ecoa o que o aluno ACABOU de salvar
     no campo (existe pra resolver "o campo sempre renderizava vazio,
     aluno duplicava o registro achando que não salvou" — ver docstring da
     própria função). O widget tem UM campo só por movimento — se o
     aluno salvou aquecimento por último hoje, mostrar o `top_set` mais
     antigo em vez do que ele literalmente acabou de digitar seria
     confuso, não mais honesto. Fica de fora, mesma categoria da dica
     "última vez";
   - **`public_workouts_extras.py::week_overview` (linha 93) → `dashboard.py::build_week_overview`** —
     marca dia como "completo" no calendário semanal a partir de QUALQUER
     `load_history` daquele dia, sem olhar `set_role`. Mesmo critério do
     streak do app de box (ver docstring de `dashboard.py`): é presença
     ("treinou hoje?"), não progresso — aquecimento prova presença genuína
     tanto quanto série principal;
   - **`public_workouts/weekly_review_ai.py`** — verificado o arquivo
     inteiro: só recebe o dict que `build_weekly_review` já calculou,
     nunca consulta `PublicWorkoutLoadLog`. Corrigido de graça, confirmado
     por leitura completa do arquivo, não por suposição (a suposição
     idêntica sobre `movement_load_display` na Revisão 4/5 estava errada —
     por isso a verificação explícita aqui, não repetir o mesmo erro).

### 2.3 Novo campo `set_role`

1. `CharField` em `PublicWorkoutLoadLog`, choices: `warmup`, `feeder`,
   `top_set`, `max_set`, **`legacy_unknown`** (5 valores — o enum precisa
   declarar `legacy_unknown` explicitamente; usar o valor sem declará-lo no
   `choices` persistiria um estado que o próprio model não reconhece).
2. **Histórico (10 legados) recebe `legacy_unknown` via backfill, não
   `top_set`.** Assumir `top_set` inventaria precisão que nunca existiu.
   `legacy_unknown` nunca entra em `eligible_for_progress_curve`,
   `eligible_for_weekly_trend` ou `eligible_for_personal_record` — mas
   continua **visível** (ver §3.3).
3. **Protocolo do payload — chave ausente ≠ chave enviada.** A view
   `PublicWorkoutRecordLoadView` (`student_app/views/public_workout_views.py:1415`)
   lê o corpo com `payload.get(...)`, que já distingue "chave nunca
   enviada" (`None`) de "chave enviada explicitamente". Regra:
   - `'set_role' not in payload` (cliente antigo, sem esse conceito, ou
     entrada que já estava no outbox do IndexedDB antes do deploy) →
     `record_load()` recebe `set_role='legacy_unknown'`;
   - `'set_role' in payload` (cliente novo, sempre envia algo, mesmo que o
     valor seja `'top_set'` por padrão do toggle) → usa o valor enviado.
   - A checagem é na VIEW, antes de chamar `record_load()` — o serviço não
     aplica default nenhum por conta própria, só recebe o valor já
     resolvido. Isso fecha a janela em que uma entrada pendente de sync,
     criada pela UI antiga, chegaria depois do deploy e seria confundida
     com uma escolha real de "série principal".
4. **`top_set` e `max_set` não se misturam na curva principal por padrão.**
   A curva principal responde "como está minha série de trabalho" — só
   `top_set`. `max_set` aparece como marcador/camada opcional, nunca
   blendado na mesma linha contínua.
5. **Nunca inferir `max_set` a partir de RIR.** RIR 0 numa série principal
   programada não prova tentativa de máximo — é só a série principal levada
   à falha, o que é esperado, não um evento especial. `max_set` só nasce de
   escolha explícita futura, nunca de inferência automática.
6. **UI** (`load_tracker.js`): campo de carga ganha um toggle binário
   discreto — "Série principal" (padrão, envia `set_role: 'top_set'`) /
   "Foi aquecimento" (envia `set_role: 'warmup'`). A nova UI **sempre**
   envia a chave explicitamente — nunca a omite — pra nunca mais cair no
   caso "chave ausente" depois do primeiro deploy. Sem expor `feeder`/
   `max_set` como jargão ao aluno.

### 2.4 Agrupamento de registros do mesmo exercício/dia — mais recente, não maior

**Correção da Revisão 3 (achado real da 3ª revisão externa):** eu tinha
proposto "o maior peso do dia" como ponto representativo. Isso está errado.
Toda gravação cria uma linha nova com `idempotency_key` própria — não existe
"editar" um registro. Se o aluno registra 100kg por engano e corrige pra
90kg no mesmo dia, "maior" preserva o erro que ele tentou corrigir; "mais
recente" (por `created_at`, não por `performed_on`, que é só a data) reflete
a intenção final dele. **Regra corrigida: série principal efetiva do dia =
`top_set` mais recente por `created_at` naquele dia.**

Isso ainda não distingue "corrigi meu peso" de "fiz uma segunda série
principal de verdade no mesmo dia" — os dois casos são indistinguíveis com
o dado atual (um campo, sem `training_session_id`/`set_sequence`). Fora de
escopo aqui; fica registrado como necessidade futura se o Curva vier a
suportar múltiplas séries de trabalho reais por dia.

**Correção da Revisão 6:** eu tinha dito que esse agrupamento ficava
"escopado dentro de `progress_snapshot.py`, sem virar abstração
compartilhada" e que `one_rep_max.py` calculava seu próprio máximo por
semana separadamente. Isso criava uma inconsistência real: a curva usa o
`top_set` mais recente do dia (90kg, corrigido), mas `_weekly_best_estimates`
iterava TODOS os `top_set` elegíveis da semana (incluindo o 100kg
descartado) e pegava o de MAIOR estimativa de 1RM — ou seja, a curva mostra
90kg no dia, mas a tendência semanal podia continuar contaminada pelo
100kg errado do mesmo dia. Curva e tendência discordando sobre o mesmo fato
é exatamente o problema que este plano existe pra evitar.

**Fix: uma função pura compartilhada**, sem ORM, que ambos chamam:

```python
def effective_top_sets_by_day(logs: list) -> list:
    """logs já filtrados por eligible_for_weekly_trend/progress_curve,
    ordenados por performed_on. Devolve 1 log por dia -- o mais recente por
    created_at. Curva e tendência semanal chamam ESTA função, nunca
    reimplementam o dedup cada uma a seu modo."""
    by_day = {}
    for log in logs:
        existing = by_day.get(log.performed_on)
        if existing is None or log.created_at > existing.created_at:
            by_day[log.performed_on] = log
    return sorted(by_day.values(), key=lambda l: l.performed_on)
```

`progress_snapshot.py` chama isso pra montar `curve_points`.
`one_rep_max.py::_weekly_best_estimates` chama a MESMA função antes de
estimar 1RM por semana — nunca mais duas implementações do "qual registro
do dia vale" podendo divergir. Fica em `progress_eligibility.py` (é sobre
"o que conta", não sobre leitura de banco — cabe junto dos predicados,
não em `progress_snapshot.py`, que é o único que faz query).

Isso ainda não distingue "corrigi meu peso" de "fiz uma segunda série
principal de verdade no mesmo dia" — os dois casos são indistinguíveis com
o dado atual (um campo, sem `training_session_id`/`set_sequence`). Fora de
escopo aqui; fica registrado em §9.5 (`training_session_id`/`set_sequence`
e `captured_at_client`) como necessidade futura.

### 2.5 Tendência semanal aceita semanas não-consecutivas (achado novo)

`detect_one_rep_max_trend` pega `weekly[-_TREND_WINDOW_WEEKS:]` — as
últimas 3 ENTRADAS da lista ordenada, não as últimas 3 semanas
consecutivas do calendário. Se o aluno só treinou esse movimento em
semanas espalhadas ao longo de 6 meses, essas 3 entradas ainda formam uma
"janela de tendência" e podem gerar `plateau`/`declining` sobre um
intervalo que não representa nada coeso.

**Correção:** exigir que as 3 semanas da janela sejam consecutivas
(diferença de exatamente 7 dias entre `week_start` vizinhos); caso
contrário, devolver `insufficient_data` mesmo com 3+ entradas históricas
disponíveis.

### 2.6 Coleta de reps/RIR — o plano não pode prometer mais do que a UI coleta

`load_tracker.js` hoje só envia `weight_kg`/`performed_on`/`movement_slug`/
`program_id` — nunca `reps` nem `rir`. Sem isso, `estimate_one_rep_max`
já devolve `None` (`weight_kg is None or reps is None`), e o template já só
mostra o badge "1RM est." quando existe estimativa (`{% if estimate %}`).
**Esse comportamento de "nunca inventar 1RM sem dado" já está correto e
deve sobreviver ao refactor sem mudança** — só precisa de teste explícito
garantindo que `progress_snapshot.py` preserva o mesmo `None` quando
`reps`/`rir` estiverem ausentes. Coletar `reps`/`rir` na UI (pra 1RM real
em toda série nova, não só quando alguém digitar por fora) fica fora de
escopo deste plano — é decisão de produto separada (V2), não um requisito
pra fechar a contaminação atual.

### 2.7 Regressão real esperada no dia do deploy — os 10 alunos reais perdem sugestão personalizada e "recorde" temporariamente

**Achado nesta rodada, verificado em código, não hipotético.**
`suggest_progressive_load_kg` (`periodization.py:206`) devolve `None`
quando `last_log is None` — comportamento **documentado e intencional** da
própria função (cai pro fallback genérico de %RM). Os 10 alunos legados
terão TODO histórico como `legacy_unknown` — zero `top_set` até logarem de
novo. Isso significa que, no momento do deploy (a partir do PR 2, quando
`movement_load_display` passa a ler `progress_snapshot.latest_top_set` em
vez do log bruto):

1. **A sugestão de carga mais personalizada some pra todos os 10**, pra
   todo movimento, até cada um logar um novo `top_set` naquele movimento
   especificamente. Cai pro fallback de %RM (menos preciso, mas nunca
   inventado — não é dado errado, é dado mais genérico).
2. **`personal_record` ("Suas Cargas") mostra vazio** pros mesmos
   movimentos, pelo mesmo motivo — `eligible_for_personal_record` não acha
   nenhum `top_set`/`max_set` real ainda.

**Por que isso não é um bug a corrigir, e sim um efeito colateral a
comunicar antes do deploy:** a alternativa (deixar `legacy_unknown`
alimentar sugestão/recorde) reabriria exatamente a contaminação que este
plano inteiro existe pra fechar — inventaria precisão sobre dado que nunca
teve essa classificação. A degradação é **temporária e autolimitada**: se
resolve sozinha, movimento por movimento, assim que o aluno registrar a
próxima série principal normalmente (o que já faz parte do uso comum do
app).

**Isso precisa ser comunicado ao Renan/Giovanna antes do PR 2 ir pro ar**
— não é código, é aviso operacional: por alguns dias, a sugestão de carga
dos 10 alunos vai parecer "menos afiada" que o normal, e a aba de recorde
pode aparecer vazia. Se um aluno perguntar, a resposta é "o sistema parou
de inventar precisão sobre seu histórico antigo — volta ao normal assim
que você registrar a próxima série", não "bug".

## 3. Problema 3 — o gráfico não respeita tempo real nem magnitude real

### 3.1 Eixo horizontal por índice, não por data

`load_chart_points`: `step_x = (_CHART_WIDTH - _CHART_PAD * 2) / (len(weighted) - 1)`,
e cada ponto usa `x = _CHART_PAD + index * step_x`. Dois registros com 1 dia
de intervalo ocupam o mesmo espaço visual que dois registros com 1 mês de
intervalo. A curva não representa ritmo real de progresso.

**Mudança proposta:** posição X proporcional ao tempo real decorrido
(`performed_on`), não ao índice do ponto na lista.

**Decidido: janela fixa de 90 dias / 12 semanas na curva principal.** É o
intervalo que mantém a curva legível e viva. Histórico mais antigo que isso
continua disponível na tabela completa, sem seletor de "todo o período"
nesta primeira entrega — evita complexidade de UI que não paga o custo
ainda.

### 3.2 Escala vertical normalizada por gráfico, sem contexto de magnitude

`min_weight, max_weight = min(weights), max(weights)` — a curva sempre
estica do mínimo ao máximo DAQUELE movimento. Uma variação de 2,5 kg ocupa a
mesma altura visual que uma de 20 kg. Emoção sem honestidade.

**Mudança proposta:** manter a auto-escala por gráfico (necessária — supino
e rosca direta têm faixas absolutas incomparáveis), mas adicionar rótulos
discretos de escala nas extremidades do eixo Y — **arredondados pro
incremento de anilha mais próximo (2,5 kg)**, não o `min`/`max` cru dos
registros (ex.: dado real 63,2–69,8 kg exibe rótulo "62,5–70 kg", que é o
que existe fisicamente numa barra), pra que o aluno julgue a magnitude
real, não só a inclinação da linha.

### 3.3 Histórico legado nunca é uma linha contínua, e o estado vazio é honesto

Conectar pontos `legacy_unknown` com a nova curva de progresso sugeriria uma
continuidade que o dado não prova. Tratamento:

- `legacy_unknown` renderiza como **pontos discretos em tom neutro**,
  rotulados "Registros anteriores" — nunca uma `<polyline>` contínua, nunca
  a mesma cor de marca da curva principal.
- A curva principal (`top_set`, linha sólida) é visualmente a única coisa
  chamada "Série principal".
- **Estado vazio quando só existe histórico legado** (nenhum `top_set` real
  ainda): a tela não mostra gráfico vazio nem finge dado que não existe.
  Copy fixo: *"Seu histórico está salvo. Registre sua próxima série
  principal para iniciar uma curva de evolução precisa."* Isso transforma
  uma limitação de dado real em convite, sem escondido nem alarmar.

## 4. O que NÃO muda

- Nenhum modelo novo, nenhuma conta nova, nenhum app `curva/` paralelo.
- `PublicWorkoutLoadLog` continua sendo a fonte de verdade única.
- O outbox offline em IndexedDB (`load_tracker.js`) continua exatamente como
  está — só ganha um campo extra no payload enviado.

## 5. Pronto quando

1. o número atual é visualmente inconfundível como o elemento principal da
   tela, em qualquer tamanho de tela testado;
2. existe `progress_eligibility.py` (predicado puro) e `progress_snapshot.py`
   (única leitura de `PublicWorkoutLoadLog` bruto pra fins de progresso,
   em lote por conta — uma tela com N movimentos nunca gera N queries), e
   **todos os 6 consumidores do mapa da seção 2.2/§8.1** (curva, tendência
   semanal, `build_student_package`, `personal_record`,
   **`movement_load_display`/sugestão de carga**) passam por eles — nenhum
   volta a escanear log bruto por conta própria (`todays_logged_weight` e
   `week_overview` ficam de fora, deliberadamente — §2.2 item 4);
3. a curva principal e a tendência semanal usam a MESMA dedup por dia
   (`effective_top_sets_by_day`) — nunca discordam sobre qual registro do
   dia vale quando há correção no mesmo dia; nunca mistura `warmup`/
   `legacy_unknown` com `top_set`, nem `top_set` com `max_set`;
4. aquecimento e histórico legado continuam salvos e visíveis (tabela /
   linha discreta), só não entram na curva principal nem em nenhum sinal
   derivado;
5. a posição horizontal reflete tempo real; o eixo vertical mostra a faixa
   absoluta de peso arredondada pra incremento de anilha, não só a forma da
   curva;
6. tendência semanal exige semanas consecutivas — nunca "3 semanas" que na
   verdade cobrem 6 meses de hiato;
7. `record_load` valida `set_role` antes de inserir; `IntegrityError` nunca
   mascara um erro de validação como colisão de idempotência;
8. os 10 alunos legados continuam vendo alguma leitura depois do deploy
   (histórico visível como "anterior", mesmo que fora da curva de
   progresso);
9. o service worker do PWA recebe o bump de `PUBLIC_WORKOUT_CACHE_EPOCH` —
   aparelho com app já instalado não fica preso indefinidamente no
   `load_tracker.js` antigo.

## 6. Única decisão que continua aberta

- Tamanho exato do número hero (~2.2-2.6rem é ponto de partida) — depende de
  como fica em tela real de 360px; ajustar durante implementação, não antes.

Todas as demais (janela temporal, timing do toggle de aquecimento, enum,
protocolo de payload, tratamento visual do legado) foram resolvidas nas
Revisões 2 e 3 — ver §7 pra como cada uma se traduz em código.

## 7. Plano técnico de implementação detalhado (Revisão 4)

### 7.1 Camadas tocadas, em ordem de dependência

```
1. Modelo + 3 migrations           public_workouts/models.py, migrations/
2. Backfill do histórico            management command novo, idempotente
3. progress_eligibility.py          novo — predicados puros
4. progress_snapshot.py             novo — única leitura de ORM pra progresso
5. Serviço de escrita                services.py::record_load (+ validação)
6. Consumidores derivados            one_rep_max.py, build_student_package,
                                       personal_record, movement_load_display
7. View (protocolo de payload)      student_app/views/public_workout_views.py
8. Apresentação da curva             public_workouts_extras.py::load_chart_points
9. Template + CSS                    workout.html, workout-shell.css
10. Cliente offline + PWA            load_tracker.js, PUBLIC_WORKOUT_CACHE_EPOCH
```

A ordem importa: 1→7 primeiro (backend aceita e resolve `set_role` mesmo
antes de qualquer cliente enviar), 8→10 depois. Fazer na ordem inversa
deixaria uma janela em que o cliente novo envia `set_role` pra um backend
que ainda não entende o campo.

### 7.2 Modelo e migrations — 3 migrations DE VERDADE, nunca `default=` no field

**Correção da Revisão 6 (dois bugs achados na auto-descrição):** eu tinha
escrito "3 migrations separadas" mas só descrevia 2 (nullable, depois
`NOT NULL`) — backfill não é migration, então na prática eram 2 disfarçadas
de 3. E o esboço de `Meta.indexes` listava só o índice NOVO, o que faria o
Django gerar uma migration que **remove** o índice já existente
`(account, movement_slug, performed_on)` — ele precisa continuar
declarado, os dois coexistem.

```python
# public_workouts/models.py — PublicWorkoutLoadLog

class PublicWorkoutLoadLogSetRole(models.TextChoices):
    WARMUP = 'warmup', 'Aquecimento'
    FEEDER = 'feeder', 'Aproximação'
    TOP_SET = 'top_set', 'Série principal'
    MAX_SET = 'max_set', 'Esforço máximo'
    LEGACY_UNKNOWN = 'legacy_unknown', 'Histórico anterior (não classificado)'

set_role = models.CharField(
    max_length=16, choices=PublicWorkoutLoadLogSetRole.choices, null=True,
)

class Meta:
    ordering = ['-performed_on', '-created_at']
    indexes = [
        models.Index(fields=['account', 'movement_slug', 'performed_on']),  # EXISTENTE — preservado
        models.Index(fields=['account', 'set_role', 'movement_slug', 'performed_on']),  # NOVO —
        # ordem (account, set_role, ...) porque a query real é em LOTE por
        # conta (§7.5: build_progress_snapshots busca tudo de uma
        # conta filtrando por set_role primeiro, agrupa por movimento em
        # Python depois) — o índice segue a consulta real, não o desenho
        # antigo por-movimento.
    ]
```

**Nunca `default='top_set'` no field.** 3 migrations reais:

1. **Migration A** — adiciona `set_role` nullable, sem default, com os
   DOIS índices (o antigo preservado + o novo).
2. **Migration B** — `CheckConstraint` permitindo só os 5 valores do enum
   OU `NULL` (defesa em profundidade — protege contra qualquer escrita que
   não passe por `record_load`, incluindo edição direta no Admin). Roda
   junto do PR 1 (§7.12) — não depende do backfill ter completado, porque
   aceita `NULL`.
3. **Migration C** — depois que o backfill confirmar zero linha `NULL` (o
   checkpoint do §7.12), torna `set_role` `null=False`. Só entra depois de
   confirmar em produção — nunca no mesmo deploy que liga a escrita.

### 7.3 Backfill

```python
# management command backfill_public_workout_load_log_set_role
PublicWorkoutLoadLog.objects.filter(set_role__isnull=True).update(
    set_role=PublicWorkoutLoadLogSetRole.LEGACY_UNKNOWN,
)
```

Idempotente. Roda uma vez, manualmente, depois da migration A e antes da
migration B.

### 7.4 `progress_eligibility.py` (novo — predicados puros)

```python
"""Predicados puros — funcionam em objeto ORM ou em dict serializado,
nunca assumem qual dos dois chega."""

from .models import PublicWorkoutLoadLogSetRole as SetRole

_CURVE_AND_TREND_ROLES = frozenset({SetRole.TOP_SET})
_PERSONAL_RECORD_ROLES = frozenset({SetRole.TOP_SET, SetRole.MAX_SET})


def _role_of(entry) -> str | None:
    return getattr(entry, 'set_role', None) if not isinstance(entry, dict) else entry.get('set_role')


def eligible_for_progress_curve(entry) -> bool:
    return _role_of(entry) in _CURVE_AND_TREND_ROLES


def eligible_for_weekly_trend(entry) -> bool:
    return _role_of(entry) in _CURVE_AND_TREND_ROLES


def eligible_for_personal_record(entry) -> bool:
    return _role_of(entry) in _PERSONAL_RECORD_ROLES


def effective_top_sets_by_day(logs: list) -> list:
    """logs já filtrados (ORM, com set_role real), ordenados por
    performed_on. Devolve 1 log por dia -- o mais recente por created_at,
    nunca o de maior peso (preservaria erro de correção, §2.4). Curva
    (progress_snapshot.py) e tendência semanal (one_rep_max.py) chamam
    ESTA função — nunca duas implementações do "qual registro do dia
    vale" podendo divergir (achado real da Revisão 6: divergiam)."""
    by_day = {}
    for log in logs:
        existing = by_day.get(log.performed_on)
        if existing is None or log.created_at > existing.created_at:
            by_day[log.performed_on] = log
    return sorted(by_day.values(), key=lambda l: l.performed_on)
```

### 7.5 `progress_snapshot.py` (novo — única leitura de ORM pra progresso, EM LOTE)

**Correção da Revisão 6 — N+1 real.** A versão anterior tinha assinatura
por movimento (`build_progress_snapshot(account_id, movement_slug)`). Uma
tela com 12 movimentos chamaria isso 12 vezes, cada chamada com suas
próprias queries de curva/legado/tendência — N+1 exatamente na tela que
precisa parecer instantânea. Corrigido pra buscar tudo da conta de uma vez
e agrupar por movimento em memória.

**Correção da Revisão 6 — DTO neutro, sem risco de import circular.** A
versão anterior usava `_serialize_load_log` (privada de `services.py`) pra
serializar `latest_top_set`. Mas `services.py::build_student_package`
passa a IMPORTAR `progress_snapshot.py` (pra deixar de escanear log bruto)
— se `progress_snapshot.py` importasse de volta `services.py`, seria
`services → progress_snapshot → services`, circular. Fix: dataclass próprio,
sem depender de nada de `services.py`.

```python
"""Único lugar que consulta PublicWorkoutLoadLog bruto (ORM, com set_role
de verdade) pra decidir o que é verdade sobre progresso, EM LOTE por
conta. Curva, badge de 1RM, tendência semanal e sugestão de carga leem
daqui — nenhum volta a escanear o log bruto por conta própria. Não importa
nada de services.py (evita import circular: services importa este módulo,
não o contrário)."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING

from django.utils import timezone

from .models import PublicWorkoutLoadLog, PublicWorkoutLoadLogSetRole as SetRole
from .progress_eligibility import _CURVE_AND_TREND_ROLES, effective_top_sets_by_day
from .one_rep_max import detect_one_rep_max_trend, estimate_one_rep_max

_WINDOW_DAYS = 90
_PLATE_INCREMENT_KG = Decimal('2.5')


@dataclass(frozen=True)
class ProgressPoint:
    """Representação neutra de um ponto — não é o model, não é o dict de
    _serialize_load_log. progress_snapshot.py nunca depende de services.py."""
    performed_on: date
    weight_kg: Decimal | None
    reps: int | None
    rir: Decimal | None
    created_at: datetime


@dataclass(frozen=True)
class ProgressSnapshot:
    latest_top_set: ProgressPoint | None
    curve_points: list  # ProgressPoint, só dentro da janela de 90 dias
    legacy_points: list  # ProgressPoint, só dentro da janela — ver 9.7
    has_legacy_history: bool  # histórico completo, SEM filtro de janela
    y_scale: dict | None
    trend_signal: str
    one_rep_max: object | None  # OneRepMaxEstimate de one_rep_max.py, ou None


def _to_point(log) -> ProgressPoint:
    return ProgressPoint(log.performed_on, log.weight_kg, log.reps, log.rir, log.created_at)


def build_progress_snapshots(*, account_id: int, as_of: date | None = None) -> dict:
    as_of = as_of or timezone.localdate()
    window_start = as_of - timedelta(days=_WINDOW_DAYS)

    # DUAS queries pra CONTA INTEIRA -- nunca uma por movimento.
    curve_logs_by_movement: dict[str, list] = {}
    for log in PublicWorkoutLoadLog.objects.filter(
        account_id=account_id, set_role__in=_CURVE_AND_TREND_ROLES,
    ).order_by('movement_slug', 'performed_on', 'created_at'):
        curve_logs_by_movement.setdefault(log.movement_slug, []).append(log)

    legacy_logs_by_movement: dict[str, list] = {}
    for log in PublicWorkoutLoadLog.objects.filter(
        account_id=account_id, set_role=SetRole.LEGACY_UNKNOWN,
    ).order_by('movement_slug', 'performed_on'):
        legacy_logs_by_movement.setdefault(log.movement_slug, []).append(log)

    movement_slugs = set(curve_logs_by_movement) | set(legacy_logs_by_movement)
    snapshots = {}
    for movement_slug in movement_slugs:
        effective = effective_top_sets_by_day(curve_logs_by_movement.get(movement_slug, []))
        windowed = [log for log in effective if log.performed_on >= window_start]
        latest = effective[-1] if effective else None

        all_legacy = legacy_logs_by_movement.get(movement_slug, [])
        # legacy_points respeita a MESMA janela de 90 dias do eixo -- um
        # ponto de 6 meses atras nao cabe no SVG atual. has_legacy_history
        # NAO filtra: o aluno ve "seu historico esta salvo" mesmo que nada
        # caiba visualmente na janela corrente (Revisao 6, achado real).
        legacy_windowed = [log for log in all_legacy if log.performed_on >= window_start]

        # DELEGA pro one_rep_max.py ja corrigido (§7.7) -- nunca reimplementa
        # estimativa/tendencia aqui. Mesma effective_top_sets_by_day usada
        # aqui e' a que _weekly_best_estimates chama, entao curva e
        # tendencia NUNCA mais discordam sobre qual registro do dia vale.
        trend = detect_one_rep_max_trend(account_id=account_id, movement_slug=movement_slug)
        one_rep_max = (
            estimate_one_rep_max(weight_kg=latest.weight_kg, reps=latest.reps, rir=latest.rir)
            if latest else None
        )

        snapshots[movement_slug] = ProgressSnapshot(
            latest_top_set=_to_point(latest) if latest else None,
            curve_points=[_to_point(log) for log in windowed],
            legacy_points=[_to_point(log) for log in legacy_windowed],
            has_legacy_history=bool(all_legacy),
            y_scale=_rounded_scale([log.weight_kg for log in windowed]),
            trend_signal=trend.label,
            one_rep_max=one_rep_max,
        )
    return snapshots


def _rounded_scale(weights: list) -> dict | None:
    """min/max arredondados pro multiplo de 2,5kg mais proximo (§3.2) --
    NUNCA o min/max cru. weights vazio -> None. min==max (serie plana,
    Revisao 6 achado real) -> aplica padding de +/-2,5kg pra nunca desenhar
    uma faixa de altura zero."""
    if not weights:
        return None
    low, high = min(weights), max(weights)
    if low == high:
        low, high = max(Decimal('0'), low - _PLATE_INCREMENT_KG), high + _PLATE_INCREMENT_KG
    return {
        'min_kg': (low / _PLATE_INCREMENT_KG).to_integral_value(rounding=ROUND_FLOOR) * _PLATE_INCREMENT_KG,
        'max_kg': (high / _PLATE_INCREMENT_KG).to_integral_value(rounding=ROUND_CEILING) * _PLATE_INCREMENT_KG,
    }
```

`build_student_package`, `personal_record` e **`movement_load_display`**
(recebendo `latest_top_set` do snapshot em vez de chamar
`_last_log_for_movement(load_history, movement_slug)` — bug real achado
nesta revisão, ver mapa em §2.2) passam a ler
`build_progress_snapshots(account_id=...)[movement_slug]` em vez de
escanear `PublicWorkoutLoadLog`/`load_history` bruto cada um por conta
própria. A view chama `build_progress_snapshots` **uma vez** por request
(não uma vez por movimento) e distribui o resultado pros consumidores que
precisarem, dentro do mesmo request. `todays_logged_weight` e
`week_overview` continuam lendo `load_history` bruto direto, sem
elegibilidade — de propósito, §2.2 item 4.

**Quem chama qual predicado, exatamente:**

| Consumidor | Lê | Chama |
|---|---|---|
| `progress_snapshot.py` (curva/1RM/tendência) | ORM em lote | filtro `set_role__in=_CURVE_AND_TREND_ROLES` na query + `effective_top_sets_by_day` |
| `one_rep_max.py::_weekly_best_estimates` | ORM direto | `eligible_for_weekly_trend(log)` por linha + `effective_top_sets_by_day` (mesma função da curva) |
| `personal_record` | dict serializado | `eligible_for_personal_record(entry)` por linha |
| `movement_load_display` | `ProgressSnapshot.latest_top_set` | nada — já vem resolvido, não filtra por conta própria |
| `todays_logged_weight`, `week_overview` | dict serializado / bruto | nenhum predicado — fora de escopo por design (§2.2 item 4) |

### 7.6 `record_load()` — validação antes do insert, `IntegrityError` sem mascarar erro, default só na FUNÇÃO

**Regressão real achada nesta rodada:** `record_load()` é chamado direto
(sem passar pela view) em **~30 lugares de teste** hoje, majoritariamente
em `test_load_log.py`, testando idempotência/validação/export — nada
relacionado a `set_role`. Se o parâmetro virar obrigatório sem nenhum
default, todos quebram no mesmo commit por um motivo que não têm nada a
ver com o que estão testando.

Isso não contradiz a regra "nunca `default='top_set'`" do §7.2 — aquela
regra é sobre o **campo do model** (evitaria fabricar precisão em dado
histórico existente) e sobre a **view** (nunca assumir por um payload
HTTP anônimo). Uma chamada direta de `record_load()` em código Python —
teste ou management command — é um contexto de confiança diferente: quem
escreve a chamada sabe o que está testando. Um default só na assinatura
da função, que a VIEW SEMPRE sobrescreve com um valor explícito de
qualquer forma, resolve os dois lados sem reabrir a lacuna:

```python
def record_load(
    *, account_id: int, movement_slug: str, weight_kg, reps=None, rir=None,
    performed_on, program_id=None, week_in_program=None,
    set_role: str = PublicWorkoutLoadLogSetRole.TOP_SET,  # default só aqui —
    # a view (§7.7... err, ver protocolo de payload) SEMPRE passa um valor
    # explicito, o default so evita quebrar ~30 chamadas de teste que nao
    # tem nada a ver com set_role
    idempotency_key: str,
) -> dict:
    _validate_load_values(weight_kg=weight_kg, rir=rir)
    if set_role not in PublicWorkoutLoadLogSetRole.values:
        raise LoadValueError(f'set_role invalido: {set_role!r}')  # valida ANTES do insert

    try:
        with transaction.atomic():
            log = PublicWorkoutLoadLog.objects.create(..., set_role=set_role)
    except IntegrityError:
        # NUNCA .get()+except DoesNotExist aninhado: um `raise` sem
        # argumento dentro do except de DENTRO relança a excecao DAQUELE
        # except (DoesNotExist), nao o IntegrityError de fora -- bug real
        # achado na Revisao 6 (comentario dizia uma coisa, Python fazia
        # outra). .filter().first() evita o aninhamento: o raise aqui fica
        # no mesmo nivel do except IntegrityError, entao relança o
        # IntegrityError original de verdade.
        log = PublicWorkoutLoadLog.objects.filter(idempotency_key=idempotency_key).first()
        if log is None:
            raise
    return _serialize_load_log(log)
```

Sem a validação explícita do `set_role` (linha acima), um futuro
`CheckConstraint` (§7.2, migration B) rejeitaria o INSERT com
`IntegrityError` por um motivo que não é colisão de idempotência — o
`.filter().first()` evita mascarar isso: se não existe log com aquela
chave, o erro original (de constraint, não de idempotência) sobe intacto.

### 7.7 `one_rep_max.py` — dedup compartilhado + janela consecutiva + frescor

**Correção da Revisão 6, duas partes.** Primeiro: `_weekly_best_estimates`
tinha só o filtro de `set_role`, mas iterava TODOS os `top_set` elegíveis
da semana sem dedup por dia — se o aluno corrigiu 100kg→90kg no mesmo dia,
os dois são `top_set`, e a função pegava a MAIOR estimativa (a do 100kg
errado), divergindo da curva (que já usa o mais recente). Fix: usar
`effective_top_sets_by_day` (§7.4) antes de estimar — a MESMA dedup da
curva.

Segundo: exigir 3 semanas consecutivas não basta — se essas 3 semanas
consecutivas forem de janeiro e for setembro agora, ainda diria "Em
evolução" sobre um treino que parou há 8 meses. Fix: a última semana da
janela também precisa ser recente (≤14 dias de `as_of`).

```python
def _weekly_best_estimates(*, account_id, movement_slug):
    logs = PublicWorkoutLoadLog.objects.filter(
        account_id=account_id, movement_slug=movement_slug,
        set_role__in=_CURVE_AND_TREND_ROLES,  # filtro no banco, nao em Python
    ).order_by('performed_on')

    best_by_week = {}
    for log in effective_top_sets_by_day(list(logs)):  # dedup compartilhado com a curva
        estimate = estimate_one_rep_max(weight_kg=log.weight_kg, reps=log.reps, rir=log.rir)
        if estimate is None:
            continue
        week = _week_start(log.performed_on)
        if week not in best_by_week or estimate.value_kg > best_by_week[week]:
            best_by_week[week] = estimate.value_kg
    return sorted(best_by_week.items())


def detect_one_rep_max_trend(*, account_id, movement_slug, as_of=None):
    as_of = as_of or timezone.localdate()
    weekly = _weekly_best_estimates(account_id=account_id, movement_slug=movement_slug)
    if len(weekly) < _TREND_WINDOW_WEEKS:
        return OneRepMaxTrend(..., label='insufficient_data', weekly_estimates_kg=())

    window = weekly[-_TREND_WINDOW_WEEKS:]
    weeks = [week for week, _value in window]
    # exige semanas consecutivas (7 dias entre vizinhas)...
    if any((weeks[i + 1] - weeks[i]).days != 7 for i in range(len(weeks) - 1)):
        return OneRepMaxTrend(..., label='insufficient_data', weekly_estimates_kg=())
    # ...E que a ultima semana seja recente -- 3 semanas consecutivas de
    # janeiro nao autorizam "Em evolucao" em setembro.
    if (as_of - weeks[-1]).days > 14:
        return OneRepMaxTrend(..., label='insufficient_data', weekly_estimates_kg=())
    ...
```

Reaproveita o rótulo `insufficient_data` já existente em vez de criar um
`stale` novo — menos tipos pra `build_weekly_review` e todo consumidor de
`OneRepMaxTrend.label` terem que tratar. Considerado e não adotado: um
rótulo `stale` distinto ("você parou" vs. "ainda não há dado suficiente")
comunicaria melhor, mas exigiria atualizar todo lugar que trata
`label` hoje — fica pra quando houver evidência de que a distinção importa
pro aluno, não antecipada aqui.

### 7.8 `load_chart_points` — passa a formatar um `ProgressSnapshot`, não a decidir

Deixa de escanear `entries` bruto. A view chama `build_progress_snapshots(account_id=...)`
**uma vez** (§7.5) e passa `snapshots[movement_slug]` pro filtro, que só
converte `ProgressSnapshot.curve_points`/`legacy_points` pra coordenadas
SVG: `x` proporcional a dias decorridos dentro da janela de 90 (já
filtrada pelo snapshot), `y` normalizado por `snapshot.y_scale`
(já arredondado e com padding pra série plana). `legacy_points` como lista
separada nunca ligada por `<polyline>`. `has_data=False` cobre "zero
`curve_points`"; `snapshot.has_legacy_history` (não filtrado por janela)
decide se mostra o estado vazio do §3.3 ou realmente nada.

### 7.9 Template + CSS — seletores exatos

- `templates/public_workouts/workout.html`, dentro do bloco
  `{% for group in load_history_by_movement %}` (linha ~380 em diante):
  `legacy_points` renderiza como `<circle class="workout-load-chart-dot--legacy">`
  isolado, **sem** `<polyline>` ligando — nunca reusa `workout-load-chart-line`/
  `workout-load-chart-area`. Bloco de estado vazio (§3.3) entra como novo
  `<p class="workout-load-chart-empty">` quando `chart.has_data` é falso
  mas `chart.legacy_points` não é vazio.
- `static/css/public_workouts/workout-shell.css`:
  - `.workout-load-chart-current strong` (hoje linha 737, `font-size: 1.05rem`)
    sobe pra `clamp(2rem, 8vw, 2.6rem)` (responsivo, nunca fixo — tela de
    360px e desktop precisam do mesmo tratamento proporcional), `font-weight: 800`.
  - `.workout-load-chart-1rm` e `.workout-load-chart-signal` (badges hoje no
    mesmo eixo do número) ganham `font-size: 0.68rem` (reduzido de
    `0.72rem` atual) e movem de posição via `order`/reflow do flex pai
    `.workout-load-chart-head` pra uma segunda linha, abaixo do número.
  - `.workout-load-chart-siblings` (hoje sempre visível, `<p>`) vira
    `<details class="workout-load-chart-siblings">` com `<summary>Ver
    variações</summary>` — o parágrafo atual entra dentro do `<details>`.
  - **Nova classe** `.workout-load-chart-scale-label` — rótulo discreto nas
    extremidades do eixo Y (`font-size: 0.62rem`, `color: var(--theme-text-muted)`).
  - **Nova classe** `.workout-load-chart-dot--legacy` — mesma geometria de
    `.workout-load-chart-dot`, mas `fill: var(--theme-text-muted)` em vez
    de `var(--brand)`, sem `filter: drop-shadow`.
  - **Nova classe** `.workout-load-chart-empty` — texto do estado vazio
    (§3.3), estilo próximo de `.workout-load-chart p` já existente pro
    caso `has_data=False` atual.

### 7.10 `load_tracker.js` + rollout de PWA — atributo e função exatos

- Novo atributo no widget, consistente com a convenção já usada
  (`data-workout-load-input`, `-field`, `-save`, `-step`, `-hint`, `-status`):
  `[data-workout-load-warmup-toggle]` — um `<input type="checkbox">` dentro
  do mesmo `[data-workout-load-input]`, desmarcado por padrão.
- `buildEntryFromWidget(widget, weightKg)` (hoje só monta
  `idempotency_key`/`movement_slug`/`program_id`/`weight_kg`/`performed_on`)
  ganha uma linha:
  ```js
  var warmupToggle = widget.querySelector('[data-workout-load-warmup-toggle]');
  entry.set_role = (warmupToggle && warmupToggle.checked) ? 'warmup' : 'top_set';
  ```
  Sempre presente no objeto — nunca `undefined`/omitido — pra nunca mais
  cair no caso "chave ausente" depois do primeiro deploy (§2.3.3).
- **`PUBLIC_WORKOUT_CACHE_EPOCH` sobe de 4 pra 5** (`student_app/views/public_workout_views.py:71`)
  — sem isso, aparelho com PWA já instalado continua servindo o
  `load_tracker.js` antigo indefinidamente, do jeito que o próprio comentário
  do código já documenta pra correções anteriores.
- Teste manual pós-deploy: sync offline→online, logout/login, reenvio
  idempotente de entrada que já estava no outbox antes do bump.

### 7.11 Testes por camada

| Camada | Casos |
|---|---|
| Migrations | migration A preserva o índice antigo (não só adiciona o novo); migration B (`CheckConstraint`) aceita `NULL` e os 5 valores, rejeita qualquer outro; migration C falha alto e claro se rodar com `NULL` residual; **migration C nunca no mesmo PR que liga a escrita** |
| `progress_eligibility.py` | `effective_top_sets_by_day` pega o mais recente por `created_at`, nunca o maior peso, com 2+ registros no mesmo dia; funciona com objeto ORM E com dict; `legacy_unknown` reprovado nas 3 funções de elegibilidade |
| `progress_snapshot.py` | **uma única chamada de `build_progress_snapshots` cobre N movimentos sem N queries** (teste de contagem de query, não só de resultado); `curve_points` e `legacy_points` respeitam a janela de 90 dias; `has_legacy_history=True` mesmo quando todo o legado cai fora da janela; `y_scale` com `min==max` aplica padding, nunca vira faixa de altura zero |
| `record_load` | `set_role` inválido → `LoadValueError` antes do insert; `IntegrityError` por causa NÃO relacionada a idempotência relança o erro original — teste explícito simulando um `IntegrityError` que NÃO é colisão de `idempotency_key`, confirmando que sobe (não fica mascarado por `DoesNotExist`) |
| View | payload sem `set_role` → `legacy_unknown`; com valor → usa o valor; serializer inclui `set_role` na resposta |
| `one_rep_max.py` | correção no mesmo dia (100kg→90kg) não contamina a semana — `_weekly_best_estimates` usa a MESMA `effective_top_sets_by_day` da curva; 3 semanas espalhadas em 6 meses → `insufficient_data`; 3 semanas consecutivas mas antigas (última >14 dias de `as_of`) → `insufficient_data`, nunca `improving` |
| `build_student_package`/`personal_record`/**`movement_load_display`** | os 3 passam a refletir `progress_snapshot`, nenhum lê log bruto direto — teste específico pra `movement_load_display` com fase canônica ativa e último log sendo aquecimento, confirmando que a sugestão de carga não usa esse valor |
| `todays_logged_weight` (regressão a NÃO introduzir) | continua devolvendo o último salvo hoje independente de `set_role` — teste que confirma isso explicitamente, pra ninguém "corrigir" isso de novo no futuro achando que é contaminação |
| `record_load` (regressão a NÃO introduzir) | as ~30 chamadas diretas existentes em `test_load_log.py`/`test_export_account_data.py`/etc. continuam passando SEM alteração — `set_role` tem default de função, não quebra teste que não é sobre isso |
| Regressão de deploy (conta só com `legacy_unknown`) | `movement_load_display` cai pro fallback de %RM (nunca erro, nunca `None` não tratado) quando `latest_top_set` é `None`; `personal_record` devolve `has_data=False` de forma limpa, não exceção |
| Golden/contrato | nenhum `data-key`/`store_key`/URL legado quebra |
| PWA | reenvio de entrada pré-bump não vira `top_set`; sync offline→online seguro |

### 7.12 Sequenciamento de deploy (Revisão 6 — escritor compatível entra no PR 1, não no PR 2)

**Dois bugs de sequenciamento corrigidos nesta rodada.** O primeiro
(Revisão 5): migration final não pode ir no mesmo PR que liga a escrita.
O segundo (Revisão 6, mais sério): a versão anterior deixava o PR 1
adicionar a coluna SEM tornar o escritor compatível — entre o deploy do
PR 1 e o do PR 2, o código antigo continuava gravando `NULL`, e pior,
enquanto isso não é só risco de migration: qualquer registro `NULL` criado
nesse intervalo fica **invisível** pra `progress_snapshot`/curva/tendência
(não bate `set_role__in=(...)` nem `set_role=legacy_unknown`) até o
próximo backfill rodar. Fix: o escritor compatível (view resolve chave
ausente → `legacy_unknown`; serializer expõe `set_role`) entra JUNTO da
migration A, não espera o PR que liga a leitura.

1. **PR 1** — migration A (nullable + os dois índices) + migration B
   (`CheckConstraint` 5 valores ou `NULL` — aceita `NULL`, não depende do
   backfill) + `progress_eligibility.py` + `progress_snapshot.py` (ainda
   sem consumidor usando) + comando de backfill + **`record_load`
   (validação do enum + fix do `IntegrityError`) + view (protocolo de
   payload: chave ausente → `legacy_unknown`) + `_serialize_load_log`
   expondo `set_role`**. Deploy. A partir daqui, **toda escrita nova já
   grava um valor real, nunca mais `NULL`** — mesmo que nenhum consumidor
   de leitura tenha mudado ainda. Roda o backfill manualmente, confirma
   zero `NULL`.
2. **PR 2** — `one_rep_max.py` (dedup compartilhado + janela consecutiva +
   frescor) + `build_student_package`/`personal_record`/
   **`movement_load_display`** lendo `progress_snapshot`
   (`todays_logged_weight`/`week_overview` ficam intocados, de propósito).
   Nenhuma migration neste PR — só leitura mudando
   pra uma fonte já correta desde o PR 1. Deploy.
3. **Checkpoint operacional (não é PR):** rodar o backfill de novo
   (idempotente — mopa qualquer `NULL` residual, que a essa altura só
   existiria se algo tivesse escapado do PR 1) e confirmar via query
   direta que `PublicWorkoutLoadLog.objects.filter(set_role__isnull=True).exists()`
   é `False`.
4. **PR 3** — migration C (torna `set_role` obrigatório, só depois do
   checkpoint confirmar dado limpo) + `load_chart_points` + template + CSS
   (hierarquia, janela temporal, escala, pontos legados, estado vazio).
   Deploy.
5. **PR 4** — `load_tracker.js` (toggle de aquecimento, payload sempre com
   `set_role`) + bump de `PUBLIC_WORKOUT_CACHE_EPOCH`. Deploy.

**Efeito colateral aceito, não um bug:** entre o deploy do PR 1 e o do
PR 4, o JS antigo continua sem enviar `set_role` — todo registro nesse
intervalo cai em `legacy_unknown` (a view do PR 1 já resolve isso). A curva
principal e o 1RM/tendência ficam sem ganhar ponto novo enquanto essa
janela durar — o registro não se perde, só não conta como progresso ainda,
e isso é verdade desde o PR 1, não desde o PR 2 como a versão anterior
descrevia.

## 8. Varredura completa de consumidores (auditoria)

Busca exaustiva por `PublicWorkoutLoadLog`/`list_load_history` em todo `.py`
do repositório, todo template que usa os filtros/tags afetados, `admin.py`
e `management/commands/`. Sem atalho de "provavelmente só é isso" — cada
linha abaixo foi lida.

### 8.1 Consumidores que passam a exigir a política (progresso/comparabilidade)

**Atualizado na Revisão 6** — o item 5 da versão anterior
(`movement_load_display` "corrigido de graça" via `load_suggestion.py`)
estava errado: a função tem uma SEGUNDA busca de log bruto própria
(`_last_log_for_movement`, linha 599) que `load_suggestion.py` nunca vê.
Item removido daqui a `todays_logged_weight` — reclassificado pra §8.2
depois de ler o corpo completo da função (era suposição errada na Revisão
4/5, corrigida por leitura de código nesta rodada).

| # | Consumidor | Arquivo:linha | Status no plano |
|---|---|---|---|
| 1 | `load_chart_points` | `public_workouts_extras.py:358` | já coberto (§7.8) |
| 2 | `_weekly_best_estimates`/`detect_one_rep_max_trend` | `one_rep_max.py:161,183` | já coberto (§7.7) |
| 3 | `build_student_package` (badge 1RM de `workout.html`) | `services.py:876` | já coberto (§7.5) |
| 4 | `personal_record` | `public_workouts_extras.py:442` | já coberto (§7.5/mapa §2.2) |
| 5 | `movement_load_display` → `_last_log_for_movement` (linha 599) | `public_workouts_extras.py:599` | **bug real, achado na Revisão 6** — busca própria, independente do item 3; corrigido em §7.5 |
| 6 | `build_weekly_review` | `services.py:906` | **corrigido de graça, verificado** — chama `detect_one_rep_max_trend` (item 2) diretamente, sem lógica própria de leitura |
| 7 | `weekly_review_ai.py::generate_weekly_review_text` | `weekly_review_ai.py:59` | **corrigido de graça, verificado por leitura completa do arquivo** — só consome o dict que `build_weekly_review` já calculou, nunca consulta o model |

### 8.2 Consumidores achados na varredura, deliberadamente FORA da política (sinal de engajamento/UI, não de progresso)

| Consumidor | Arquivo:linha | O que faz | Por que fica fora |
|---|---|---|---|
| `recent_load_accounts` | `metrics.py:131` | Conta ANY log nos últimos 14 dias pra classificar retenção (`healthy`/`attention`/`high_risk`) no cockpit comercial | A pergunta é "essa pessoa apareceu e treinou", não "ela progrediu" — um aquecimento prova presença genuína. Filtrar aqui esconderia engajamento real |
| `has_recent_training` | `operations.py:197` | Decide se o work item semanal do Premium é revisão normal ou escalado pra `CUSTOMER_SUCCESS_CONTACT` (aluno sem atividade recente) | Mesmo raciocínio — é gatilho operacional de "sumiu?", não claim de evolução |
| `last_load_by_movement` | `services.py` (dentro de `build_student_package`) | Dica "Última vez: X kg" pro campo de preenchimento | Conveniência de UI, não afirmação de progresso — já decidido assim na Revisão 2 |
| `export_account_data`/`list_load_history` | `services.py:1035,992` | Export LGPD do titular — inclui histórico de carga bruto | Export tem que mostrar a verdade registrada, nunca uma visão filtrada. Ganha `set_role` de graça quando `_serialize_load_log` for atualizado, sem filtrar nada |
| `todays_logged_weight` | `public_workouts_extras.py:531` | Ecoa o que o aluno acabou de salvar hoje nesse campo (evita duplicar registro por o campo parecer vazio) | Reclassificado nesta revisão: é confirmação de "o que eu digitei", não claim de progresso — priorizar `top_set` mostraria valor diferente do que o aluno literalmente acabou de salvar, pior UX, não mais honesto |
| `week_overview` → `dashboard.py::build_week_overview` | `public_workouts_extras.py:93` | Marca dia como "completo" no calendário semanal a partir de QUALQUER `load_history` daquele dia | Mesmo critério do streak do app de box — presença ("treinou hoje?"), não progresso |

### 8.3 Falsos positivos da busca (só menção em docstring, nenhum consumo real)

- `dashboard.py:22,28` — comentário explicando que QUEM CHAMA a função é responsável pela consulta; `build_week_overview` em si é pura, recebe `completed_dates` já calculado (o consumo real de `load_history` é em `week_overview`, o template tag em `public_workouts_extras.py:93` — ver §8.2).
- `schema.py:17` — referência de documentação, não código.

### 8.4 Limites confirmados

- Nenhum consumidor de `PublicWorkoutLoadLog` existe fora de `public_workouts/`
  e `student_app/` — confirma a fronteira D.00 (modelo próprio, nunca
  vazado pra outro app).
- Nenhum registro em `public_workouts/admin.py` pra este model.
- Nenhum `management/commands/*.py` toca o model diretamente.
- Nenhum template além de `workout.html` usa `load_chart_points`,
  `personal_record`, `todays_logged_weight` ou `movement_load_display`.
- Nenhum arquivo `.js` além de `load_tracker.js` grava carga; nenhum outro
  lê pra montar gráfico (o gráfico de avaliação física —
  `assessments.js`/silhueta — é dado diferente, fora de escopo).

**Conclusão da varredura (atualizada na Revisão 6):** o mapa de 7
consumidores do §8.1 (5 exigem mudança de código, 2 — `build_weekly_review`
e `weekly_review_ai.py` — herdam o fix de graça, verificado por leitura
completa, não suposição). Os 6 itens do §8.2 foram avaliados e excluídos
com motivo, não esquecidos — dois deles (`todays_logged_weight`,
`week_overview`) só entraram nesta rodada, depois de eu ter proposto por
engano um fix pra `todays_logged_weight` que teria causado regressão de
UX real.

### 8.5 Duas pendências fechadas nesta varredura

1. **O índice novo só se justifica se o filtro for no banco.** A tabela já
   tem `(account, movement_slug, performed_on)`. Meu primeiro esboço de
   `progress_snapshot.py` filtrava `set_role` em Python depois de buscar
   tudo — nesse desenho, o índice novo seria custo de escrita sem ganho de
   leitura, porque a query real nem usa a coluna no `WHERE`. Corrigido:
   `progress_snapshot.py` agora filtra `set_role__in=...` direto na
   queryset (§7.5), e aí o índice `(account, movement_slug, set_role,
   performed_on)` do §7.2 passa a ser exatamente o que a query usa.
2. **Janela de 90 dias: a partir de hoje, não do último registro.** Decidido
   — se o aluno parou de registrar, a curva mostra o hiato real (espaço
   vazio à direita) em vez de esconder a inatividade comprimindo a janela
   pro último dado que existe. É a mesma lógica de nunca maquiar ausência
   de dado — layout consistente com o resto do plano.

## 9. Alternativas mais sofisticadas consideradas — e por que não entram agora

Quatro pontos onde existe uma versão tecnicamente mais elaborada do que a
proposta neste plano. Registradas aqui pra não serem redescobertas do zero
quando o volume de dado ou a necessidade de produto justificar — nenhuma
delas resolve um problema que exista hoje, com 10 contas e algumas dezenas
de registro por movimento.

### 9.1 `Window` function (SQL) em vez de agrupamento em Python

`effective_top_sets_by_day` (§7.4) agrupa "mais recente por dia" com um
`dict` em Python. A alternativa é uma `Window(expression=RowNumber(),
partition_by=[F('performed_on')], order_by=F('created_at').desc())` do
Django, filtrando `row_number=1` — resolveria no banco, sem trazer todas as
linhas pra memória. **Não adotado agora**: com dezenas de registros por
movimento por conta, a diferença de custo é irrelevante, e o `dict` em
Python é mais fácil de ler e testar sem depender de comportamento de
`Window` function por engine. Reconsiderar se o histórico por movimento
crescer pra milhares de linhas (não é o caso previsível no curto prazo).

### 9.2 `QuerySet`/`Manager` customizado em vez de módulo de função solta

Uma alternativa mais "Django idiomático" pra `progress_eligibility.py`
seria um manager customizado —
`PublicWorkoutLoadLog.objects.eligible_for_curve()` como método de
queryset encadeável, em vez de uma função de módulo que recebe a queryset
de fora. **Não adotado**: dois motivos reais, não só estilo. Primeiro, o
resto do módulo (`services.py`, `one_rep_max.py`) já usa funções soltas
consistentemente — um manager customizado seria o único lugar do domínio
com esse padrão, quebrando a convenção local sem ganho claro. Segundo, e
mais importante: `personal_record` recebe **dict serializado**, não
queryset — um método de manager não ajuda nesse caso de qualquer jeito,
então adotar o padrão só resolveria parte dos consumidores.

### 9.3 Captura de 3 estados (aquecimento / normal / máximo) em vez de 2

O plano atual usa toggle binário (§2.3.6) e defere `max_set` pra "escolha
explícita futura" — ou seja, `eligible_for_personal_record` nunca vai ter
`max_set` de verdade pra somar até essa "escolha futura" ser construída.
Uma alternativa real: 3 estados já nesta entrega — "Aquecimento" / "Série
principal" (padrão) / "Foi o meu máximo hoje" — captura `max_set`
genuinamente a partir de agora, sem esperar uma onda futura.
**Considerado, não adotado nesta entrega:** um terceiro estado exige
decidir a linguagem certa pra não confundir o aluno (o próprio §2.3.5 já
rejeitou inferir `max_set` por RIR — expor o conceito explicitamente na UI
tem o risco inverso, do aluno marcar "foi meu máximo" toda vez que uma
série for difícil, inflando `max_set` do mesmo jeito que a inferência por
RIR faria, só que por escolha do usuário em vez do sistema). Fica como
próxima iteração natural, não bloqueador desta.

### 9.4 `CHECK CONSTRAINT NOT VALID` + `VALIDATE CONSTRAINT` em vez de `AlterField(null=False)`

A migration C (§7.2/§7.12) usa `AlterField` direto pra `null=False`. Em
tabela grande, isso pode segurar lock de escrita durante o scan de
validação. A técnica de zero-downtime do Postgres é adicionar a constraint
como `NOT VALID` primeiro (não escaneia, lock rápido) e `VALIDATE
CONSTRAINT` depois, em transação separada (escaneia, mas com lock mais
leve). **Não adotado**: a tabela tem dezenas de linhas, não milhões — o
`AlterField` direto é instantâneo nesse volume. Documentado aqui como a
técnica certa se este model crescer muito antes de qualquer migration
futura precisar do mesmo tipo de mudança.

### 9.5 Identidade de sessão real (`training_session_id`/`set_sequence`) e `captured_at_client`

A sofisticação futura mais valiosa não é nenhuma das anteriores — é
resolver identidade de sessão e ordem real dos eventos, apontada na
revisão desta rodada:

1. **`training_session_id` + `set_sequence`.** `effective_top_sets_by_day`
   (§7.4) resolve "qual registro do dia vale" assumindo que o mais recente
   é sempre a correção da intenção final do aluno. Isso é uma aproximação
   boa, não uma verdade absoluta — não distingue "corrigi um erro de
   digitação" de "fiz duas séries principais reais no mesmo dia" (ex.:
   treino dividido em duas sessões). Só um identificador de sessão de
   treino + sequência de série dentro dela resolve isso de verdade.
2. **`captured_at_client`.** `created_at` é hoje o instante em que o
   SERVIDOR recebeu o dado (sync), não o instante em que o aluno de fato
   apertou salvar — o outbox offline existe exatamente pra permitir
   registrar sem rede. Alguém offline por 2 dias e sincronizando depois
   pode ter a ORDEM de `created_at` divergindo da ordem real dos eventos.
   V1 (este plano) aceita `created_at` como aproximação — correto pro uso
   comum (um aparelho, majoritariamente online), mas é uma limitação
   conhecida, não uma verdade garantida sob uso offline prolongado ou
   múltiplos aparelhos. Campo futuro:
   `performed_on` (dia do treino) / `captured_at_client` (instante real do
   registro) / `created_at` (instante de sincronização) — três conceitos
   hoje comprimidos em dois campos.

**Não adotado agora**: nenhum dos dois é necessário pro volume e pro
padrão de uso atual (10 contas, um aparelho por aluno na prática). Vira
prioridade se o Curva expandir pra múltiplas séries de trabalho reais por
dia ou uso offline prolongado se tornar comum — não antes disso.

### 9.6 Snapshot materializado ou `Window` function no banco — só com volume real

A evolução correta depois do snapshot em lote (§7.5) seria materializar
uma tabela de projeção de progresso, ou mover o agrupamento por dia pra
`Window` function no banco (mesmo raciocínio do §9.1, agora void pelo
batch). **Não há motivo pra evento distribuído, microserviço ou CQRS
completo agora** — isso só faria sentido com milhares de log por conta,
não é o caso previsível no curto prazo.
