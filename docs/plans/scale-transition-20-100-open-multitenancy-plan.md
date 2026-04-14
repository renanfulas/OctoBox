<!--
ARQUIVO: plano formal de transicao de escala do OctoBox entre beta fechado, crescimento por celulas e multitenancy aberto.

TIPO DE DOCUMENTO:
- plano de execucao arquitetural e operacional

AUTORIDADE:
- alta

DOCUMENTOS IRMAOS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/center-layer.md](../architecture/center-layer.md)
- [../architecture/signal-mesh.md](../architecture/signal-mesh.md)
- [unit-cascade-architecture-plan.md](unit-cascade-architecture-plan.md)
- [operational-contact-memory-migration-plan.md](operational-contact-memory-migration-plan.md)
- [phase1-closed-beta-20-boxes-corda.md](phase1-closed-beta-20-boxes-corda.md)

QUANDO USAR:
- quando a duvida for como crescer do beta fechado ate a plataforma sem trocar de filosofia no susto.
- quando precisarmos decidir o que deve existir agora, o que deve rodar em background e quais gates liberam cada fase.

POR QUE ELE EXISTE:
- evita que a escala seja tratada como opiniao ou impulso.
- separa crescimento de receita, crescimento de densidade e mudanca real de topologia.
- organiza a transicao para que a fase futura comece a ser preparada antes de virar urgencia.

O QUE ESTE ARQUIVO FAZ:
1. define as tres fases oficiais de escala do OctoBox.
2. descreve a topologia, o objetivo e os limites de cada fase.
3. documenta o trabalho invisivel que precisa acontecer em background desde o inicio.
4. estabelece gates, checklist e criterio de pronto por fase.

PONTOS CRITICOS:
- a Fase 3 muda a filosofia estrutural do sistema; ela nao pode nascer como improviso.
- a Fase 2 nao deve ser tratada como intervalo neutro; ela e a ponte real para a plataforma.
- `AuditEvent` nao deve virar o read model final da operacao.
-->

# Plano de transicao de escala 20 -> 100 -> 100+

## Tese central

O OctoBox nao deve crescer por salto cego.

Ele deve crescer por tres movimentos diferentes:

1. **Fase 1**: tracao com isolamento forte e beta fechado.
2. **Fase 2**: densidade controlada com isolamento medio e infraestrutura compartilhada.
3. **Fase 3**: plataforma com multitenancy aberto de verdade.

Em linguagem simples:

1. primeiro construimos casas separadas e confiaveis.
2. depois organizamos um condominio com servicos compartilhados.
3. por ultimo, se o volume justificar, subimos para um predio de apartamentos.

## Data-base deste plano

Este plano passa a valer a partir de **2026-04-13**.

Ele assume:

1. beta fechado como momento atual do produto.
2. necessidade de monetizar cedo sem abrir infraestrutura cedo demais.
3. preparacao silenciosa da arquitetura futura desde a Fase 1.

## Regra principal de transicao

A Fase 3 nao pode comecar na Fase 3.

Ela precisa comecar invisivelmente na Fase 1 e amadurecer na Fase 2.

Traducao direta:

1. a infraestrutura muda em ondas.
2. os contratos mudam cedo.
3. a topologia muda tarde.

## Fase 1 - Beta fechado ate 20 boxes

## Objetivo

Ganhar tracao, aprender com operacao real e sustentar beta fechado com alto controle.

## Topologia

1. 1 servidor principal.
2. isolamento forte por box.
3. sem conversa entre boxes.
4. deploy e recuperacao simples.

## O que significa sucesso na Fase 1

1. o sistema roda com previsibilidade.
2. o time entende o custo por box.
3. incidentes sao recuperaveis sem caos.
4. a base de contratos ja comeca a apontar para a escala futura.

## O que precisa existir antes do primeiro box

### Fundacao operacional minima

1. `intent_id` nos fluxos criticos.
2. `snapshot_version` em `manager`, `reception` e `owner`.
3. metadata canonica em auditoria.
4. `action_kind`, `surface`, `subject_type` e `subject_id` padronizados.

### Isolamento forte do box

1. namespace por box para cache.
2. namespace por box para logs.
3. namespace por box para exportacoes e arquivos.
4. config e segredos por box documentados.
5. politica clara de fronteira do runtime por box.

### Operacao e recuperacao

1. backup definido.
2. restore testado ao menos uma vez.
3. checklist de deploy.
4. checklist de rollback.
5. rotina curta de incidente.

### Observabilidade minima

