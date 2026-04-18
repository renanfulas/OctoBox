<!--
ARQUIVO: regras objetivas para Cloudflare na frente do OctoBox.

POR QUE ELE EXISTE:
- traduz o playbook do edge para configuracao executavel.
- evita que a camada externa dependa de interpretacao livre na hora da publicacao.

O QUE ESTE ARQUIVO FAZ:
1. lista regras concretas de rate limit por rota.
2. define a postura recomendada para o admin no edge.
3. organiza a ordem de ativacao no provedor.
4. registra o contrato de cache seguro para HTML autenticado e `/static/`.
5. define a validacao minima depois da ativacao do proxy.

PONTOS CRITICOS:
- essas regras so fazem sentido se o trafego publico passar pelo proxy.
- ativacao sem observabilidade pode causar falso positivo silencioso.
-->

# Regras concretas de Cloudflare

## Firewall e origem

Aplicar esta postura base:

1. usar Cloudflare como unica frente publica do dominio
2. manter a origem fora de canais publicos
3. habilitar WAF gerenciado
4. bloquear scanners obvios e user-agents malformados no edge
5. revisar qualquer bypass direto para a origem

## SSL e proxy

Ativar o proxy com esta postura:

1. registro `app` apontando para a VPS com nuvem laranja ligada
2. SSL/TLS em `Full (strict)`
3. nao usar `Flexible`
4. validar login e POST antes de subir regras mais agressivas

Regra pratica:

1. o Cloudflare deve acelerar a borda
2. a origem continua dona da sessao e do HTML autenticado

## Contrato de cache

Aplicar esta separacao:

1. `/static/*` pode receber cache forte no edge
2. HTML autenticado nao deve receber `Cache Everything`
3. rotas dinamicas como `/login/`, `/dashboard/`, `/alunos/`, `/financeiro/` e `/operacao/` devem ficar em `bypass cache`

Traducao pratica:

1. uniforme e cartaz podem ficar no armario da recepcao
2. prontuario e conversa com o aluno nao

## Regras de cache recomendadas

Criar as seguintes regras no produto de cache do Cloudflare:

1. nome: static-assets-strong
expressao: starts_with(http.request.uri.path, "/static/")
acao: permitir cache no edge para assets, mantendo compressao e TTL coerente com a origem

2. nome: authenticated-html-bypass
expressao: http.request.uri.path eq "/login/" or http.request.uri.path eq "/dashboard/" or starts_with(http.request.uri.path, "/alunos/") or starts_with(http.request.uri.path, "/financeiro/") or starts_with(http.request.uri.path, "/operacao/")
acao: bypass cache

Regra negativa:

1. nao aplicar `Cache Everything` em `app.octoboxfit.com.br/*`

## Sessao e login

Para preservar sessao sem surpresa:

1. manter `Full (strict)`
2. nao cachear HTML autenticado
3. validar login, logout e navegacao entre superficies autenticadas logo apos ativar o proxy
4. preencher `SECURITY_TRUSTED_PROXY_IPS` apenas depois de confirmar os proxies reais do Cloudflare

## Rate limits por rota

Criar regras separadas em Rate Limiting Rules:

1. nome: login-burst
expressao: http.request.method eq "POST" and http.request.uri.path eq "/login/"
periodo: 300 segundos
limite: 8
acao: block por 10 minutos

2. nome: student-export
expressao: http.request.method eq "GET" and starts_with(http.request.uri.path, "/alunos/exportar/")
periodo: 300 segundos
limite: 6
acao: managed challenge ou block por 10 minutos

3. nome: finance-export
expressao: http.request.method eq "GET" and starts_with(http.request.uri.path, "/financeiro/exportar/")
periodo: 300 segundos
limite: 6
acao: managed challenge ou block por 10 minutos

4. nome: student-autocomplete
expressao: http.request.method eq "GET" and http.request.uri.path eq "/api/v1/students/autocomplete/"
periodo: 60 segundos
limite: 60
acao: managed challenge

5. nome: dashboard-read
expressao: http.request.method eq "GET" and http.request.uri.path eq "/dashboard/"
periodo: 60 segundos
limite: 30
acao: managed challenge

6. nome: students-read
expressao: http.request.method eq "GET" and http.request.uri.path eq "/alunos/"
periodo: 60 segundos
limite: 30
acao: managed challenge

7. nome: finance-read
expressao: http.request.method eq "GET" and http.request.uri.path eq "/financeiro/"
periodo: 60 segundos
limite: 30
acao: managed challenge

8. nome: class-grid-read
expressao: http.request.method eq "GET" and http.request.uri.path eq "/grade-aulas/"
periodo: 60 segundos
limite: 30
acao: managed challenge

9. nome: operations-read
expressao: http.request.method eq "GET" and starts_with(http.request.uri.path, "/operacao/")
periodo: 60 segundos
limite: 30
acao: managed challenge

## Postura do admin no edge

1. manter o caminho real apenas em `DJANGO_ADMIN_URL_PATH`
2. nao divulgar esse caminho em material operacional
3. se a operacao permitir, restringir a rota a IPs esperados
4. se ainda nao der para restringir por IP, aplicar managed challenge forte no caminho do admin

Expressao base da regra do admin:

1. `starts_with(http.request.uri.path, "/SEU-CAMINHO-REAL-DO-ADMIN/")`

## Ordem recomendada de ativacao

1. publicar o dominio atras do Cloudflare
2. confirmar SSL/TLS em `Full (strict)`
3. ativar apenas a regra de cache forte para `/static/`
4. ativar `bypass cache` para HTML autenticado
5. validar login, POST e navegacao autenticada
6. ativar WAF gerenciado
7. criar as 9 regras acima
8. criar a regra especifica do admin
9. preencher `SECURITY_TRUSTED_PROXY_IPS` com proxies confiaveis reais
10. observar logs antes de promover IPs ou CIDRs para bloqueio permanente

## Validacao minima depois da ativacao

Confirmar estes sinais:

1. respostas publicas trazem `cf-ray`
2. `/login/` funciona sem loop
3. `/financeiro/` e `/alunos/` funcionam com sessao estavel
4. assets em `/static/` continuam fortes
5. HTML autenticado nao mostra comportamento de cache indevido
6. a regua de primeiro hit e hit quente melhora ou, no minimo, nao regride

Regua recomendada:

1. repetir a medicao de `Financeiro` e `Alunos`
2. comparar `elapsed_ms`, `req-total` e `view_total_ms`
3. verificar se o gap entre rede observada e tempo interno da view caiu
