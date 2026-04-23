<!--
ARQUIVO: C.O.R.D.A. da frente de endurecimento das superficies de seguranca do OctoBox.

TIPO DE DOCUMENTO:
- plano de frente ativa
- contrato de execucao
- prompt operacional reutilizavel

AUTORIDADE:
- alta para a frente atual de correcao de falhas de autorizacao, exposicao e higiene defensiva

DOCUMENTOS PAIS:
- [../architecture/deep-access-control-architecture.md](../architecture/deep-access-control-architecture.md)
- [deep-access-control-rollout-plan.md](deep-access-control-rollout-plan.md)
- [../reference/production-security-baseline.md](../reference/production-security-baseline.md)

DOCUMENTOS IRMAOS:
- [../guides/security-architecture-guide.md](../guides/security-architecture-guide.md)
- [../reference/external-security-edge-playbook.md](../reference/external-security-edge-playbook.md)
- [../reference/cloudflare-edge-rules.md](../reference/cloudflare-edge-rules.md)

QUANDO USAR:
- quando a pergunta for como corrigir as falhas de seguranca recentes sem criar debito tecnico
- quando precisarmos abrir uma frente organizada de hardening de borda HTTP, autorizacao e anti-exfiltracao
- quando um agente ou engenheiro precisar de contrato claro para executar a frente por ondas

POR QUE ELE EXISTE:
- evita corrigir achados criticos de forma isolada e sem ordem
- reduz o risco de "fechar uma porta e abrir outra" durante o hardening
- alinha seguranca, anti-cheat, auditoria e performance numa unica lingua de execucao

O QUE ESTE ARQUIVO FAZ:
1. consolida o contexto da frente de endurecimento atual
2. organiza riscos, direcao e ondas de execucao
3. define criterios de aceite e guardrails de regressao
4. entrega um prompt operacional reutilizavel em formato C.O.R.D.A.

PONTOS CRITICOS:
- esta frente nao pode depender apenas de login; precisa de autorizacao, escopo e telemetria
- endurecer uma rota nao autoriza vazar cookies, headers ou detalhes de excecao em logs locais
- throttling sem calibracao pode virar anti-produto; o alvo e bloquear abuso sem punir operacao legitima
-->

# C.O.R.D.A. - Security Surface Hardening

## C - Contexto

O OctoBox ja saiu do modo artesanal de seguranca e hoje tem base importante:

1. `ADMIN_URL_PATH` privado
2. middlewares de seguranca, throttle e honeypot
3. fingerprint de sessao
4. trilha de auditoria
5. baseline operacional de proxies, blocklist e rate limits
6. separacao crescente entre fluxo normal, fluxo sensivel e acesso profundo

Ao mesmo tempo, a repassada recente mostrou que a casa ainda tem algumas portas fortes na fachada e portas fracas no corredor lateral.

### Fotografia atual dos achados mais importantes

1. `RAG` de projeto com busca e resposta acessiveis para qualquer usuario autenticado
2. `Mapa do Sistema` acessivel para qualquer usuario autenticado, expondo rotas, ownership e estrutura interna
3. endpoint de bootstrap interno `debug/init-system/` com `migrate` e criacao de superuser usando credencial hardcoded
4. endpoints financeiros da API v1 confiando em `LoginRequiredMixin` onde deveria existir autorizacao por papel e por recurso
5. autocomplete de alunos expondo PII demais para uma fronteira de autorizacao fraca
6. retorno de `str(exc)` em bordas sensiveis
7. `RoleRequiredMixin` despejando cookies e headers em arquivo local ao negar permissao
8. allowlist de IP em endpoint tokenizado lendo `X-Forwarded-For` diretamente, sem a mesma cadeia de proxy confiavel do middleware central

Em linguagem simples:

1. a casa ja tem portaria, camera e muro
2. mas algumas salas internas ainda aceitam cracha demais
3. e um ou outro corredor ainda anota segredos no quadro quando alguem tenta entrar errado

### Tese da frente

Esta frente nao existe apenas para "corrigir bugs de seguranca".

Ela existe para:

