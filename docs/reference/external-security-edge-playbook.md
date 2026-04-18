<!--
ARQUIVO: playbook de seguranca externa do edge.

POR QUE ELE EXISTE:
- fecha a parte que o codigo sozinho nao consegue cumprir quando o app esta atras do edge do provedor.
- organiza rate limit no proxy, observabilidade e politicas de bloqueio por IP/faixa com criterio operacional.

O QUE ESTE ARQUIVO FAZ:
1. define o que fica no app e o que sobe para o edge.
2. lista regras objetivas para Cloudflare ou proxy equivalente na frente do Render.
3. define sinais minimos de observabilidade e resposta a abuso.
4. registra a politica de cache segura para apps autenticados.

PONTOS CRITICOS:
- o app nao deve confiar em X-Forwarded-For sem proxy confiavel configurado.
- bloquear no edge e melhor do que deixar a rajada chegar no gunicorn.
-->

# Playbook de seguranca externa do edge

## Regra de fronteira

O app agora cobre:

1. throttle por escopo dentro do runtime
2. bloqueio por IP e faixa via variaveis de ambiente
3. logging de eventos de seguranca em stdout

O edge precisa cobrir:

1. rate limit antes do request chegar no gunicorn
2. regras gerenciadas contra bot, scanner e abuso volumetrico
3. bloqueio por IP, faixa, ASN ou pais quando necessario
4. telemetria externa para 403, 429 e padrao de rajada

## Topologia recomendada

Stack recomendada para o deploy atual:

1. cliente
2. Cloudflare ou proxy equivalente com WAF e rate limit
3. Render edge
4. aplicacao Django/Gunicorn

Regra pratica:

1. o usuario nunca deve falar direto com a origem publica sem a camada de edge controlada
2. o app deve confiar em IP encaminhado apenas se SECURITY_TRUSTED_PROXY_IPS estiver preenchido com os proxies reais

## Cache e sessao no edge

No edge, separar claramente:

1. assets estaticos
2. HTML autenticado

Contrato recomendado:

1. `/static/*` com cache forte
2. HTML autenticado em `bypass cache`
3. nada de `Cache Everything` no dominio inteiro do app
4. `Full (strict)` como modo padrao de SSL/TLS

Rotas que devem ficar fora de cache forçado:

1. `/login/`
2. `/dashboard/`
3. `/alunos/`
4. `/financeiro/`
5. `/operacao/*`

## Regras de rate limit no edge

Criar as seguintes regras no proxy:

1. POST /login/
limite sugerido: 8 por 5 minutos por IP

2. GET /alunos/exportar/*
limite sugerido: 6 por 5 minutos por IP

3. GET /financeiro/exportar/*
limite sugerido: 6 por 5 minutos por IP

4. GET /api/v1/students/autocomplete/
limite sugerido: 60 por minuto por IP

5. GET /dashboard/
limite sugerido: 30 por minuto por IP

6. GET /alunos/
limite sugerido: 30 por minuto por IP

7. GET /financeiro/
limite sugerido: 20 por minuto por IP

8. GET /grade-aulas/
limite sugerido: 30 por minuto por IP

9. GET /operacao/*
limite sugerido: 30 por minuto por IP

## Politicas de bloqueio por IP/faixa

Aplicar no edge:

1. bloquear IPs confirmados de abuso imediatamente
2. bloquear CIDRs reincidentes quando o padrao vier da mesma faixa
3. preferir desafio ou bloqueio temporario antes do bloqueio permanente quando a evidencia ainda for fraca

Aplicar no app:

1. preencher SECURITY_BLOCKED_IPS para IPs pontuais
2. preencher SECURITY_BLOCKED_IP_RANGES para faixas CIDR
3. preencher SECURITY_TRUSTED_PROXY_IPS apenas com proxies que realmente encaminham o IP do cliente

## Observabilidade minima

No edge, monitorar:

1. total de requests bloqueados por rota
2. picos de 429 por caminho
3. origem por IP, faixa, ASN e pais
4. volume por user-agent e assinatura de bot
5. presenca de `cf-ray` nas respostas apos ativacao do proxy
6. diferenca entre primeiro hit e hit quente nas superficies autenticadas

No app, monitorar:

1. logs octobox.security com security_rate_limit_triggered
2. logs octobox.security com security_ip_blocked
3. aumento abrupto de 429 em /login/, /alunos/exportar/, /financeiro/exportar/ e /api/v1/students/autocomplete/

## Runbook de resposta

Quando houver abuso:

1. confirmar rota, IP e janela no edge
2. verificar se o evento tambem apareceu nos logs octobox.security
3. elevar o bloqueio para IP ou CIDR no edge primeiro
4. refletir o bloqueio no app via SECURITY_BLOCKED_IPS ou SECURITY_BLOCKED_IP_RANGES se o evento persistir
5. revisar se o limite daquela rota ficou baixo demais ou alto demais

## Contrato de configuracao no Render

Variaveis que devem ser preenchidas no deploy:

1. DJANGO_ADMIN_URL_PATH
2. SECURITY_TRUSTED_PROXY_IPS
3. SECURITY_BLOCKED_IPS
4. SECURITY_BLOCKED_IP_RANGES
5. EXPORT_RATE_LIMIT_MAX_REQUESTS
6. EXPORT_RATE_LIMIT_WINDOW_SECONDS
7. HEAVY_READ_RATE_LIMIT_MAX_REQUESTS
8. HEAVY_READ_RATE_LIMIT_WINDOW_SECONDS
9. AUTOCOMPLETE_RATE_LIMIT_MAX_REQUESTS
10. AUTOCOMPLETE_RATE_LIMIT_WINDOW_SECONDS
11. SECURITY_LOG_LEVEL

## Criterio de pronto desta camada

Esta camada so pode ser considerada encaixada quando:

1. existir um proxy controlado na frente da origem
2. os limites do edge estiverem criados nas rotas listadas acima
3. SECURITY_TRUSTED_PROXY_IPS estiver configurado com proxies reais
4. logs de bloqueio e throttle estiverem visiveis no runtime
5. o time conseguir bloquear um IP ou CIDR sem novo deploy de codigo
6. login e sessao estiverem estaveis com o proxy ativo
7. HTML autenticado estiver fora de cache indevido
