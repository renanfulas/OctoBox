<!--
ARQUIVO: guia canonico de deploy do OctoBOX em Hostinger VPS.

TIPO DE DOCUMENTO:
- guia operacional de producao

AUTORIDADE:
- alta para a rota Hostinger VPS do primeiro cliente

DOCUMENTOS IRMAOS:
- [hostinger-vps-bootstrap-checklist.md](hostinger-vps-bootstrap-checklist.md)
- [hostinger-vps-post-deploy-smoke-checklist.md](hostinger-vps-post-deploy-smoke-checklist.md)
- [hostinger-vps-backup-and-restore-runbook.md](hostinger-vps-backup-and-restore-runbook.md)
- [../reference/production-security-baseline.md](../reference/production-security-baseline.md)
- [../reference/cloudflare-edge-rules.md](../reference/cloudflare-edge-rules.md)

QUANDO USAR:
- quando a decisao for publicar o primeiro cliente em uma Hostinger VPS
- quando o deploy for sem Docker, com runtime nativo Linux
- quando a operacao quiser um roteiro repetivel e pedagogico

POR QUE ELE EXISTE:
- traduz a base atual do projeto para uma VPS Linux controlada pela equipe
- evita deploy improvisado com passos lembrados de cabeca
- documenta a arquitetura minima recomendada para o primeiro cliente

PONTOS CRITICOS:
- este guia assume Ubuntu LTS, Cloudflare na frente e PostgreSQL + Redis na mesma VPS
- nao substitui backup, restore e smoke funcional
- nao publicar com SQLite, runserver ou Redis exposto
-->

# Deploy canonico do OctoBOX em Hostinger VPS

## Objetivo

Publicar o OctoBOX em uma Hostinger VPS com:

1. Ubuntu LTS
2. Cloudflare na frente do dominio
3. `Nginx -> Gunicorn -> Django`
4. PostgreSQL local
5. Redis local
6. `systemd` cuidando dos servicos
7. backup e restore reais

Em linguagem simples:

1. a VPS e a casa
2. o Nginx e a portaria
3. o Gunicorn e o corredor interno
4. o Django e o apartamento
5. o Postgres e o cofre
6. o Redis e a memoria de curto prazo

---

## Arquitetura travada para esta rota

Defaults obrigatorios deste guia:

1. provedor: Hostinger VPS
2. regiao: Sao Paulo
3. sistema operacional: Ubuntu LTS
4. borda publica: Cloudflare
5. banco: PostgreSQL na mesma VPS
6. cache: Redis na mesma VPS
7. runtime Python: `venv`
8. processo web: Gunicorn
9. reverse proxy: Nginx
10. processo manager: `systemd`
11. sem Docker no v1
12. sem SQLite em producao

---

## Configuracao minima recomendada da VPS

Nao use o menor plano como padrao se a app, o banco e o Redis vao morar juntos.

Configuracao recomendada:

1. `2 vCPU`
2. `8 GB RAM`
3. `100 GB NVMe`

Minimo aceitavel apenas para inicio muito enxuto:

1. `1 vCPU`
2. `4 GB RAM`
3. `50 GB NVMe`

Sinal vermelho:

1. subir app, Postgres e Redis juntos em plano com pouca RAM
2. deixar disco sem folga para `collectstatic`, logs e dumps

---

## Estrutura recomendada na VPS

```text
/srv/octobox/
|-- app/                  -> checkout do repositorio
|-- venv/                 -> ambiente virtual Python
|-- shared/
|   `-- octobox.env       -> segredos e envs de producao
`-- backups/              -> dumps temporarios locais
```

Arquivos de apoio do projeto:

1. template `systemd`: [../../infra/hostinger-vps/systemd/octobox-gunicorn.service](../../infra/hostinger-vps/systemd/octobox-gunicorn.service)
2. template `nginx`: [../../infra/hostinger-vps/nginx/octobox.conf](../../infra/hostinger-vps/nginx/octobox.conf)
3. script Linux de backup: [../../scripts/linux/backup_postgres.sh](../../scripts/linux/backup_postgres.sh)

---

## Passo a passo de deploy

### Etapa 1. Comprar e registrar a base

1. contratar a VPS em Sao Paulo
2. escolher Ubuntu LTS
3. anotar IP, usuario inicial, dominio e acesso SSH
4. colocar o dominio atras do Cloudflare antes do go-live

### Etapa 2. Endurecer a maquina

