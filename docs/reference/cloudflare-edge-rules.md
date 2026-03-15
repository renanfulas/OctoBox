<!--
ARQUIVO: regras objetivas para Cloudflare na frente do OctoBox.

POR QUE ELE EXISTE:
- traduz o playbook do edge para configuracao executavel.
- evita que a camada externa dependa de interpretacao livre na hora da publicacao.

O QUE ESTE ARQUIVO FAZ:
1. lista regras concretas de rate limit por rota.
2. define a postura recomendada para o admin no edge.
3. organiza a ordem de ativacao no provedor.

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
2. ativar WAF gerenciado
3. criar as 9 regras acima
4. criar a regra especifica do admin
5. preencher `SECURITY_TRUSTED_PROXY_IPS` com proxies confiaveis reais
6. observar logs antes de promover IPs ou CIDRs para bloqueio permanente