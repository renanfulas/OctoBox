<!--
ARQUIVO: guia de deploy para homologacao e pacote minimo de producao.

TIPO DE DOCUMENTO:
- guia operacional de deploy

AUTORIDADE:
- media

DOCUMENTO PAI:
- [first-box-rollout-plan.md](first-box-rollout-plan.md)

QUANDO USAR:
- quando a duvida for como publicar um ambiente de homologacao minimamente estavel fora da maquina local

POR QUE ELE EXISTE:
- Traduz a nova camada de configuracao em um roteiro executavel de publicacao.

O QUE ESTE ARQUIVO FAZ:
1. Define variaveis minimas de ambiente.
2. Explica PostgreSQL, collectstatic e HTTPS.
3. Resume o checklist minimo antes de abrir para usuarios reais.

PONTOS CRITICOS:
- Este guia depende da configuracao em config/settings/ e precisa andar junto com ela.
-->

# Deploy de homologacao e pacote minimo de producao

Este guia cobre o minimo para tirar o projeto do modo local e colocar em um ambiente de homologacao mais estavel.

## Objetivo

Levar o projeto para um ambiente com:

1. PostgreSQL
2. variaveis de ambiente
3. static files coletados corretamente
4. HTTPS na borda
5. rotina minima de backup

## Configuracao de ambiente

O projeto agora usa DJANGO_ENV para escolher o conjunto de settings:

1. development
2. production

Para homologacao, use DJANGO_ENV=production.

Variaveis minimas recomendadas:

```env
DJANGO_ENV=production
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=coloque-uma-chave-forte-aqui
DJANGO_ALLOWED_HOSTS=homolog.seudominio.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://homolog.seudominio.com
DATABASE_URL=postgresql://postgres:senha@host:5432/octobox_control
DB_SSL_REQUIRE=True
DJANGO_SECURE_SSL_REDIRECT=True
```

## Instalacao

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py bootstrap_roles
python manage.py createsuperuser
```

## Processo web

O repositorio agora inclui um [Procfile](../../Procfile) com um processo web simples via Gunicorn.

Comando minimo para hosts com start command explicito:

```bash
gunicorn config.wsgi --log-file -
```

## Fluxo recomendado no Render

O repositorio agora inclui um [render.yaml](../../render.yaml) para subir um web service Django e um PostgreSQL gerenciado no Render com o minimo de friccao.

Leitura pratica desse fluxo:

1. o build instala dependencias e roda `collectstatic`
2. o pre-deploy roda `migrate` e `bootstrap_roles`
3. o processo web sobe com Gunicorn
4. o healthcheck usa `/api/v1/health/`

Observacoes importantes para Render:

1. o superuser continua sendo manual e deve ser criado depois do primeiro deploy
2. `RENDER_EXTERNAL_HOSTNAME` e absorvido automaticamente pelo Django para `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`
3. se quiser dominio proprio, configure-o no Render e mantenha `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS` como sobreposicao explicita quando necessario

## Static files

Em homologacao e producao, o projeto usa WhiteNoise. Isso permite um deploy simples sem depender imediatamente de um bucket ou CDN.

Fluxo:

1. rodar collectstatic
2. publicar a pasta staticfiles junto da aplicacao
3. manter DEBUG desligado

## HTTPS

O Django agora suporta endurecimento de HTTPS por configuracao.

O ideal e terminar TLS no proxy reverso ou plataforma de hospedagem, por exemplo:

1. Nginx
2. Railway
3. Render
4. Fly.io
5. VPS com Caddy

Se o proxy enviar X-Forwarded-Proto corretamente, o Django respeita isso via SECURE_PROXY_SSL_HEADER.

## Banco de dados

Localmente o projeto continua aceitando SQLite.

Para homologacao e producao, o caminho minimo recomendado e PostgreSQL via DATABASE_URL.

Exemplo:

```env
DATABASE_URL=postgresql://postgres:senha@localhost:5432/octobox_control
```

## Checklist minimo antes de abrir para usuarios reais

1. DJANGO_SECRET_KEY forte e fora do repositorio
2. DEBUG=False
3. ALLOWED_HOSTS preenchido
4. CSRF_TRUSTED_ORIGINS preenchido com HTTPS
5. PostgreSQL configurado
6. collectstatic executado
7. bootstrap_roles executado
8. superuser criado
9. backup do banco testado

## Proximo nivel depois disso

1. Sentry ou monitoramento de erro
2. logs estruturados
3. healthcheck dedicado
4. CI para testes e check antes de deploy
5. storage externo para media quando a aplicacao crescer