<!--
ARQUIVO: plano pratico de banco de dados e PostgreSQL para fechar a Fase 1 do OctoBox por ondas curtas.

TIPO DE DOCUMENTO:
- plano arquitetural e operacional de banco

AUTORIDADE:
- alta para movimentos de schema, isolamento, restore e observabilidade na Fase 1

DOCUMENTOS IRMAOS:
- [scale-transition-20-100-open-multitenancy-plan.md](scale-transition-20-100-open-multitenancy-plan.md)
- [phase1-closed-beta-20-boxes-corda.md](phase1-closed-beta-20-boxes-corda.md)
- [unit-cascade-architecture-plan.md](unit-cascade-architecture-plan.md)
- [../rollout/first-box-production-execution-checklist.md](../rollout/first-box-production-execution-checklist.md)
- [../rollout/postgres-homolog-provisioning-checklist.md](../rollout/postgres-homolog-provisioning-checklist.md)
- [../rollout/postgres-homolog-restore-runbook.md](../rollout/postgres-homolog-restore-runbook.md)

QUANDO USAR:
- quando a duvida for como transformar a estrategia atual de banco em execucao pratica de Fase 1
- quando precisarmos organizar movimentos de schema, observabilidade, restore e isolamento por ondas pequenas
- quando quisermos decidir o que entra agora, o que fica em background e o que deve ser explicitamente adiado

POR QUE ELE EXISTE:
- evita tratar arquitetura de banco como uma conversa abstrata ou opiniao solta
- traduz a estrategia de isolamento forte por box em entregas verificaveis
- reduz o risco de abrir o primeiro box com banco “bonito no papel” e fraco em incidente real

O QUE ESTE ARQUIVO FAZ:
1. consolida a leitura atual do banco do OctoBox para a Fase 1
2. define principios e nao-objetivos de banco
3. organiza os movimentos em ondas curtas e aplicaveis
4. registra gates, failure checks e backlog adiado para nao inflar escopo

PONTOS CRITICOS:
- este plano nao autoriza multitenancy aberto na Fase 1
- este plano nao autoriza migration destrutiva sem restore e rollback ensaiados
- `AuditEvent` pode servir como trilha rica agora, mas nao deve virar o read model operacional final
-->

# Plano SQL Fase 1 - Ondas Praticas

## Tese central

Na Fase 1, o banco do OctoBox deve operar como:

1. `single-tenant por box no runtime`
2. `tenant-ready nos contratos e metadados`
3. `barato de restaurar`
4. `facil de depurar`
5. `forte contra mistura acidental de dados`

Em linguagem simples:

1. cada box ainda mora na sua casa
2. mas ja vamos padronizar numero da casa, etiqueta do quadro de luz e manual do encanamento
3. assim, no futuro, da para virar condominio sem quebrar o piso inteiro

## Leitura atual do banco

Hoje o OctoBox ja tem sinais importantes de maturidade para a Fase 1:

1. identidade de runtime por box via `BOX_RUNTIME_SLUG` e `runtime_namespace`
2. namespace de cache por box
3. healthcheck expondo `runtime_slug` e `runtime_namespace`
4. `intent_id`, `snapshot_version`, `ownership_scope` e contratos de cascata ja nascendo
5. PII sensivel protegida com campos criptografados e blind index pesquisavel
6. trilha de auditoria e idempotencia ja presentes
7. `student_identity` ja introduz semantica de `box_root_slug` sem ligar multitenancy aberto

Ao mesmo tempo, o banco ainda carrega uma nuance estrutural importante:

1. varios modelos vivem em apps reais como `students`, `finance`, `operations` e `communications`
2. porem boa parte do estado historico ainda preserva `app_label = 'boxcore'`
3. isso significa que ownership de codigo e ownership de schema ainda nao sao a mesma coisa

Traducao pratica:

1. o predio ja trocou varios moradores de andar
2. mas a matricula de alguns apartamentos ainda aponta para o bloco antigo
3. qualquer plano de banco que ignore isso vai errar a cirurgia

## Objetivo da Fase 1 no banco

Fechar a Fase 1 de banco para operar o primeiro box ate 20 boxes com:

1. isolamento forte
2. rollback simples
3. observabilidade minima confiavel
4. schema compreendido
5. base pronta para a Fase 2 sem migracao traumática

Sucesso significa:

1. o schema quente e seus indices criticos estao mapeados
2. o runtime de cada box esta identificavel e auditavel
3. backup e restore foram testados
4. queries quentes principais tem baseline
5. o banco suporta o piloto sem improviso

## Nao-objetivos desta fase

1. nao ligar multitenancy aberto
2. nao espalhar `tenant_id` em todo o schema sem necessidade
3. nao fazer reparticionamento complexo
4. nao abrir microservicos por causa de banco
5. nao trocar topologia por moda arquitetural

