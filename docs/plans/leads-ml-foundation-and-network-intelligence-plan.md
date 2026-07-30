<!--
ARQUIVO: plano de execucao da frente de ML de leads/vendas — correcao da fundacao e expansao para inteligencia de rede cross-tenant.

TIPO DE DOCUMENTO:
- plano de execucao ativo

AUTORIDADE:
- alta para a frente de ML de leads e para a trilha de inteligencia de rede
- subordinado a [../architecture/operational-intelligence-ml-layer.md](../architecture/operational-intelligence-ml-layer.md) em tese arquitetural

DOCUMENTO PAI:
- [../architecture/operational-intelligence-ml-layer.md](../architecture/operational-intelligence-ml-layer.md)

DOCUMENTOS IRMAOS:
- [leads-ml-technical-execution-guide.md](leads-ml-technical-execution-guide.md) — COMO implementar cada onda (assinaturas, migrations, testes)
- [../reference/lead-attribution-ml-foundation.md](../reference/lead-attribution-ml-foundation.md)
- [../architecture/finance-churn-ml-foundation.md](../architecture/finance-churn-ml-foundation.md)
- [growth-engine-activation-plan.md](growth-engine-activation-plan.md)
- [scale-transition-20-100-open-multitenancy-plan.md](scale-transition-20-100-open-multitenancy-plan.md)

QUANDO USAR:
- quando for retomar ou executar qualquer onda da frente de ML de leads
- quando a duvida for o que e cross-tenant, o que e per-tenant, e o que nunca pode sair do schema do box
- quando for decidir se um numero de conversao pode ir para a tela

POR QUE ELE EXISTE:
- a auditoria adversarial de 2026-07-28 (39 achados, 6 dimensoes, verificacao independente) provou que a Fase 1 de leads esta incompleta e que a leitura de canal em producao mede a populacao errada.
- registra a decisao de NAO construir a Fase 2 completa (score/modelo) agora: com o volume de uma box, celula canal x janela nao sai do ruido em menos de um ano.
- formaliza a resposta estrategica ao problema de volume: inteligencia de rede — padroes agregados compartilhados entre boxes, com correcao local progressiva.

O QUE ESTE ARQUIVO FAZ:
1. registra o estado real da fundacao (o que a auditoria confirmou).
2. define o Trilho A: correcao da fundacao em 6 ondas pequenas e verificaveis.
3. define o Trilho B: inteligencia de rede cross-tenant em 3 ondas, com gates de ativacao.
4. lista as decisoes que sao do dono do produto, com recomendacao e default assumido.

PONTOS CRITICOS:
- dado cru de aluno/lead NUNCA sai do schema do tenant. O que viaja para o public e agregado anonimo com piso de contagem (k-anonimato).
- benchmark e prior de rede so publicam celula com N minimo; abaixo disso a celula e suprimida, nao zerada.
- Trilho B inteiro e gated: nao abre antes do Trilho A fechar e do numero de boxes justificar.
- ML nunca escreve verdade primaria (regra-mestra do documento pai).
- ATIVO.
-->

# ML de Leads — fundacao honesta e inteligencia de rede

## Tese central

A frente de ML de leads tem dois problemas de natureza diferente:

1. a fundacao de dado esta incompleta e a leitura atual mente na tela (problema de engenharia, corrigivel em ondas pequenas)
2. uma box sozinha nunca gera volume estatistico para score de lead (problema estrutural, que engenharia local nao resolve)

O problema 2 tem uma unica saida honesta: **a rede**. O OctoBox e multi-tenant; cada box e pequena, mas a soma das boxes nao e. Padroes agregados da rede (nunca dados crus) viram conhecimento inicial de cada box, e a leitura local corrige o padrao da rede conforme o dado proprio acumula.

Em linguagem curta:

1. primeiro parar de medir errado (Trilho A)
2. depois medir junto (Trilho B)
3. score e modelo so quando a rede der volume — nao antes

## O que a auditoria provou (2026-07-28)