1. reduzir profundidade herdada por qualquer sessao autenticada
2. endurecer superficies de leitura e mutacao com autorizacao real
3. impedir recon, enumeração e exfiltracao assistida pelo proprio produto
4. fazer isso sem matar performance e sem bloquear fluxo legitimo de owner, manager e operacao

## O - Objetivo

Fechar as falhas de maior severidade encontradas na borda HTTP e nas superfícies internas expostas, transformando a seguranca do OctoBox em uma fronteira mais precisa:

1. quem pode ver
2. quem pode agir
3. o que pode ser lido por rota
4. o que vira evento auditavel
5. o que deve ser contido por throttle, telemetria e regras de abuso

### Sucesso significa

1. `RAG`, `MAPA`, endpoints financeiros e rotas internas criticas deixam de depender so de autenticacao
2. acesso passa a ser controlado por papel e, quando necessario, por escopo de recurso
3. PII e detalhes internos deixam de vazar por autocomplete, erros e logs locais
4. rotas sensiveis recebem throttles coerentes com risco real
5. negativas de permissao, tentativas suspeitas e abuso geram rastros auditaveis e revisaveis
6. os testes deixam de proteger comportamento frouxo e passam a proteger fronteiras corretas

## R - Riscos

### 1. Risco de corrigir autorizacao e criar novo vazamento

Hoje o `RoleRequiredMixin` registra cookies e headers em `playwright_debug.log`.

Se a frente endurecer varias rotas sem matar esse comportamento:

1. a permissao melhora
2. mas o sistema passa a guardar material sensivel quando alguem e negado

Regra:

1. nenhuma onda desta frente pode promover mais rotas para `RoleRequiredMixin` antes de neutralizar esse vazamento

### 2. Risco de fechar a porta errada

Se a equipe corrigir apenas `RAG` e `MAPA`, mas deixar:

1. `debug/init-system/`
2. `PaymentLinkView`
3. `StudentFreezeView`

o predio continua vulneravel por portas mais fundas.

### 3. Risco de anti-produto por throttle agressivo

Pela lente do `Security & Anti-Cheat Engineer`, throttle bom e como catraca inteligente:

1. segura rajada estranha
2. nao tranca o funcionario normal toda hora

Se os limites forem chutados:

1. owner, manager e recepcao sofrem falso positivo
2. a operacao comeca a pedir bypass manual
3. a seguranca vira atrito em vez de fronteira

### 4. Risco de BOLA/IDOR camuflado por "esta logado"

Algumas views atuais ainda raciocinam assim:

1. se entrou no predio, pode abrir a gaveta

Isso e perigoso principalmente em:

1. links de pagamento
2. congelamento de aluno
3. leitura de PII em autocomplete
4. leitura assistida de codigo e docs no RAG

### 5. Risco de exfiltracao para terceiro quando o RAG remoto estiver ligado

Se o RAG puder usar provedor externo:

1. contexto interno recuperado pode sair para OpenAI ou Anthropic
2. a autorizacao frouxa deixa de ser so leitura indevida interna
3. vira potencial exfiltracao assistida por provedor externo

### 6. Risco de plano bonito sem telemetria util

Sem eventos e contadores claros:

1. a equipe nao sabe quem esta batendo nas portas
2. nao sabe se o throttle ficou frouxo
3. nao sabe se o abuso migrou de rota

## D - Direcao

### Regra mestra

`autorizacao antes de conveniencia, escopo antes de amplitude, telemetria antes de blocklist, silencio para o atacante e clareza para o operador`

### Principios de execucao

1. nenhuma rota sensivel nova deve depender apenas de `LoginRequiredMixin`
2. nenhum endpoint interno deve permanecer exposto so porque "nao e producao"
3. nenhuma borda sensivel deve devolver `str(exc)` ao cliente
4. nenhum mecanismo de negacao deve despejar cookies, headers ou PII em log local
5. toda correcao critica deve vir junto de teste de regressao
6. quando a mudanca tocar throttle, deve explicitar alvo, dimensao e risco de falso positivo

### Frentes tecnicas da obra

#### 1. Fronteira de autorizacao