## Principios de execucao

1. schema atual primeiro, ideal futuro depois
2. additive migration vence destructive migration
3. restore ensaiado vence confianca abstrata
4. indice certo vence tuning folclorico
5. isolamento completo vence isolamento pela metade
6. medir antes de densificar

## Frentes de dados mais sensiveis

### 1. Cadastro e identidade

Arquivos-base:

1. `students/model_definitions.py`
2. `onboarding/model_definitions.py`
3. `student_identity/models.py`

Risco principal:

1. mistura entre identidade do aluno, identidade do canal e identidade do box

### 2. Financeiro

Arquivos-base:

1. `finance/model_definitions.py`

Risco principal:

1. fila quente com leituras pesadas, cobranças concorrentes e risco de estresse em `Payment` e `FinanceFollowUp`

### 3. WhatsApp e integrações

Arquivos-base:

1. `communications/model_definitions/whatsapp.py`
2. `shared_support/models.py`

Risco principal:

1. duplicidade, webhook repetido, lookup de PII e idempotencia quebrada

### 4. Operacao e auditoria

Arquivos-base:

1. `operations/model_definitions.py`
2. `auditing/model_definitions.py`

Risco principal:

1. usar auditoria como muleta definitiva para leitura quente da operacao

## Ondas de execucao

## Onda 0 - Mapa real do banco

### Objetivo

Parar de discutir o banco por intuicao e congelar a fotografia viva da Fase 1.

### Entregas

1. inventario oficial das tabelas quentes
2. mapa de joins e filtros quentes por superficie
3. tabela de “ownership de codigo vs ownership de schema”
4. lista de constraints e indices criticos existentes

### Escopo minimo

1. `Student`
2. `StudentIntake`
3. `MembershipPlan`
4. `Enrollment`
5. `Payment`
6. `FinanceFollowUp`
7. `WhatsAppContact`
8. `WhatsAppMessageLog`
9. `ClassSession`
10. `Attendance`
11. `AuditEvent`
12. `IdempotencyKey`
13. `StudentIdentity`
14. `StudentBoxMembership`

### Failure checks

1. nao saber dizer quais tabelas suportam `manager`, `reception` e `finance`
2. nao saber onde existe PII criptografada e onde existe blind index
3. nao saber quais models ainda dependem do estado historico de `boxcore`

### Gate de saida

1. o time consegue explicar o schema atual sem contradicao
2. o time sabe quais pontos sao banco atual, ownership atual e intencao futura

## Onda 1 - Endurecimento de boundary e isolamento

### Objetivo

Garantir que o isolamento do box nao pare no cache.

### Entregas

1. checklist de namespace por box para cache, logs, exports e storage
2. padrao de naming por box/celula documentado
3. validacao de `runtime_slug` e `runtime_namespace` no deploy e no healthcheck
4. separacao conceitual documentada entre `runtime identity` e futura `tenant identity`

### Movimentos práticos

1. revisar todos os pontos em que arquivos exportados recebem nome, caminho ou download
2. revisar logging para garantir contexto minimo por box no payload de log
3. revisar jobs/imports para garantir que o artefato gerado e o evento carregam identidade do box
4. formalizar que `box_root_slug` nao e ainda o multitenancy aberto do produto

### Failure checks

1. cache por box existe, mas exportacao continua generica
2. logs nao permitem descobrir rapidamente de qual box veio o erro
3. runtime slug e tenant futuro sao tratados como se fossem a mesma coisa

### Gate de saida

1. cada artefato operacional quente sabe de qual box veio
2. um incidente consegue ser localizado por box sem investigacao artesanal

## Onda 2 - Restore, rollback e seguranca de schema

### Objetivo

Fazer o banco sobreviver ao primeiro susto.

### Entregas

1. backup inicial validado
2. restore real em homologacao isolada
3. checklist de rollback de aplicacao e banco
4. lista de migrations sensiveis da Fase 1
5. criterio formal para migrations additive vs destructive

### Movimentos práticos

1. ensaiar restore do dump em banco isolado
2. validar compatibilidade de restore com as migrations atuais
3. identificar migrations que mexem em blind index, uniqueness, auditoria e concorrencia otimista
4. criar regra operacional: nenhuma migration estrutural critica vai a producao sem caminho de volta descrito

### Failure checks

1. backup existe mas nunca foi restaurado
2. migration muda chave, unique ou indice sem plano de reversao
3. o time depende de memoria para recuperar producao

### Gate de saida

1. restore e rollback foram executados pelo menos uma vez com evidencia
2. o primeiro box pode sofrer incidente sem deixar cliente na mao

## Onda 3 - Queries quentes e baseline de performance

### Objetivo