Resumo dos 4 pontos onde a fundacao quebra de verdade. Detalhe completo nos achados da auditoria; aqui fica o essencial com ancora de codigo:

1. **Nao existe trilho de job multi-tenant.** Comandos agendados rodam no schema `public` contra tabelas TENANT (`boxcore` esta em `TENANT_APPS`, [../../config/settings/base.py](../../config/settings/base.py)). O unico padrao correto do repo e `finance/reconciliation.py` (itera `Box` + `schema_context`) e nunca foi replicado. Sem isso, qualquer job de features explode ou roda para zero tenants em silencio.
2. **Os dois eixos da atribuicao sao um eixo so.** `onboarding/intake_actions.py` sobrescreve `source` com `derive_operational_source(canal_declarado)` — a "porta de entrada" e calculada a partir da "rua de origem", contradizendo o contrato do doc de referencia. Canal `event` grava `operational_source='whatsapp'` (fato falso, exportado como label Prometheus). Canal instagram/site/google/meta grava `source=IMPORT`, ligando o botao de convite pensado para listas importadas.
3. **O funil nao tem desfecho datado.** `StudentIntake` so tem `created_at`/`updated_at`. Conversao e recuperavel via `AuditEvent action='student_intake_converted'`; **rejeicao nao deixa rastro nenhum** — cada semana parada apaga a classe negativa do dataset.
4. **A unica agregacao por canal mede a populacao complementar da que interessa.** `onboarding/queries.py` filtra `linked_student__isnull=True`: todo lead convertido some do agregado. Canal com 10 leads e 8 conversoes aparece como 2; canal com 10 leads e 0 conversoes aparece como 10. O KPI se chama "Captacao".

Colaterais com dano vivo: vazamento de cache cross-tenant em `access/shell_actions.py` (chave sem schema; helper correto pronto em `control/cache.py` sem uso) e taxa de conversao sem coorte exibida ao dono em `student_identity/recommendations/invitation_operations_recommendations.py`.

## Inventario completo dos achados

Registro integral para que nada se perca entre sessoes. 39 achados brutos, 2 refutados,
37 sobreviventes. A coluna ONDA diz onde cada um e resolvido; `—` significa
fora do caminho critico (backlog consciente, nao esquecimento).

### Erros de leitura que a auditoria cometeu (registrados para nao voltarem)

1. **REFUTADO — "a atribuicao se perde na conversao lead->aluno".** Falso no caminho principal:
   `catalog/student_form_context.py` pre-preenche o canal a partir do `raw_payload` do intake e
   `catalog/form_definitions/student_forms.py` torna o campo obrigatorio. O buraco real e menor:
   os atalhos (convite por WhatsApp cria `Student` sem canal; checkout expresso).
2. **INFLADO — seis achados eram o mesmo bug.** Todos apontam para o filtro
   `linked_student__isnull=True` de `onboarding/queries.py`. E um defeito so, com seis narrativas.
   Tratar como seis itens de backlog inflaria o esforco em 6x.
3. **CORRIGIDO — "a conversao e irrecuperavel".** E recuperavel via
   `AuditEvent action='student_intake_converted'` (`students/infrastructure/django_audit.py`).
   O que nao tem rastro nenhum e a **rejeicao**.

### Bloqueante

| # | Arquivo | Achado | Onda |
|---|---|---|---|
| B1 | `operations/management/commands/run_due_nightly_lead_import_jobs.py` | Comando agendado roda no `public` contra tabela TENANT; sem trilho de job multi-tenant | 1 |

### Alto

