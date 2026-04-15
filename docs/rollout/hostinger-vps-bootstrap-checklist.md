<!--
ARQUIVO: checklist de bootstrap da Hostinger VPS para o OctoBOX.

TIPO DE DOCUMENTO:
- checklist operacional

AUTORIDADE:
- alta para preparar a maquina do primeiro cliente

DOCUMENTO PAI:
- [hostinger-vps-production-deploy.md](hostinger-vps-production-deploy.md)

QUANDO USAR:
- antes do primeiro deploy na Hostinger VPS
- sempre que uma nova VPS for preparada para repetir a topologia

PONTOS CRITICOS:
- este checklist trata apenas da base da maquina
- deploy, smoke e backup tem checklists proprios
-->

# Checklist de bootstrap da Hostinger VPS

Use:

- `[ ]` nao iniciado
- `[~]` em andamento
- `[x]` validado
- `[!]` bloqueador

## 1. Compra e identidade

- [ ] VPS criada em Sao Paulo
- [ ] Ubuntu LTS selecionado
- [ ] IP da VPS registrado
- [ ] dominio registrado
- [ ] conta do Cloudflare pronta

## 2. Acesso e seguranca

- [ ] acesso SSH confirmado
- [ ] usuario administrativo proprio criado
- [ ] chave SSH configurada
- [ ] rotina fora de `root` definida
- [ ] firewall ativo com `22`, `80` e `443`

## 3. Pacotes e servicos base

- [ ] `git` instalado
- [ ] `python3` instalado
- [ ] `python3-venv` instalado
- [ ] `nginx` instalado
- [ ] `postgresql` instalado
- [ ] `redis-server` instalado
- [ ] `postgresql`, `redis-server` e `nginx` iniciam no boot

## 4. Estrutura do OctoBOX

- [ ] `/srv/octobox/app` criado
- [ ] `/srv/octobox/venv` criado
- [ ] `/srv/octobox/shared` criado
- [ ] `/srv/octobox/backups` criado
- [ ] usuario `octobox` criado
- [ ] permissoes revisadas

## 5. Runtime e envs

- [ ] repositorio clonado em `/srv/octobox/app`
- [ ] `venv` criada
- [ ] `requirements.txt` instalado
- [ ] `/srv/octobox/shared/octobox.env` criado
- [ ] `DJANGO_ENV=production`
- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` definido
- [ ] `PHONE_BLIND_INDEX_KEY` definido
- [ ] `DATABASE_URL` definido
- [ ] `REDIS_URL` definido
- [ ] `DJANGO_ALLOWED_HOSTS` definido
- [ ] `BOX_RUNTIME_SLUG` definido
- [ ] `DJANGO_ADMIN_URL_PATH` definido

## 6. Banco e cache

- [ ] usuario PostgreSQL da app criado
- [ ] banco `octobox_control` criado
- [ ] senha forte definida
- [ ] PostgreSQL escutando localmente
- [ ] Redis escutando localmente
- [ ] Redis sem exposicao publica

## 7. Bootstrap do Django

- [ ] `migrate` executado
- [ ] `collectstatic --noinput` executado
- [ ] `bootstrap_roles` executado
- [ ] `createsuperuser` executado
- [ ] `manage.py check` executado

## 8. Publicacao web

- [ ] `octobox-gunicorn.service` instalado
- [ ] servico Gunicorn ativo
- [ ] `octobox.conf` do Nginx instalado
- [ ] `nginx -t` verde
- [ ] `nginx` reiniciado sem erro

## 9. Borda e go-live

- [ ] dominio atras do Cloudflare
- [ ] proxy do Cloudflare ativo
- [ ] WAF ativo
- [ ] admin privado fora do caminho padrao
- [ ] regras de edge aplicadas

## 10. Gate de pronto

Nao abrir para cliente real se qualquer item abaixo estiver em `nao`.

- [ ] healthcheck responde
- [ ] login responde
- [ ] dashboard responde
- [ ] alunos responde
- [ ] operacao responde
- [ ] grade responde
- [ ] backup diario configurado
- [ ] restore ensaiado
- [ ] reboot da VPS validado