Entender onde o banco respira mais forte antes de aumentar densidade.

### Entregas

1. baseline de queries quentes por superficie
2. shortlist de indices faltantes ou suspeitos
3. lista de consultas que devem ser lidas por snapshot e nao por improviso em view
4. criterio de p95 alvo para `manager`, `reception` e `finance hot paths`

### Movimentos práticos

1. mapear consultas de `manager`, `reception`, `owner` e `finance`
2. identificar filtros mais repetidos: `status`, `due_date`, `created_at`, `suggested_at`, `resolved_at`, `phone_lookup_index`, `box_root_slug`
3. verificar joins mais caros e N+1 escondidos
4. priorizar indices que ajudam leitura quente sem inflar escrita cedo demais

### Failure checks

1. o time so descobre gargalo depois do go-live
2. indice e criado por suposicao, sem query real por tras
3. payload de leitura cresce mais rapido que a estrategia de snapshot

### Gate de saida

1. existe baseline minima das consultas quentes
2. existe fila priorizada de tuning com justificativa real

## Onda 4 - Metadados tenant-ready sem ligar multitenancy

### Objetivo

Preparar o futuro sem ativar o futuro cedo demais.

### Entregas

1. tabela de metadados obrigatorios para flows criticos
2. uso consistente de `intent_id`, `action_kind`, `surface`, `subject_type`, `subject_id`
3. uso consistente de `snapshot_version` nos payloads quentes
4. estrategia documentada para introduzir `tenant identity` interna na Fase 2

### Movimentos práticos

1. endurecer `cascade_intent` e `cascade_resolution` como lingua de metadata operacional
2. garantir que as superficies quentes carreguem `snapshot_version` estavel
3. garantir que flows operacionais gravem metadados minimos na auditoria
4. definir criterios para quando `tenant_id` entra no schema de forma canônica, e quando ainda nao deve entrar

### Failure checks

1. o sistema quer virar multitenant sem metadado canônico suficiente
2. cada fluxo grava metadata com nomes diferentes
3. `AuditEvent` recebe tudo, mas sem padrao que permita transicao futura

### Gate de saida

1. a Fase 2 pode nascer por extensao, nao por reinvencao
2. o schema ja fala parte da lingua futura sem romper a topologia atual

## Onda 5 - Fechamento do primeiro box

### Objetivo

Amarrar banco, runtime e operacao num go-live seguro.

### Entregas

1. checklist de banco embutido no go-live do primeiro box
2. decisao oficial do limite inicial de densidade por servidor
3. criterio de “abrir nova celula” documentado
4. backlog priorizado do que fica para Fase 2

### Validacoes finais

1. `/api/v1/health/` responde com boundary coerente
2. restore e rollback ja foram ensaiados
3. queries quentes tem baseline minima
4. runtime e artefatos operacionais carregam identidade do box
5. o time consegue localizar falha por box, superficie e fluxo

## Ordem sugerida de execucao

1. Onda 0
2. Onda 1
3. Onda 2
4. Onda 3
5. Onda 4
6. Onda 5

Regra:

1. Onda 2 nao pode ser pulada
2. Onda 4 nao autoriza Fase 3; ela so prepara a tubulacao
3. Onda 5 so existe quando 0, 1, 2 e 3 estiverem verdes

## Riscos principais e como evitar

### 1. Isolamento pela metade

O que pode dar errado:

1. cache isolado, mas logs e exports cruzados

Como evitar:

1. tratar namespace por box como contrato transversal, nao detalhe de cache

### 2. Restore decorativo

O que pode dar errado:

1. backup existe, mas restore nunca foi testado

Como evitar:

1. homologacao com banco isolado e drill real documentado

### 3. Performance folclorica

O que pode dar errado:

1. criar indice no escuro ou culpar Postgres por problema de leitura montada errado

Como evitar:

1. baseline de queries quentes antes de tuning

### 4. Falsa preparacao para multitenancy

O que pode dar errado:

1. achar que `BOX_RUNTIME_SLUG` sozinho resolve tenant

Como evitar:

1. separar explicitamente `runtime identity`, `box identity` e futura `tenant identity`

## Backlog adiado para Fase 2

1. `tenant_id` canônico transversal no schema
2. roteamento por celula
3. Postgres dedicado por celula quando a carga pedir
4. control plane interno de boxes
5. read model operacional mais proprio e menos dependente de auditoria

## Definicao de pronto

Este plano pode ser considerado executado na Fase 1 quando:

1. o banco do primeiro box for compreendido, restauravel e observavel
2. o isolamento por box estiver inteiro o suficiente para nao misturar operacao
3. as queries quentes estiverem medidas
4. as migrations sensiveis tiverem criterio de seguranca
5. a Fase 2 puder comecar por extensao controlada, nao por cirurgia de emergencia