| # | Arquivo | Achado | Onda |
|---|---|---|---|
| A1 | `onboarding/attribution.py` (`derive_operational_source`) | `operational_source` e funcao deterministica do canal declarado; canal `event` grava `whatsapp` (fato falso exportado ao Prometheus) | 3 |
| A2 | `onboarding/model_definitions.py` | `StudentIntake` sem historico de transicao; `updated_at` poluido por escrita nao-transicional (webhook de WhatsApp reescreve) | 4 |
| A3 | `onboarding/intake_invite_actions.py` | `linked_student` nao marca conversao — o convite ja o preenche e cria `Student` com `status=LEAD` | 4 + decisao 1 |
| A4 | `access/shell_actions.py` | Vazamento de cache cross-tenant (chave sem schema) em todo request autenticado, incluindo `pending_intakes` | 2 |
| A5 | `catalog/finance_snapshot/snapshot.py` | Exemplar do churn ja carrega agregacao O(historico) em Python 2x por request, com coluna JSON — nao replicar | 6 (como anti-padrao) |
| A6 | `onboarding/queries.py` | Radar mede backlog aberto, nao captacao — denominador exclui quem converteu | 5 |
| A7 | `student_identity/recommendations/invitation_operations_recommendations.py` | Taxa de conversao exibida ao dono: razao entre populacoes disjuntas, sem coorte, contando pageviews; pode passar de 100% e dispara alerta | 2 (rotular) / 6 (coorte) |

### Medio

| # | Arquivo | Achado | Onda |
|---|---|---|---|
| M1 | `students/infrastructure/django_intakes.py` | Conversao nao reconcilia atribuicao no adapter (so o form da UI faz) — atalhos ficam sem canal | 4 |
| M2 | `onboarding/queries.py` | Filtro "Resolvido" e estruturalmente vazio: intersecta `[APPROVED, REJECTED]` com base que ja excluiu ambos | 5 |
| M3 | `onboarding/intake_actions.py` | `captured_at` nunca preenchido em producao; teste esconde a lacuna | 3 |
| M4 | `auditing/services.py` | Audit log nao registra transicao de intake e escreve best-effort silencioso | 4 |
| M5 | `communications/model_definitions/whatsapp.py` | Sem elo `WhatsAppContact <-> StudentIntake`; nao ha registro de primeiro contato do lead | 4 (`first_contacted_at`) |
| M6 | `onboarding/attribution.py` | Fallback legado fabrica canal para linha que declarou ausencia de origem | 3 (procedencia) |
| M7 | `onboarding/attribution.py` | Camada de qualificacao posterior sem chamador de producao (`merge_qualification_response`) | decisao 4 |
| M8 | `catalog/form_definitions/student_forms.py` | Zero dos 6 campos obrigatorios de saida de ML; `source_confidence` escrito na verdade primaria a partir de `form.clean()` | 3 + 6 |
| M9 | `onboarding/queries.py` | 3 dos 11 canais canonicos sem card nem bucket: lead "Evento" some sem cair em `missing` | 5 |
| M10 | `docs/reference/lead-attribution-ml-foundation.md` | Doc aponta `onboarding/views.py` como casa da atribuicao; o arquivo real e `intake_actions.py` | 3 (doc) |
| M11 | `operations/services/contact_importer.py` | Trilha de maior volume de leads ignora o contrato: cria intake sem `raw_payload` de atribuicao | 3 |
| M12 | `catalog/finance_snapshot/` | Camada de ML do churn vive dentro de `catalog/` e persiste dado de treino dentro do GET | 6 (nascer fora) |
| M13 | `onboarding/queries.py` | Radar materializa todo `raw_payload` em Python a cada request; periodo default `all` | 5/6 (coluna materializada) |
| M14 | `onboarding/model_definitions.py` | Nenhum indice sustenta as agregacoes: `source` e `created_at` sem indice, zero composto | 6 |
| M15 | `students/domain/acquisition_resolution.py` | `unidentified`/`legacy` tratados como canais reais — assimetria gera conflito falso e descarta declaracao boa | 3 + decisao 6 |
| M16 | `students/domain/acquisition_resolution.py` | `source_confidence` nao calibrado, conflata corroboracao com fonte unica — nao serve de peso estatistico | 6 (estratificar, nao ponderar) |
| M17 | `onboarding/forms.py` | Sem deduplicacao de lead no balcao: mesmo telefone gera N linhas e infla o denominador de N canais | decisao 7 |
| M18 | `onboarding/model_definitions.py` | Sem `converted_at`/`rejected_at`: impossivel montar janela de maturacao; censura a direita sem correcao | 4 |