1. healthcheck do app.
2. healthcheck do Redis.
3. logs de app.
4. logs de erro.
5. latencia das superficies quentes.
6. volume de auditoria por box.

### Seguranca minima de producao

1. rate limit.
2. admin protegido.
3. segredos fora do repositorio.
4. cookies e HTTPS corretos.
5. permissao por papel revisada.

## Trabalho em background da Fase 1

1. endurecer `intent_id` e idempotencia.
2. padronizar envelope de evento.
3. amadurecer `snapshot_version`.
4. amadurecer `ownership_scope` e `contact_stage`.
5. criar mapa de capacidade por box.
6. medir custo real por workspace e por box.
7. preparar read model operacional leve.
8. documentar a `box runtime boundary`.

## Gate de saida da Fase 1

So avancar quando:

1. 10 a 20 boxes rodarem com folga no servidor-alvo.
2. custo por box estiver entendido.
3. incidentes comuns forem recuperaveis.
4. os contratos criticos ja estiverem em uso real.
5. a observabilidade minima estiver confiavel.

## Checklist operacional da Fase 1

1. provisionar servidor.
2. subir Redis e app com healthcheck.
3. validar backup e restore.
4. validar deploy e rollback.
5. validar `intent_id`.
6. validar `snapshot_version`.
7. validar auditoria enriquecida.
8. definir limite oficial de boxes e usuarios simultaneos.

## Fase 2 - 21 a 100 boxes

## Objetivo

Aumentar densidade, reduzir custo marginal por box e profissionalizar a operacao.

## Topologia recomendada

1. Servidor A: app web.
2. Servidor B: Redis, cache e sinais quentes.
3. Servidor C opcional: Postgres dedicado.

## Filosofia da Fase 2

1. boxes ainda continuam separados operacionalmente.
2. a infraestrutura fica mais compartilhada.
3. a observabilidade deixa de ser luxo e vira requisito.
4. a arquitetura futura de tenant comeca a ganhar forma sem ser ativada ainda.

## O que significa sucesso na Fase 2

1. 21 a 100 boxes rodam por celula com previsibilidade.
2. o custo marginal por box cai.
3. a equipe consegue localizar gargalo por box, superficie e celula.
4. a base tecnica ja fala a lingua do multitenancy futuro.

## O que precisa entrar na Fase 2

### Resiliencia de runtime

1. fallback oficial `SSE -> polling/version`.
2. retry e backoff claros.
3. comportamento uniforme em `manager`, `reception` e `owner`.

### Capacidade por celula

1. quantidade alvo de boxes por celula.
2. quantidade alvo de usuarios simultaneos por celula.
3. regra de lotacao da celula.
4. regra de quando abrir nova celula.

### Observabilidade seria

1. latencia por box.
2. erro por box.
3. custo de query por superficie.
4. uso de Redis por superficie.
5. p95 e p99 por fluxo critico.
6. volume de auditoria por box.

### Leitura quente da operacao

1. read model operacional leve.
2. menor dependencia de `AuditEvent` para leitura quente.
3. historico e cooldown em trilho mais proprio.

### Ownership materializado

1. `contact_stage`.
2. `ownership_scope`.
3. `next_actor_role`.

### Namespaces maduros

1. cache por box.
2. stream por box.
3. storage por box.
4. logs por box.
5. exports por box.

### Control plane nascente

1. catalogo interno de boxes.
2. status de saude por box.
3. capacidade por celula.
4. roteamento basico interno.

## Trabalho em background da Fase 2

1. introduzir identidade interna de tenant sem ligar multitenancy aberto.
2. separar `box identity` de `runtime identity`.
3. preparar dual-read onde fizer sentido.
4. preparar roteamento por celula.
5. endurecer testes de boundary.
6. medir custo real por box ativo.
7. preparar migracao de leitura e cache.

## Gate de saida da Fase 2

So avancar quando:

1. 50 a 100 boxes estiverem rodando com previsibilidade.
2. fallback realtime estiver maduro.
3. observabilidade por box estiver confiavel.
4. read model operacional estiver estavel.
5. identidade interna de tenant ja existir.
6. a equipe souber dizer com clareza o custo e o limite de uma celula.

## Checklist operacional da Fase 2

1. separar app e Redis.
2. separar banco se a carga pedir.
3. validar fallback `version`.
4. validar telemetria por box.
5. validar capacidade da celula.
6. validar read model operacional.
7. validar boundary entre boxes.
8. formalizar control plane interno minimo.

## Fase 3 - 100+ boxes

