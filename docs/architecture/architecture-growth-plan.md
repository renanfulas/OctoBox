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

Para a trilha especifica de quebra do monolito interno em apps Django reais, leia tambem [app-split-plan.md](app-split-plan.md).

O objetivo nao e fazer um sistema complexo antes da hora. O objetivo e fazer o simples atual de um jeito que permita crescer para:

1. integracao oficial com WhatsApp
2. automacao de pagamentos e cobranca
3. API para app mobile
4. multiunidade e franquias
5. relatorios inteligentes, IA e ML

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

Hoje a base ja tem bons sinais:

1. dominios internos separados por pastas
2. queries e snapshots de leitura para telas principais
3. services e workflows nas areas mais sensiveis
4. auditoria e papeis reais
5. preparo inicial para comunicacao por WhatsApp

Hoje os limites principais ainda sao:

1. tudo ainda vive dentro do app Django `boxcore`
2. nao existe camada oficial de API versionada
3. nao existe camada oficial de integracoes externas
4. nao existe base oficial para jobs assincronos
5. aluno e canal WhatsApp ainda estao perto demais na modelagem do negocio

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
4. modelar multiunidade antes de estabilizar unidade unica
5. espalhar integracao de WhatsApp em views e templates

## Decisao pratica imediata

Nos proximos ciclos, o caminho mais seguro e:

1. consolidar o core atual
2. abrir fronteira de API
3. abrir fronteira de integracao
4. abrir fronteira de jobs
5. so depois crescer para WhatsApp oficial, mobile e inteligencia

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