### Baixo

| # | Arquivo | Achado | Onda |
|---|---|---|---|
| L1 | `onboarding/attribution.py` | `LEGACY_SOURCE_TO_ACQUISITION_CHANNEL` converte import CSV em "Indicacao" — inferencia contada como declaracao | 3 |
| L2 | `onboarding/attribution.py` | Bloco `ml_features` e perna de `qualification` sao codigo morto (zero leitores) | 3 (remover) / decisao 4 |
| L3 | `onboarding/model_definitions.py` | Criptografia quebra join intake<->aluno; indices btree inuteis sobre ciphertext. `phone_lookup_index` e a unica chave de join valida | 6 (declarar) |

## Trilho A — fundacao honesta (Ondas 1-6)

> A implementacao tecnica de cada onda (assinaturas, esqueleto de codigo, migrations,
> nomes de teste, comando de verificacao e rollback) fica em
> [leads-ml-technical-execution-guide.md](leads-ml-technical-execution-guide.md).
> Este documento define O QUE e POR QUE; o guia define COMO.

### Onda 1: trilho de job por tenant (desbloqueia tudo)

1. objetivo: existir um jeito unico e testado de rodar calculo agendado em todos os schemas
2. arquivos: novo `shared_support/management/tenant_sweep.py` replicando o padrao de `finance/reconciliation.py`; migrar `finance/management/commands/evaluate_finance_followups.py`, `operations/management/commands/run_due_nightly_lead_import_jobs.py`, `jobs/management/commands/run_due_async_job_retries.py`
3. pronto quando: os tres comandos rodam do `public` sem `ProgrammingError` e existe teste que quebra se um comando agendado novo nao usar o wrapper
4. nao fazer: nenhuma feature de lead, nenhum job novo

### Onda 2: higiene de fronteira e parar de mentir na tela (paralela a Onda 1)

1. objetivo: fechar o vazamento cross-tenant e tirar de producao numero que nao mede o que diz medir
2. arquivos: `access/shell_actions.py` passa a usar `control.cache.tenant_cache_key`; copy do radar e KPI "Captacao" viram "fila aberta por canal"; alerta da taxa de conversao de convites desativado ate existir coorte
3. pronto quando: box B nao le contador do box A, e nenhuma tela apresenta razao de eventos como taxa de conversao
4. nao fazer: nao reescrever a metrica como coorte agora (Onda 6); nao mexer no queryset do radar ainda

### Onda 3: desfazer a colinearidade e fechar a taxonomia

1. objetivo: `operational_source` voltar a significar "por onde o registro entrou"
2. arquivos: `onboarding/intake_actions.py` (parar de sobrescrever `source`; gravar origem real do canal de captura; passar `captured_at`); `onboarding/attribution.py` (isolar `derive_operational_source` no caminho legado, cobrir os 11 canais, erro em canal nao mapeado; `extract_acquisition_channel` devolve procedencia declarado/inferido/ausente); `operations/services/contact_importer.py` (gravar bloco attribution no import em lote)
3. pronto quando: lead "Evento" digitado no balcao grava `operational_source='manual'`, `declared_channel='event'`, `captured_at` preenchido
4. nao fazer: nao backfillar dado antigo (marcar `schema_version=2` e conviver com as duas formas); nao tocar em `Student`

### Onda 4: marcadores de desfecho (a lacuna que sangra por dia parado)

1. objetivo: datar entrada e saida do funil
2. arquivos: `onboarding/model_definitions.py` ganha `first_contacted_at`, `converted_at`, `rejected_at` (nullable, db_index) e `conversion_kind`; helper unico de transicao chamado por `onboarding/facade.py`, `onboarding/intake_invite_actions.py`, `students/infrastructure/django_intakes.py`; audit event em toda transicao; backfill de `converted_at` via `AuditEvent action='student_intake_converted'`
3. pronto quando: toda mutacao de `status` passa pelo helper e `rejected_at` existe para toda rejeicao nova
4. nao fazer: NAO criar tabela de historico versionado completo — para o volume de uma box, colunas denormalizadas entregam o valor com fracao do custo