## Objetivo

Transformar o produto em plataforma com multitenancy aberto real.

## Mudanca de filosofia

Aqui muda a regra principal do predio:

1. o isolamento deixa de ser principalmente por caixinha de runtime.
2. ele passa a ser principalmente por identidade logica forte de tenant.
3. a plataforma passa a compartilhar mais infraestrutura sem perder fronteira.

## O que significa sucesso na Fase 3

1. densidade por infraestrutura sobe.
2. custo marginal por tenant cai.
3. isolamento logico fica forte e testavel.
4. a operacao vira de plataforma, nao de hospedagem artesanal.

## O que precisa existir antes de ligar a Fase 3

### Tenant model canonico

1. identidade de tenant.
2. relacao tenant/box.
3. RBAC por tenant.
4. policies por tenant.

### Routing multi-tenant

1. request routing.
2. cache routing.
3. event routing.
4. storage routing.

### Boundary real

1. testes de vazamento entre tenants.
2. testes de autorizacao cruzada.
3. testes de isolamento de cache.
4. testes de stream e evento.

### Migracao progressiva

1. dual-read quando necessario.
2. migracao gradual de leitura.
3. rollback seguro.
4. estrategia clara para desligar o legado.

### Observabilidade de plataforma

1. metricas por tenant.
2. metricas por celula.
3. custo por tenant.
4. hotspots por superficie.

### Operacao de plataforma

1. onboarding de tenant.
2. offboarding.
3. backup por tenant.
4. restore por tenant.
5. incident response por tenant.

## Trabalho em background da Fase 3

1. consolidar a identidade de tenant nos contratos.
2. consolidar control plane.
3. amadurecer os trilhos de migracao de dados.
4. amadurecer observabilidade de plataforma.

## Gate de entrada da Fase 3

So ativar quando:

1. a Fase 2 estiver estavel.
2. os limites de capacidade por celula estiverem comprovados.
3. a equipe souber operar boundaries logicos com seguranca.
4. a migracao puder ser feita por rollout controlado e nao por big bang.

## Checklist operacional da Fase 3

1. validar tenant model.
2. validar roteamento multi-tenant.
3. validar boundary tests.
4. validar dual-read e rollback.
5. validar observabilidade de tenant.
6. ativar rollout progressivo.

## Fundações invisiveis obrigatorias desde ja

Estas pecas devem comecar cedo para a transicao ficar suave:

1. `intent_id`.
2. `snapshot_version`.
3. envelope canonico de evento.
4. `action_kind`, `surface`, `subject_type`, `subject_id`.
5. `ownership_scope`.
6. `contact_stage`.
7. namespace claro de cache, stream e storage.
8. metricas por box e superficie.
9. read model operacional auxiliar.
10. vocabulario unico entre payload, template, CSS e JS nas superficies quentes.

## O que nunca fazer

1. nao pular da Fase 1 para multitenancy aberto no susto.
2. nao transformar `AuditEvent` em read model final.
3. nao deixar cada tela inventar seu proprio fallback realtime.
4. nao misturar `box`, `tenant`, `surface` e `runtime` como se fossem a mesma coisa.
5. nao vender 100+ sem medir capacidade real de celula.

## Ordem pratica recomendada

### Agora

1. fechar checklist de producao da Fase 1.
2. validar isolamento forte por box.
3. validar backup e restore.
4. validar `intent_id`.
5. validar `snapshot_version`.
6. subir observabilidade minima.

### Entre 1 e 20 boxes

1. medir custo por box.
2. estabilizar uma celula.
3. amadurecer fallback realtime.
4. amadurecer namespace por box.
5. iniciar read model operacional leve.

### Entre 20 e 50 boxes

1. separar Redis do app.
2. separar banco se necessario.
3. validar capacidade por celula.
4. iniciar control plane interno.

### Entre 50 e 100 boxes

1. amadurecer identidade interna de tenant.
2. amadurecer dual-read.
3. endurecer testes de boundary.
4. preparar roteamento multi-tenant.

### Perto de 100 boxes

1. decidir a virada com base em metrica.
2. ativar rollout progressivo.
3. mover leitura e cache.
4. desligar o legado em etapas.

## Resumo executivo

Este plano organiza a escala assim:

1. **Fase 1** paga a obra.
2. **Fase 2** prepara a estrutura.
3. **Fase 3** liga a plataforma.

Em linguagem simples:

1. primeiro fazemos a casa dar lucro.
2. depois montamos o condominio.
3. por ultimo subimos o predio.
