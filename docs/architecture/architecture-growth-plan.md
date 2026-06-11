<!--
ARQUIVO: plano de evolucao arquitetural do produto.

POR QUE ELE EXISTE:
- Registra a direcao tecnica do OctoBox para crescer sem virar um sistema fragil.
- Alinha produto, arquitetura e ordem de execucao antes de entrar em integracoes e features mais pesadas.

O QUE ESTE ARQUIVO FAZ:
1. Define principios de arquitetura para o crescimento do produto.
2. Organiza a evolucao em fases pequenas e executaveis.
3. Define o que entra agora, o que entra depois e o que ainda nao deve ser feito.

TIPO DE DOCUMENTO:
- direcao arquitetural

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [octobox-conceptual-core.md](octobox-conceptual-core.md)

QUANDO USAR:
- quando houver duvida sobre rumo de crescimento, ordem macro de evolucao e limites do que ainda nao deve entrar

PONTOS CRITICOS:
- Este plano deve acompanhar a realidade do produto, nao uma aspiracao vazia.
- Mudancas de direcao precisam preservar simplicidade operacional e baixo acoplamento.
-->

# Plano de evolucao arquitetural

Este documento traduz a ambicao do OctoBox em uma arquitetura de crescimento pragmatica.

Para a trilha especifica de quebra do monolito interno em apps Django reais, leia tambem [app-split-plan.md](app-split-plan.md) (trilha ja executada; mantida como registro).

Para a direcao especifica da camada superior de inteligencia operacional, score, previsao e guardrails de ML, leia tambem [operational-intelligence-ml-layer.md](operational-intelligence-ml-layer.md).

O objetivo nao e fazer um sistema complexo antes da hora. O objetivo e fazer o simples atual de um jeito que permita crescer para:

1. integracao oficial com WhatsApp
2. automacao de pagamentos e cobranca
3. API para app mobile
4. multiunidade e franquias
5. relatorios inteligentes, IA e ML

Neste trilho, a regra continua sendo clara:

1. ML sobe acima do core
2. ML nao redefine verdade transacional
3. ML depende de dados consolidados, reconciliados e auditaveis

## Tese de arquitetura

O OctoBox nao deve crescer como um conjunto de telas Django cada vez mais pesadas.

Ele deve crescer como uma plataforma operacional com cinco camadas claras:

1. dominio transacional confiavel
2. interface web interna para operacao humana
3. interface de API para clientes externos e app mobile
4. integracoes externas e jobs assincronos
5. inteligencia operacional acima do core, nunca misturada no core

## Principios nao negociaveis

1. O simples vem antes do sofisticado.
2. Toda nova feature precisa ter um lugar arquitetural claro.
3. Regra de negocio mutavel nao deve morar em template nem em view HTTP.
4. Leitura e escrita devem continuar separadas quando a regra ficar sensivel.
5. Integracoes externas nao devem contaminar o request web principal.
6. O produto precisa continuar barato de manter.
7. O sistema deve ficar mais previsivel a cada etapa, nao mais brilhante e mais opaco.

## Estado atual resumido

> Revisado em 2026-06-11: a versao anterior desta secao descrevia o estado
> pre-virada multi-tenant (boxcore como casa de tudo, sem API, integracoes ou
> jobs oficiais). O runtime venceu o doc e a secao foi corrigida.

Hoje a base ja tem bons sinais:

1. apps de dominio reais fora de `boxcore`: `access`, `students`, `finance`, `operations`, `catalog`, `communications`, `auditing`, `dashboard`, `guide`, `quick_sales`
2. fronteiras oficiais ja abertas: `api` (contrato `v1`), `integrations` (webhooks de WhatsApp e Resend), `jobs` (execucao assincrona sem fila externa)
3. runtime multi-tenant vivo em producao: `django-tenants` com schema por box, control plane proprio (`control`), funil comercial (`signup`) e identidade cruzada de aluno (`student_identity`) no schema publico; primeiro box provisionado em 2026-05-23
4. identidade de canal ja desacoplada do aluno: contrato WhatsApp com blind index, backfill historico e constraint de unicidade
5. queries, snapshots, presenters e page payloads nas telas principais, com auditoria, papeis reais e throttling por escopo

Hoje os limites principais ainda sao:

1. `boxcore` permanece como app legado de estado (~13,5 mil linhas): ancora de migrations, app label e namespace de admin — ver [boxcore-state-residue-inventory.md](boxcore-state-residue-inventory.md)
2. a leitura quente da operacao ainda depende demais de `AuditEvent`; o read model operacional leve ainda nao existe
3. so dois corredores reais de CENTER foram promovidos (`class_grid`, `workspace`); fluxo novo ainda tende a entrar por view direta
4. custo por box e capacidade por celula ainda nao foram medidos; o gate da Fase 1 de escala segue aberto
5. a suite E2E ainda e minima frente as superficies criticas do produto

## Arquitetura alvo por blocos

### 1. Core de dominio

Responsavel por:

1. alunos
2. financeiro
3. operacao de aulas
4. auditoria
5. onboarding

Regra:

1. modelos, invariantes, servicos de aplicacao e casos de uso confiaveis
2. sem dependencia de interface web, template, webhook ou app mobile

### 2. Web operacional

Responsavel por:

1. dashboard
2. catalogo visual
3. operations por papel
4. admin

Regra:

1. ser fina
2. chamar snapshots e casos de uso
3. nao carregar side effects externos pesados no request

### 3. API publica e mobile