### Onda 5: separar leitura operacional de leitura analitica

1. objetivo: existir uma query que enxergue o funil inteiro
2. arquivos: `onboarding/queries.py` — `queue_queryset` mantem o recorte de fila; nasce `analytics_queryset` sem recorte de vinculo/status, janelado por `created_at`; cards derivados de `ACQUISITION_CHANNEL_MODEL_CHOICES` com invariante `soma(cards) + missing == total`; filtro "Resolvido" passa a trocar a base em vez de intersectar
3. pronto quando: teste com um intake approved, um rejected e um "Evento" retorna linhas no filtro Resolvido e fecha a soma dos cards
4. nao fazer: nada de ML aqui; nada de persistencia dentro do GET (nao replicar o padrao de `catalog/finance_snapshot/snapshot.py` que persiste durante render)

### Onda 6: feature layer minimo por tenant

1. objetivo: data product deterministico, versionado, computado por job (via Onda 1)
2. arquivos: novo pacote `intelligence/` como TENANT app, comecando por `intelligence/leads/`
3. saida por canal e por janela: `captured_total`, `converted_total`, `rejected_total`, `open_total`, mediana de dias captura->conversao, cobertura de atribuicao — tudo carimbado com `rule_version`, `computed_at`, `input_window`, `is_recommendation=False` (contrato do documento pai)
4. pronto quando: o mesmo job rodado duas vezes sobre o mesmo banco produz o mesmo resultado; taxas estratificadas por bucket de confianca, nao ponderadas
5. nao fazer: nenhum score, nenhuma probabilidade, nenhum modelo, nenhuma escrita em `StudentIntake`/`Student`

## Trilho B — inteligencia de rede cross-tenant (Ondas 7-9)

### A ideia em forma precisa

Duas capacidades, nesta ordem de maturidade:

1. **Benchmark de rede**: cada box ve seus numeros ao lado da mediana anonima da rede ("seu Instagram converte 12%; a mediana de boxes do seu porte e 18%"). Valor imediato, zero modelo.
2. **Priors com correcao local (o "ir corrigindo")**: box nova comeca com o padrao agregado da rede como conhecimento inicial e, conforme o dado proprio acumula, a leitura local ganha peso ate dominar. O nome tecnico disso e *shrinkage* (partial pooling):

```
leitura_ajustada = (n_local * taxa_local + m * prior_da_rede) / (n_local + m)
```

onde `n_local` e o volume proprio da box e `m` e o peso do prior (ex.: 10 — documentado e versionado). Com `n_local=0` (box nova), a leitura E o prior da rede. Com `n_local` grande, o prior vira ruido de fundo. A transicao e continua, auditavel e sem modelo caixa-preta.

Isso tambem **corrige um defeito ja conhecido do churn**: o piso `min_realized_count=5` em `catalog/finance_snapshot/ai/learning.py` e uma gambiarra de amostra pequena. Com prior de rede, celula pequena deixa de ser descartada ou superconfiante — ela e encolhida na direcao do padrao coletivo.

### Principios inegociaveis

1. dado cru de aluno ou lead NUNCA sai do schema do tenant — nem nome, nem telefone, nem linha individual
2. o que sobe para o `public` e agregado por celula (segmento x canal x janela), e so quando a celula tem `N >= k` (piso k-anonimo, sugerido k=10)
3. box tem opt-out da contribuicao para a rede (decisao de produto — ver secao de decisoes)
4. todo prior publicado carrega `prior_version`, `computed_at`, `input_window`, `box_cohort` e N de origem
5. leitura que usa prior de rede exibe isso explicitamente (`is_network_prior=True`) — a box sabe quando esta lendo a rede e quando esta lendo a si mesma
6. ML nao escreve verdade primaria — prior recomenda leitura, nunca muta dado operacional