Responsavel por:

1. trocar autenticacao fraca por autorizacao declarada
2. aplicar `RoleRequiredMixin` ou policy dedicada nas rotas sensiveis
3. quando necessario, introduzir validacao por recurso

Alvos imediatos:

1. `knowledge/views.py`
2. `guide/views.py`
3. `api/v1/finance_views.py`
4. `api/v1/views.py`

#### 2. Fronteira de superficie exposta

Responsavel por:

1. matar ou isolar rotas de debug e bootstrap
2. reduzir payloads com PII
3. revisar endpoints tokenizados e webhooks com cadeia correta de confianca

Alvos imediatos:

1. `api/v1/internal_views.py`
2. `guide/views.py`
3. `api/v1/views.py`

#### 3. Fronteira de higiene defensiva

Responsavel por:

1. parar de vazar excecoes cruas
2. remover logs locais sensiveis
3. garantir mensagens de erro seguras e logs internos saneados

Alvos imediatos:

1. `access/permissions/mixins.py`
2. `api/v1/internal_views.py`
3. `api/v1/finance_views.py`

#### 4. Fronteira de anti-exfiltracao e anti-abuse

Responsavel por:

1. calibrar throttles para `RAG`, `MAPA`, autocomplete e endpoints de alto valor
2. registrar negacoes e rajadas suspeitas
3. preparar comportamento observavel antes de subir blocklist

Alvos imediatos:

1. `shared_support/security/__init__.py`
2. suites de testes de seguranca e API

### Ordem recomendada

1. neutralizar vazamentos colaterais de log e excecao
2. remover ou bloquear bootstrap inseguro
3. fechar autorizacao de `RAG` e `MAPA`
4. fechar BOLA/IDOR dos endpoints financeiros
5. reduzir superficie de PII no autocomplete
6. calibrar throttles e observabilidade dedicados
7. so depois reavaliar corpus, RAG remoto e acesso profundo mais fino

## A - Acoes / Ondas

### Onda 0 - Safety rails imediatos

Objetivo:

1. parar os vazamentos mais absurdos antes de endurecer o resto

Entregas:

1. remover dump de cookies e headers de `RoleRequiredMixin`
2. substituir `str(exc)` por mensagens seguras nas bordas mais criticas
3. revisar se logs internos preservam correlation id sem preservar material sensivel

Criterio de pronto:

1. negar permissao nao gera arquivo com cookies
2. falhas de Stripe, bootstrap e financeiro nao revelam excecao crua ao cliente

### Onda 1 - Fechar o corredor proibido

Objetivo:

1. eliminar ou neutralizar a superficie de bootstrap inseguro

Entregas:

1. remover `debug/init-system/` do runtime ou protegê-lo de forma operacionalmente segura e temporaria
2. eliminar credenciais hardcoded e segredos em query string
3. revisar manifesto e rotas para garantir que a superficie sensivel nao fique anunciada sem necessidade

Criterio de pronto:

1. nao existe mais rota capaz de rodar `migrate` e criar superuser por chamada HTTP simples

### Onda 2 - Fechar leitura privilegiada

Objetivo:

1. impedir que qualquer autenticado leia a planta e o cerebro do sistema

Entregas:

1. `ProjectKnowledgeSearchView` e `ProjectKnowledgeAnswerView` protegidos por papel
2. `ProjectKnowledgeHealthView` movido para fronteira fechada ou reduzido a health interno
3. `SystemMapView` protegido por papel
4. testes atualizados para provar "papel correto entra, autenticado generico nao entra"

Criterio de pronto:

1. `RAG` e `MAPA` deixam de ser biblioteca interna aberta a qualquer sessao autenticada

### Onda 3 - Fechar mutacao indevida

Objetivo:

1. impedir BOLA/IDOR nas operacoes financeiras

Entregas:

1. `PaymentLinkView` com autorizacao por papel e por escopo funcional
2. `StudentFreezeView` com autorizacao por papel e validacao do recurso alvo
3. auditoria de alto valor para tentativa negada, congelamento e criacao de checkout
4. testes cobrindo acesso negado e acesso permitido