Responsavel por:

1. contratos REST versionados
2. autenticacao de clientes
3. payloads estaveis para app mobile
4. leitura e escrita externas controladas

Regra:

1. contrato claro
2. versao explicita
3. sem acoplamento com templates

### 4. Integracoes externas

Responsavel por:

1. WhatsApp oficial
2. gateway de pagamento
3. webhooks externos
4. adaptadores de terceiros

Regra:

1. tudo com fronteira propria
2. payload bruto isolado
3. idempotencia e rastreabilidade desde o inicio

### 5. Jobs e automacoes

Responsavel por:

1. envio de mensagens
2. reprocessamento
3. consolidacao de relatorios
4. tarefas periodicas
5. score, previsao e pipelines futuros de IA

Regra:

1. nada disso deve depender de request web aberto
2. tarefas precisam ser reexecutaveis e auditaveis

## Ordem de execucao recomendada

> Status em 2026-06-11: as Fases 1 a 4 ja foram executadas — os pacotes
> previstos viraram apps reais (`api/`, `integrations/`, `jobs/`), a identidade
> de canal foi desacoplada do aluno e o split de dominio aconteceu. A Fase 5
> esta parcialmente viva: tenancy real entrou em producao via `django-tenants`
> (ver [../plans/schema-per-tenant-migration-plan.md](../plans/schema-per-tenant-migration-plan.md)
> e ADR-005 a ADR-010 em [../adr/README.md](../adr/README.md)) e o app do aluno
> (PWA) existe; relatorios inteligentes e ML continuam como direcao formalizada,
> nao construida. As fases abaixo ficam como registro do trilho seguido.

### Fase 1: solidificar a base atual

Objetivo:

1. manter o simples funcionando
2. reduzir acoplamento escondido
3. registrar a direcao da arquitetura

Entradas desta fase:

1. plano arquitetural no repositorio
2. pacotes reservados para API, integracoes e jobs
3. padronizacao de documentacao e leitura

Nao fazer nesta fase:

1. mover modelos de forma agressiva
2. instalar filas ou frameworks externos sem uso real
3. adicionar features so porque a arquitetura agora comporta

### Fase 2: preparar fronteiras reais

Objetivo:

1. criar interfaces estaveis antes das integracoes pesadas

Entregas:

1. `boxcore/api/` com contrato inicial e versao `v1`
2. `boxcore/integrations/whatsapp/` com modelos de evento e adaptadores
3. `boxcore/jobs/` com padrao de execucao assincrona
4. politica de idempotencia para webhooks e tarefas

### Fase 3: desacoplar identidade de pessoa e identidade de canal

Objetivo:

1. impedir que o crescimento do WhatsApp contamine o dominio do aluno

Entregas:

1. aluno deixa de depender do numero como identidade primaria de canal
2. contatos e canais passam a suportar historico, consentimento e vinculos mais ricos
3. deduplicacao e reconciliacao passam a ficar em camada de integracao e onboarding

### Fase 4: separar apps de dominio de verdade

Objetivo:

1. sair do monolito interno por pastas e ir para apps Django reais quando o custo fizer sentido

Sequencia sugerida:

1. `core`
2. `access`
3. `students`
4. `finance`
5. `operations`
6. `communications`
7. `auditing`
8. `api`
9. `integrations`
10. `jobs`

Observacao:

1. isso nao deve ser feito de uma vez
2. deve acontecer por fatias seguras, com testes e aliases de compatibilidade quando necessario
3. a trilha pratica de baixo e medio custo ficou detalhada em [app-split-plan.md](app-split-plan.md)

### Fase 5: adicionar capacidade de plataforma

Objetivo:

1. permitir multiunidade, franquias, mobile e inteligencia sem reescrever o core

Entregas futuras:

1. tenancy ou particionamento por unidade
2. API mobile completa
3. pipelines de comunicacao inteligente
4. data products e relatorios automaticos
5. camadas de IA sobre dados consolidados e confiaveis

## O que evitar agora

1. microservicos
2. event-driven distribuido sem necessidade real
3. adicionar IA sem qualidade de dado e sem jobs confiaveis
4. abrir multitenancy para volume antes de fechar os gates de custo, backup/restore e observabilidade da Fase 1 de escala
5. espalhar integracao de WhatsApp em views e templates

## Decisao pratica imediata

Nos proximos ciclos, o caminho mais seguro e:

1. fechar o gate da Fase 1 de escala: backup/restore testado, custo medido por box, observabilidade minima confiavel
2. construir o read model operacional leve antes de crescer densidade de boxes
3. continuar drenando `boxcore` por fatias seguras, comecando pelos residuos de compatibilidade
4. promover fluxos novos pelo corredor oficial de facade/CENTER em vez de view direta
5. so depois crescer para WhatsApp oficial em volume, mobile completo e inteligencia

## Sinal de arquitetura saudavel

O projeto esta no caminho certo se, a cada nova feature:

1. fica claro onde ela entra
2. fica claro qual camada ela toca
3. o request web nao fica mais pesado
4. a chance de efeito colateral diminui
5. os testes ficam mais faceis de escrever, nao mais dificeis

## Sinal de arquitetura doente

O projeto esta saindo do caminho se:

1. toda nova feature exige mexer em muitos modulos ao mesmo tempo
2. integracao externa entra direto em view ou template
3. logica de negocio e side effect externo ficam misturados
4. o dashboard vira lugar de regra operacional
5. o medo de tocar no codigo passa a aumentar
