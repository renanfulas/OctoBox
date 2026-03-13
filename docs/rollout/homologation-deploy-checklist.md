<!--
ARQUIVO: checklist exato para subir a homologacao do OctoBox com validacao tecnica e criterio de pronto.

TIPO DE DOCUMENTO:
- checklist operacional

AUTORIDADE:
- media

DOCUMENTO PAI:
- [deploy-homologation.md](deploy-homologation.md)

QUANDO USAR:
- quando a duvida for qual sequencia exata validar antes de considerar a homologacao pronta para uso piloto

POR QUE ELE EXISTE:
- transforma o guia geral de deploy em uma sequencia curta e executavel.
- reduz chance de esquecer etapa critica antes de abrir o sistema para boxes piloto.

O QUE ESTE ARQUIVO FAZ:
1. organiza pre-deploy, deploy e pos-deploy.
2. define variaveis minimas e comandos obrigatorios.
3. registra smoke tests e rollback minimo.

PONTOS CRITICOS:
- este checklist assume PostgreSQL, HTTPS e `DJANGO_ENV=production`.
- se qualquer validacao critica falhar, a homologacao nao deve ser aberta para cliente piloto.
-->

# Checklist exato de deploy para homologacao

## Objetivo

Subir uma homologacao publica estavel o suficiente para:

1. validar ambiente real
2. testar onboarding do primeiro box
3. operar o piloto com risco controlado

## Definicao de pronto

A homologacao so pode ser considerada pronta quando:

1. a aplicacao sobe com `DJANGO_ENV=production`
2. login funciona
3. arquivos estaticos carregam sem erro
4. migracoes aplicam sem quebrar
5. `bootstrap_roles` foi executado
6. backup foi gerado e verificado
7. a rota [api/v1/health/](../../api/v1/urls.py) responde OK

## Etapa 0: decidir a hospedagem

Escolher agora:

1. plataforma de deploy
2. banco PostgreSQL
3. dominio ou subdominio de homologacao

Recomendacao pragmatica:

1. Render
2. Railway
3. Fly.io
4. VPS simples com Caddy ou Nginx

Critério:

1. precisa suportar variaveis de ambiente, processo web, PostgreSQL e HTTPS facil

## Etapa 1: preparar os segredos e variaveis

Variaveis minimas obrigatorias:

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

Checklist:

1. `DJANGO_SECRET_KEY` forte e fora do repositorio
2. `DJANGO_ALLOWED_HOSTS` preenchido com o host real
3. `DJANGO_CSRF_TRUSTED_ORIGINS` com HTTPS real
4. `DATABASE_URL` validada
5. `DB_SSL_REQUIRE` coerente com o provedor do banco

## Etapa 2: preparar o banco

Checklist:

1. criar banco PostgreSQL da homologacao
2. confirmar host, porta, usuario e senha
3. validar acesso do ambiente de deploy ao banco

Teste minimo:

1. a aplicacao precisa conseguir executar `migrate` sem erro

## Etapa 3: instalar dependencias e publicar a aplicacao

Comandos obrigatorios no ambiente:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py bootstrap_roles
python manage.py createsuperuser
```

Checklist:

1. dependencias instaladas
2. migracoes aplicadas
3. static files coletados
4. grupos de acesso criados
5. superuser criado

## Etapa 4: validar o processo web

Checklist:

1. processo da aplicacao sobe sem exception de startup
2. `DJANGO_SECRET_KEY` nao dispara fail-fast
3. WhiteNoise serve assets corretamente
4. root URL abre sem erro 500

Arquivos centrais desta validacao:

1. [config/settings/base.py](../../config/settings/base.py)
2. [config/settings/production.py](../../config/settings/production.py)
3. [config/urls.py](../../config/urls.py)

## Etapa 5: smoke test obrigatorio

Executar e validar manualmente:

1. abrir `/login/`
2. fazer login com superuser
3. abrir `/dashboard/`
4. abrir `/alunos/`
5. abrir `/grade-aulas/`
6. abrir `/operacao/`
7. abrir `/api/v1/health/`
8. confirmar que CSS e layout carregaram corretamente
9. confirmar que logout funciona

Checklist de resultado:

1. sem erro 500
2. sem pagina sem estilo
3. sem rota critica quebrada
4. sem problema evidente de permissao no fluxo base

## Etapa 6: validar backup antes de abrir para piloto

Checklist:

1. gerar backup inicial do banco
2. confirmar tamanho e timestamp do arquivo
3. registrar onde o backup fica salvo
4. testar restauracao em ambiente isolado quando possivel

Referencia:

1. [backup-guide.md](backup-guide.md)
2. [scripts/backup_postgres.ps1](../../scripts/backup_postgres.ps1)

## Etapa 7: registrar o estado da homologacao

Registrar internamente:

1. URL da homologacao
2. data do deploy
3. hash ou versao publicada
4. banco usado
5. responsavel pelo deploy
6. responsavel pelo suporte do piloto

## Etapa 8: criterio de liberacao para o primeiro box

So liberar se todos os itens abaixo estiverem verdes:

1. login OK
2. dashboard OK
3. alunos OK
4. Recepcao OK
5. grade em leitura OK
6. backup OK
7. healthcheck OK
8. papeis bootstrapados

Se qualquer item critico falhar:

1. homologacao continua interna
2. nao abrir para box piloto ainda

## Rollback minimo

Se o deploy sair ruim:

1. bloquear a liberacao para cliente
2. voltar para a versao anterior da aplicacao
3. manter o banco atual se nao houve migracao destrutiva
4. restaurar backup apenas se a migracao ou operacao tiver corrompido estado

## Sequencia exata recomendada

1. escolher plataforma e banco
2. criar variaveis de ambiente
3. publicar a app
4. rodar migracoes
5. rodar `collectstatic`
6. rodar `bootstrap_roles`
7. criar superuser
8. abrir smoke test
9. gerar backup inicial
10. liberar homologacao para uso interno do piloto

## Formula curta

Para a homologacao existir de verdade, precisamos sair desta sequencia com quatro certezas:

1. sobe
2. loga
3. persiste
4. recupera