Criterio de pronto:

1. estar logado deixa de ser suficiente para agir em pagamento ou aluno arbitrario

### Onda 4 - Reduzir exfiltracao e enumeração

Objetivo:

1. diminuir vazamento de PII e estrutura por endpoints de leitura

Entregas:

1. `StudentAutocompleteView` restrito por papel
2. payload de autocomplete reduzido ao minimo operacional necessario
3. criterio explicito do que pode ou nao sair em API de busca
4. allowlist de fontes do `RAG` reavaliada por sensibilidade

Criterio de pronto:

1. autocomplete deixa de funcionar como mini-motor de enumeração de CPF/telefone
2. corpus do RAG fica mais proximo de conhecimento util e mais longe de planta interna sensivel

### Onda 5 - Anti-cheat, throttle e observabilidade

Objetivo:

1. preparar a frente para abuso real sem punir uso legitimo

Entregas:

1. throttle dedicado para `RAG`, `MAPA` e leituras sensiveis equivalentes
2. eventos auditaveis de negacao, rajada e tentativa anomala
3. revisao da allowlist de IP de endpoints tokenizados usando cadeia de proxy confiavel central
4. medicao de falso positivo e de latencia das rotas protegidas

Criterio de pronto:

1. a equipe enxerga abuso com clareza
2. o sistema contem rajada sem quebrar o fluxo normal do produto

## Checklist curto de aceite

1. nenhuma rota critica nova depende so de autenticacao
2. nenhuma borda critica devolve excecao crua
3. nenhum log local novo guarda cookies ou headers sensiveis
4. toda correcao critica tem teste de regressao
5. toda rota endurecida tem justificativa de papel e de risco
6. throttles novos vieram com criterio de calibracao e observabilidade

## Prompt operacional reutilizavel

Use este prompt quando um agente for executar uma onda desta frente:

```text
Voce esta executando a frente "Security Surface Hardening" do OctoBox.

Objetivo principal:
Fechar as falhas de autorizacao, exposicao, exfiltracao e higiene defensiva da onda atual sem criar regressao funcional, sem vazar dados em logs locais e sem degradar a operacao legitima.

Contexto obrigatorio:
- O projeto e um Django modular com access, api, guide, knowledge, finance, operations e shared_support.
- O README e os docs do projeto devem ser lidos antes de codar.
- A tese de seguranca atual exige autorizacao real, telemetria e principio do menor privilegio.
- A frente atual nao aceita "esta logado" como justificativa suficiente para ver ou agir em superficies sensiveis.

Escopo desta execucao:
- Trabalhe apenas na onda solicitada.
- Preserve contratos publicos validos quando possivel.
- Se uma mudanca exigir ruptura de contrato, explicite isso antes de concluir.

Nao-negociaveis:
1. Nao devolver `str(exc)` ao cliente em bordas sensiveis.
2. Nao registrar cookies, headers sensiveis ou tokens em logs locais.
3. Nao depender apenas de `LoginRequiredMixin` em rota critica.
4. Nao aplicar throttle sem explicar alvo, dimensao e risco de falso positivo.
5. Nao deixar teste protegendo comportamento inseguro antigo.

Formato de entrega:
1. Diagnostico curto da onda.
2. Mudancas implementadas.
3. Testes adicionados ou ajustados.
4. Riscos residuais.
5. Verificacao final.

Criterios de aceite:
- O comportamento inseguro anterior deixa de ser possivel.
- O teste cobre a regressao principal.
- A mudanca respeita o estilo e a arquitetura do OctoBox.
- A operacao legitima continua clara e utilizavel.
```

## Failure checks para esta frente

Antes de fechar qualquer PR desta frente, revisar:

1. esta rota ainda permite leitura ou mutacao para autenticado generico?
2. a resposta ainda revela detalhes internos que bastariam para um atacante aprender demais?
3. a negacao de permissao ainda vaza material sensivel em arquivo local?
4. o throttle novo bloqueia abuso real ou so atrapalha uso legitimo?
5. os testes validam a fronteira certa ou ainda protegem o comportamento frouxo antigo?