### Onda 7: perfil/segmento do aluno (per-tenant)

A "categoria" do aluno que a conexao lead->aluno precisa nao existe hoje — `Student.status` e ciclo de vida (lead/active/paused/inactive), nao segmento. Esta onda cria o data product de segmento em baixa cardinalidade, dentro de `intelligence/`:

1. dimensoes candidatas (todas ja existem como materia-prima): plano e ciclo de cobranca (`Enrollment.plan` -> `MembershipPlan.billing_cycle`, `sessions_per_week`), comportamento de pagamento (pontual/atrasado, via `finance/overdue_metrics.py`), faixa etaria (`Student.birth_date`), canal resolvido de aquisicao (`Student.resolved_acquisition_source`)
2. saida: `student_segment` versionado por regra transparente (ex.: `plano_trimestral+pontual+30-40`), NUNCA por clustering opaco nesta fase
3. pronto quando: todo aluno ativo tem segmento computavel por job, reproduzivel, com `rule_version`
4. nao fazer: nao gravar segmento no model `Student` (e leitura derivada, vive no data product)

### Onda 8: hub de rede (SHARED app no public)

1. novo app `intelligence_network` em `SHARED_APPS` — o precedente de camada cross-box ja existe (`student_identity` e SHARED)
2. modelos no `public` SEM FK para tabelas de tenant (licao do Sprint 2: FK cross-schema e proibida) — chaves denormalizadas: `box_slug`, `box_cohort`, `segment_key`, `channel`, `window`
3. o job da Onda 1 varre os tenants, le os data products das Ondas 6-7 e faz upsert das celulas que passam o piso k no hub
4. cohort de box (porte por alunos ativos, ticket mediano, regiao) entra como dimensao — boxes heterogeneas nao podem ser mediadas cegamente; o benchmark compara box com seu cohort, nao com a rede inteira
5. primeira superficie: benchmark anonimo no radar de canais ("voce vs mediana do seu cohort"), com N exibido e celula suprimida abaixo do piso
6. pronto quando: uma box le a mediana do proprio cohort sem conseguir inferir nenhuma box individual
7. nao fazer: nenhum prior aplicado ainda — so leitura comparativa

### Onda 9: priors e correcao local

1. o hub passa a publicar priors versionados por (cohort, segmento, canal): taxa de conversao esperada, tempo mediano ate conversao, taxa de retencao 90d pos-conversao
2. as leituras per-tenant (Onda 6) passam a exibir a versao ajustada por shrinkage ao lado da crua, com o peso do prior documentado
3. box nova (cold start): radar e fila nascem com prior do cohort mais proximo, marcados `is_network_prior=True`, e convergem para o dado local conforme `n_local` cresce — este e o "automaticamente ir corrigindo para novos boxes"
4. aplicacao retroativa no churn: `build_recommendation_historical_score_map` pode partir do prior de rede em vez de 0.0 para acao sem historico local
5. pronto quando: uma box nova exibe leitura de canal util no dia 1, rotulada como herdada da rede, e um teste prova a convergencia (prior domina com n=0, local domina com n grande)
6. nao fazer: ainda nenhum modelo probabilistico — shrinkage de taxas e o teto desta onda

### Fechamento do loop lead -> aluno -> categoria -> retencao

Com Ondas 4+7 fechadas, a pergunta certa vira computavel: **nao "qual canal traz mais leads", mas "qual canal traz alunos que ficam"**. O join per-tenant e: `StudentIntake.converted_at` -> `Student` -> segmento (Onda 7) -> retencao/churn (trilha financeira ja existente). Isso conecta as duas trilhas de ML do produto: canal de aquisicao vira feature de risco de churn, e risco de churn por segmento vira qualidade de canal. E o que o documento pai chama de "primeira trilha oficial" — atribuicao, conversao e retencao lidas como um circuito so.

### Gates de ativacao do Trilho B

