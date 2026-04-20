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
PHONE_BLIND_INDEX_KEY=coloque-uma-chave-forte-separada-aqui
DJANGO_ALLOWED_HOSTS=homolog.seudominio.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://homolog.seudominio.com
DATABASE_URL=postgresql://postgres:senha@host:5432/octobox_control
DJANGO_ADMIN_URL_PATH=painel-interno-nao-obvio
REDIS_URL=redis://usuario:senha@host:6379/0
CACHE_IGNORE_EXCEPTIONS=True
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
3. o blueprint inclui tambem uma Key Value para a cache compartilhada
4. o processo web sobe com Gunicorn
5. o healthcheck usa `/api/v1/health/`
6. o `autoDeploy` fica desligado para que a publicacao venha do gate do GitHub Actions, e nao de qualquer push isolado na branch
7. a publicacao agora tambem depende do workflow `Student Onboarding Corridors Regression`, que trava o verde quando os corredores `link em massa`, `lead importado` e `aluno ja cadastrado` perdem cobertura explicita
8. a publicacao agora tambem depende do workflow `Student Onboarding Real Smoke`, que trava o release quando o fluxo real `staff cria convite -> aluno abre link -> OAuth -> Grade/WOD ou aguardando aprovacao` quebra

Observacoes importantes para Render:

1. o superuser continua sendo manual e deve ser criado depois do primeiro deploy
2. `PHONE_BLIND_INDEX_KEY` precisa ser preenchida manualmente no servico ou no Blueprint antes do primeiro build
3. `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS` continuam aceitando sobreposicao explicita e o runtime agora tambem absorve `RENDER_EXTERNAL_HOSTNAME` quando esse hostname existir
4. `DJANGO_ADMIN_URL_PATH` deve ser preenchido com um caminho nao obvio antes de abrir o ambiente
5. se quiser dominio proprio, configure-o no Render e mantenha `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS` como sobreposicao explicita quando necessario
6. para gate real de deploy, o repositorio agora espera publicar via `Render Production Gate & Deploy`, usando `RENDER_DEPLOY_HOOK_URL` e um GitHub Environment `production`
7. esse gate agora espera tres camadas juntas:
   - runtime base e integridade
   - seguranca
   - regressao explicita do onboarding do aluno
8. e uma quarta camada de comportamento real:
   - smoke ponta a ponta do onboarding do aluno

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
2. PHONE_BLIND_INDEX_KEY forte e fora do repositorio
3. DEBUG=False
4. ALLOWED_HOSTS preenchido
5. CSRF_TRUSTED_ORIGINS preenchido com HTTPS ou garantido via `RENDER_EXTERNAL_HOSTNAME`
6. PostgreSQL configurado
7. cache compartilhada configurada ou fallback local conscientemente aceito
8. admin privado configurado por `DJANGO_ADMIN_URL_PATH`
9. collectstatic executado
10. bootstrap_roles executado
11. superuser criado
12. backup do banco testado

## Proximo nivel depois disso

1. Sentry ou monitoramento de erro
2. logs estruturados
3. healthcheck dedicado
4. gate de CI e deploy via GitHub Actions antes de publicar
5. storage externo para media quando a aplicacao crescer
