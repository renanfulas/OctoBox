<!--
ARQUIVO: guia de seguranca viva do OctoBox.

TIPO DE DOCUMENTO:
- guia de seguranca

AUTORIDADE:
- media para orientacao de seguranca aplicada

DOCUMENTO PAI:
- [README.md](./README.md)

DOCUMENTOS IRMAOS:
- [../reference/production-security-baseline.md](../reference/production-security-baseline.md)
- [../reference/external-security-edge-playbook.md](../reference/external-security-edge-playbook.md)
- [../reference/cloudflare-edge-rules.md](../reference/cloudflare-edge-rules.md)
- [../architecture/deep-access-control-architecture.md](../architecture/deep-access-control-architecture.md)
-->

# Guia de seguranca

## Tese atual

A seguranca do OctoBox ficou mais eficiente porque deixou de depender so de boa intencao no codigo.

Hoje ela esta mais distribuida em:

1. configuracao
2. middleware
3. contratos de dados
4. edge
5. operacao e runbook

## O que melhorou desde o inicio

### 1. Admin e acesso

Hoje a postura esta mais forte porque:

1. existe `ADMIN_URL_PATH` privado
2. existe gate de admin instalado no runtime
3. existe leitura mais clara entre acesso normal e acesso profundo

### 2. Contencao de abuso

O sistema ganhou defesas mais concretas:

1. rate limits por escopo
2. honeypot e deteccao de scanner
3. blocklist preparada para operar com evidencia
4. fingerprint e middleware de seguranca

### 3. Protecao de dados sensiveis

Um salto importante foi o tratamento de telefone e PII:

1. campos sensiveis criptografados
2. busca por blind index
3. chave dedicada para blind index
4. exigencia mais dura fora do modo local

### 4. Infra e edge

A maturidade subiu porque a seguranca nao ficou so dentro do Django:

1. existe baseline operacional de producao
2. existe playbook de edge externo
3. existem regras para proxies confiaveis e blocklist
4. existe checklist operacional para deploy e rollback

### 5. Observabilidade de seguranca

O projeto tambem ficou mais eficiente porque consegue observar melhor:

1. logs de seguranca
2. trilha de auditoria
3. middleware com eventos claros de bloqueio e 429

## Linha de defesa atual

### Na borda HTTP

1. throttles e limits
2. honeypot
3. CSP
4. validacao de IP confiavel

### No dominio e dados

1. blind index
2. modelos e constraints
3. auditoria
4. idempotencia em integracoes

### Na operacao

1. baseline de ambiente
2. runbooks
3. smoke checks
4. restore e rollback preparados

## Regra de seguranca madura

Hoje o projeto esta melhor quando segue esta ordem:

1. primeiro negar o facil abuso
2. depois observar o que continua entrando
3. so entao endurecer mais com evidencia

Isso e melhor do que sair bloqueando tudo no chute, porque evita falso positivo operacional.

## O que nao devemos fazer

1. expor admin como caminho obvio
2. buscar PII diretamente em campo criptografado
3. bloquear range inteiro sem telemetria real
4. mexer em seguranca sem atualizar baseline ou runbook correspondente
5. tratar seguranca so como detalhe do deploy e nao do runtime

## Riscos que continuam no radar

1. configuracao incompleta de proxies confiaveis
2. endurecimento forte no app sem alinhamento com o edge
3. bypass de rotas e imports historicos sem facade ou contrato claro
4. achar que "ter middleware" ja significa seguranca madura

## Resumo do ganho de maturidade

O salto principal foi este:

1. a seguranca saiu do modo artesanal
2. entrou em modo institucional
3. e hoje conversa melhor com runtime, deploy, observabilidade e operacao