Alinhado a [growth-engine-activation-plan.md](growth-engine-activation-plan.md):

1. Onda 7 abre apos Ondas 4-5 fecharem (precisa de `converted_at` e leitura analitica)
2. Onda 8 abre com Trilho A completo + numero de boxes ativos suficiente para o piso k nao suprimir tudo (piloto viavel no beta fechado de ~20 boxes para celulas grossas; benchmark fino pede mais)
3. Onda 9 abre apos meses de `converted_at`/`rejected_at` coletados com honestidade + Onda 8 estavel
4. score/modelo de verdade (Fase 3 do documento pai) so depois de 6 meses de desfecho datado E rede ativa

## Decisoes do dono (com recomendacao)

1. **Definicao oficial de "lead convertido"** — candidatos: `linked_student` nao-nulo (contaminado pelo convite), `intake.status='approved'` (canonico, escritor unico), `Student ACTIVE + Enrollment`. Recomendacao e DEFAULT ASSUMIDO neste plano: `approved` = conversao comercial; `ACTIVE+Enrollment` = conversao de receita, reportada como camada separada. Nunca `linked_student`.
2. **Opt-in ou opt-out da rede** — a box contribui com agregados por padrao? Recomendacao: opt-out (contribui por padrao, pode sair), com transparencia no onboarding do box. E o modelo que faz a rede ter valor cedo.
3. **Benchmark visivel para todos ou diferencial de plano** — decisao comercial pura. Recomendacao: nas primeiras ondas, visivel para todos (constroi o habito e o moat); monetizacao decide depois.
4. **O convite por WhatsApp continua restrito a `IntakeSource.IMPORT`?** — apos Onda 3, leads de balcao que declaram Instagram deixam de ser elegiveis. Recomendacao: trocar o criterio para condicao explicita ("lead sem contato previo e com telefone").
5. **Lead some da fila ao ser convidado?** — hoje sim, via `linked_student__isnull=True`. Recomendacao: nao; criar estado `INVITED` que nao colapsa em resolvido.
6. **"Nao identificado" e resposta valida do aluno?** — hoje produz conflito falso na reconciliacao. Recomendacao: remover; "nao sei" e ausencia de declaracao.
7. **Duplicata de lead no balcao: bloquear ou fundir?** — recomendacao: avisar e oferecer fusao; nunca bloquear a recepcao.
8. **Piso de N para publicar taxa** — recomendacao: suprimir o numero abaixo de 20 conversoes na celula local (benchmark de rede usa piso k=10 por celula agregada) e sempre exibir o N ao lado do percentual.

## O que NAO fazer em nenhuma onda

1. nao subir linha individual de lead/aluno para o `public`
2. nao treinar modelo probabilistico antes da Fase 3 do documento pai
3. nao usar clustering opaco para segmento enquanto regra transparente resolver
4. nao criar FK cross-schema
5. nao persistir dado de treino dentro de request GET
6. nao apresentar prior de rede como se fosse dado da propria box

## Riscos

1. **Heterogeneidade entre boxes**: mediar Instagram de uma box premium de capital com uma box de bairro do interior produz prior enganoso. Mitigacao: cohort como dimensao obrigatoria da Onda 8 em diante.
2. **Piso k suprimindo tudo no inicio**: com poucas boxes, celulas finas (segmento x canal) nao passam o piso. Mitigacao: comecar com celulas grossas (so canal, so cohort) e refinar conforme a rede cresce.
3. **Prior desatualizado**: padrao de rede muda (ex.: canal decai). Mitigacao: `input_window` rolante e `prior_version` — prior velho expira, nao acumula.
4. **Interpretacao errada pelo dono**: benchmark lido como meta ("tenho que bater 18%"). Mitigacao: copy explicita de comparacao, nunca de meta, e N sempre visivel.
5. **LGPD**: agregado anonimo com piso k e a fronteira segura; qualquer coisa alem (ex.: recomendacao individual cross-box) exige revisao juridica antes de sair do papel.