Entrar por SSH e rodar:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3 python3-venv python3-pip nginx postgresql redis-server ufw build-essential libpq-dev pkg-config
```

Depois:

1. criar um usuario administrativo proprio
2. configurar chave SSH
3. evitar usar `root` como rotina
4. ligar o firewall

Exemplo:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Etapa 3. Criar o usuario da app e estrutura de runtime

```bash
sudo adduser --system --group --home /srv/octobox octobox
sudo mkdir -p /srv/octobox/app /srv/octobox/shared /srv/octobox/backups /run/octobox
sudo chown -R octobox:octobox /srv/octobox /run/octobox
```

### Etapa 4. Clonar o projeto e instalar dependencias

```bash
sudo -u octobox git clone <SEU_REPOSITORIO_GIT> /srv/octobox/app
sudo -u octobox python3 -m venv /srv/octobox/venv
sudo -u octobox /srv/octobox/venv/bin/pip install --upgrade pip
sudo -u octobox /srv/octobox/venv/bin/pip install -r /srv/octobox/app/requirements.txt
```

### Etapa 5. Configurar PostgreSQL

Dentro do `psql`, criar usuario e banco dedicados:

```sql
CREATE USER octobox_app WITH PASSWORD 'troque-esta-senha';
CREATE DATABASE octobox_control OWNER octobox_app;
GRANT ALL PRIVILEGES ON DATABASE octobox_control TO octobox_app;
```

Confirmacoes obrigatorias:

1. o Postgres escuta apenas localmente, salvo necessidade real
2. a senha e forte e nao vai para o repositorio

### Etapa 6. Configurar Redis local

Defaults desta rota:

1. Redis em `127.0.0.1:6379`
2. sem exposicao publica
3. uso para cache, sessao e snapshots

### Etapa 7. Criar o arquivo de ambiente

Criar `/srv/octobox/shared/octobox.env` com base em [.env.example](../../.env.example).

Minimo obrigatorio:

```env
DJANGO_ENV=production
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=gere-um-segredo-forte
PHONE_BLIND_INDEX_KEY=gere-uma-chave-forte-separada
DJANGO_ALLOWED_HOSTS=app.seudominio.com
DATABASE_URL=postgresql://octobox_app:troque-esta-senha@127.0.0.1:5432/octobox_control
REDIS_URL=redis://127.0.0.1:6379/0
BOX_RUNTIME_SLUG=box-piloto-vila-mar
OPERATIONS_MANAGER_WORKSPACE_ENABLED=False
DJANGO_ADMIN_URL_PATH=troque-por-caminho-longo-nao-obvio
DJANGO_SECURE_SSL_REDIRECT=True
SECURITY_TRUSTED_PROXY_IPS=
```

Se o piloto incluir manager no dia 1:

```env
OPERATIONS_MANAGER_WORKSPACE_ENABLED=True
```

### Etapa 8. Bootstrap do Django

```bash
cd /srv/octobox/app
sudo -u octobox bash -lc 'set -a && source /srv/octobox/shared/octobox.env && set +a && /srv/octobox/venv/bin/python manage.py migrate'
sudo -u octobox bash -lc 'set -a && source /srv/octobox/shared/octobox.env && set +a && /srv/octobox/venv/bin/python manage.py collectstatic --noinput'
sudo -u octobox bash -lc 'set -a && source /srv/octobox/shared/octobox.env && set +a && /srv/octobox/venv/bin/python manage.py bootstrap_roles'
sudo -u octobox bash -lc 'set -a && source /srv/octobox/shared/octobox.env && set +a && /srv/octobox/venv/bin/python manage.py createsuperuser'
sudo -u octobox bash -lc 'set -a && source /srv/octobox/shared/octobox.env && set +a && /srv/octobox/venv/bin/python manage.py check'
```

### Etapa 9. Subir Gunicorn via systemd

1. copiar o template `systemd` para `/etc/systemd/system/octobox-gunicorn.service`
2. ajustar dominio, usuario e caminhos se necessario
3. recarregar o daemon e subir o servico

```bash
sudo systemctl daemon-reload
sudo systemctl enable octobox-gunicorn
sudo systemctl start octobox-gunicorn
sudo systemctl status octobox-gunicorn
```

### Etapa 10. Configurar o Nginx

1. copiar o template de [../../infra/hostinger-vps/nginx/octobox.conf](../../infra/hostinger-vps/nginx/octobox.conf) para `/etc/nginx/sites-available/octobox.conf`
2. ajustar `server_name`
3. habilitar o site
4. testar a configuracao
5. reiniciar o Nginx

```bash
sudo ln -s /etc/nginx/sites-available/octobox.conf /etc/nginx/sites-enabled/octobox.conf
sudo nginx -t
sudo systemctl restart nginx
```

### Etapa 11. Fechar a borda no Cloudflare

1. apontar DNS para a VPS
2. manter o proxy do Cloudflare ativo
3. ativar WAF
4. aplicar as regras de [../reference/cloudflare-edge-rules.md](../reference/cloudflare-edge-rules.md)
5. preencher `SECURITY_TRUSTED_PROXY_IPS` apenas quando houver confirmacao dos proxies reais

### Etapa 12. Validar a publicacao

Rotas obrigatorias:

1. `/api/v1/health/`
2. `/login/`
3. `/dashboard/`
4. `/alunos/`
5. `/operacao/`
6. `/grade-aulas/`

O deploy so passa quando:

1. health responde
2. login funciona
3. assets carregam
4. as rotas centrais nao retornam `500`

---

## Contrato operacional minimo

Antes de abrir para cliente real, confirme:

1. `DEBUG=False`
2. `DJANGO_SECRET_KEY` forte
3. `PHONE_BLIND_INDEX_KEY` forte
4. `DATABASE_URL` apontando para PostgreSQL
5. `REDIS_URL` apontando para Redis
6. `DJANGO_ADMIN_URL_PATH` nao obvio
7. backup diario configurado
8. restore ensaiado
9. Cloudflare ativo
10. reboot da VPS nao derruba a app permanentemente

---

## Pos-deploy imediato

Depois do primeiro deploy:

1. rodar o checklist [hostinger-vps-post-deploy-smoke-checklist.md](hostinger-vps-post-deploy-smoke-checklist.md)
2. configurar backup diario com [hostinger-vps-backup-and-restore-runbook.md](hostinger-vps-backup-and-restore-runbook.md)
3. registrar evidencias do go-live
