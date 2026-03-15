<!--
ARQUIVO: baseline operacional de seguranca para deploy.

POR QUE ELE EXISTE:
- transforma a camada de seguranca em configuracao objetiva de producao.
- evita que throttle, proxy confiavel e blocklist dependam de memoria ou improviso.

O QUE ESTE ARQUIVO FAZ:
1. define os valores iniciais recomendados para o ambiente.
2. explica o que deve ficar vazio ate existir evidencia real.
3. documenta o criterio de promocao de IP para blocklist.

PONTOS CRITICOS:
- sem proxy confiavel configurado, o IP do cliente pode ser interpretado errado.
- blocklist sem evidencia real gera falso positivo e bloqueio inutil.
-->

# Baseline operacional de seguranca

## Valores iniciais recomendados no deploy

Preencher no ambiente de producao com este baseline:

1. `DJANGO_ADMIN_URL_PATH`: caminho nao obvio e privado, com pelo menos 16 caracteres utilitarios
2. `LOGIN_RATE_LIMIT_MAX_REQUESTS=8`
3. `LOGIN_RATE_LIMIT_WINDOW_SECONDS=300`
4. `ADMIN_RATE_LIMIT_MAX_REQUESTS=12`
5. `ADMIN_RATE_LIMIT_WINDOW_SECONDS=300`
6. `WRITE_RATE_LIMIT_MAX_REQUESTS=30`
7. `WRITE_RATE_LIMIT_WINDOW_SECONDS=60`
8. `EXPORT_RATE_LIMIT_MAX_REQUESTS=6`
9. `EXPORT_RATE_LIMIT_WINDOW_SECONDS=300`
10. `DASHBOARD_RATE_LIMIT_MAX_REQUESTS=30`
11. `DASHBOARD_RATE_LIMIT_WINDOW_SECONDS=60`
12. `HEAVY_READ_RATE_LIMIT_MAX_REQUESTS=30`
13. `HEAVY_READ_RATE_LIMIT_WINDOW_SECONDS=60`
14. `AUTOCOMPLETE_RATE_LIMIT_MAX_REQUESTS=60`
15. `AUTOCOMPLETE_RATE_LIMIT_WINDOW_SECONDS=60`
16. `SECURITY_LOG_LEVEL=WARNING`

Regra pratica:

1. login e exportacao ficam mais apertados porque sao alvos naturais de brute force e abuso volumetrico
2. dashboard e leituras pesadas ficam no mesmo baseline para simplificar a primeira operacao
3. autocomplete fica mais solto porque faz parte do fluxo normal de digitacao, mas continua protegido

## Proxy confiavel

`SECURITY_TRUSTED_PROXY_IPS` deve conter apenas IPs de proxies que realmente repassam o IP do cliente.

Sem isso:

1. o app pode confiar em cabecalho errado
2. o blocklist pode mirar o IP errado
3. o throttle por IP perde valor operacional

Se ainda nao houver lista fechada do provedor:

1. deixe `SECURITY_TRUSTED_PROXY_IPS` vazio
2. publique o proxy externo primeiro
3. preencha a lista so depois de confirmar os IPs ou ranges oficiais do provedor

## Blocklist inicial

Baseline inicial recomendado:

1. `SECURITY_BLOCKED_IPS` vazio
2. `SECURITY_BLOCKED_IP_RANGES` vazio

Motivo:

1. sem telemetria real, bloquear IP publico ou faixa por antecipacao tende a ser chute
2. o bloqueio permanente deve nascer de evidencia, nao de suspeita abstrata

## O que merece entrar primeiro no blocklist

Promover para `SECURITY_BLOCKED_IPS` quando houver evidencia clara de abuso concentrado em um IP:

1. repeticao de 429 nas mesmas rotas por multiplas janelas seguidas
2. tentativa recorrente de login fora do padrao normal
3. rajada em exportacao ou autocomplete sem sessao operacional compativel
4. scanner automatizado insistindo em caminhos sensiveis

Promover para `SECURITY_BLOCKED_IP_RANGES` apenas quando houver evidencia clara de reincidencia na mesma faixa:

1. varios IPs vizinhos repetindo o mesmo padrao
2. mesmo ASN ou mesmo bloco pequeno insistindo na mesma classe de abuso
3. edge mostrando concentracao de eventos que justifique subir de IP isolado para CIDR

## O que nao deve entrar por padrao

Nao preencher blocklist permanente com base apenas em intuicao para:

1. paises inteiros
2. ASNs inteiros
3. ranges publicos amplos sem evidencia
4. IPs unicos vistos uma vez sem reincidencia

## Sequencia curta de operacao

1. aplicar o baseline acima no deploy
2. subir o proxy externo com regras do playbook do edge
3. confirmar os proxies reais e preencher `SECURITY_TRUSTED_PROXY_IPS`
4. observar logs `octobox.security` por alguns dias
5. promover IPs ou CIDRs para blocklist so quando houver evidencia repetida

## Estado considerado correto hoje

Hoje, sem log consolidado de producao nesta base, a decisao mais segura e:

1. publicar com throttles definidos
2. manter blocklist inicial vazio
3. deixar a promocao para blocklist depender de telemetria real