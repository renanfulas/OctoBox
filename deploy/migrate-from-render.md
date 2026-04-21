# Migração Render → VPS Hostgator

Roteiro completo para sair do Render e rodar tudo no VPS em São Paulo.
Cada fase pode ser feita em dias separados — o Render continua no ar até o passo final.

---

## Fase 1 — Preparar o VPS (1–2h)

### 1.1 Setup inicial
```bash
# SSH no VPS como root
ssh root@129.121.47.167

# Clonar e rodar o setup
git clone https://github.com/renanfulas/OctoBox.git /srv/octobox
bash /srv/octobox/deploy/setup.sh
```

### 1.2 Criar as variáveis de ambiente
```bash
cp /srv/octobox/deploy/env.example /etc/octobox.env
chmod 600 /etc/octobox.env
chown octobox:octobox /etc/octobox.env
nano /etc/octobox.env   # preencha os valores reais
```

Gere o SECRET_KEY:
```bash
openssl rand -base64 50
```

### 1.3 Configurar backup no Google Drive
```bash
bash /srv/octobox/deploy/backup-setup.sh
```

### 1.4 Configurar monitoramento
```bash
apt-get install -y mailutils
# Edite o email em deploy/healthcheck.sh
nano /srv/octobox/deploy/healthcheck.sh

cp /srv/octobox/deploy/healthcheck.sh /usr/local/bin/octobox-healthcheck
chmod +x /usr/local/bin/octobox-healthcheck

echo "*/5 * * * * root /usr/local/bin/octobox-healthcheck" \
    > /etc/cron.d/octobox-healthcheck
```

---

## Fase 2 — Migrar o banco de dados do Render (30min)

### 2.1 Exportar do Render
No painel do Render, vá em **PostgreSQL → Connect → PSQL Command** e rode:
```bash
pg_dump $DATABASE_URL --no-acl --no-owner -Fc > render_export.dump
```

Ou direto pela connection string:
```bash
pg_dump "postgresql://usuario:senha@host.render.com/dbname" \
    --no-acl --no-owner -Fc > render_export.dump
```

### 2.2 Copiar para o VPS
```bash
scp render_export.dump root@129.121.47.167:/tmp/
```

### 2.3 Importar no VPS
```bash
# No VPS
sudo -u postgres pg_restore \
    --dbname=octobox \
    --no-acl --no-owner \
    --clean --if-exists \
    /tmp/render_export.dump

rm /tmp/render_export.dump
```

---

## Fase 3 — Testar o VPS antes de cortar o DNS (30min)

### 3.1 Subir o app
```bash
sudo -u octobox /srv/octobox/.venv/bin/python manage.py migrate --noinput
sudo -u octobox /srv/octobox/.venv/bin/python manage.py bootstrap_roles
sudo systemctl start octobox
sudo systemctl start nginx
```

### 3.2 Testar via IP (sem mexer no DNS)
Adicione temporariamente no `/etc/hosts` da sua máquina local:
```
129.121.47.167  octoboxfit.com.br
```

Acesse `https://octoboxfit.com.br` — se funcionar, está pronto.
Remova a linha do `/etc/hosts` depois.

### 3.3 Configurar HTTPS
```bash
sudo certbot --nginx -d octoboxfit.com.br -d www.octoboxfit.com.br
```

---

## Fase 4 — Adicionar secrets no GitHub (5min)

No repositório GitHub → **Settings → Secrets → Actions**, adicione:

| Secret | Valor |
|---|---|
| `VPS_HOST` | `129.121.47.167` |
| `VPS_USER` | `octobox` |
| `VPS_SSH_KEY` | Chave SSH privada (veja abaixo) |
| `VPS_PORT` | `22` |
| `SMOKE_BASE_URL_VPS` | `https://octoboxfit.com.br` |

Gerar a chave SSH para o GitHub Actions:
```bash
# No VPS
sudo -u octobox ssh-keygen -t ed25519 -f /home/octobox/.ssh/github_actions -N ""
cat /home/octobox/.ssh/github_actions.pub >> /home/octobox/.ssh/authorized_keys

# Copie a chave PRIVADA para o secret VPS_SSH_KEY
cat /home/octobox/.ssh/github_actions
```

---

## Fase 5 — Corte do DNS (5min de downtime)

### 5.1 Baixar o TTL antes (faça 24h antes se possível)
No painel DNS da Hostgator/Registro.br, mude o TTL dos registros A para **60 segundos**.

### 5.2 Na hora do corte
1. Aponte o registro A de `octoboxfit.com.br` para `129.121.47.167`
2. Aguarde propagação (1–5 min com TTL baixo)
3. Teste `curl https://octoboxfit.com.br/api/v1/health/`

### 5.3 Monitorar por 24h
```bash
# No VPS — acompanhe os logs em tempo real
journalctl -u octobox -f
tail -f /var/log/nginx/access.log
```

---

## Fase 6 — Desligar o Render (após 48h estável)

1. Exporte um último backup do Render como segurança
2. No painel Render: **Settings → Delete Service** para cada serviço
3. Cancel o plano

---

## Comandos úteis no VPS

```bash
# Status do app
systemctl status octobox

# Reiniciar sem downtime
systemctl reload octobox

# Logs do app
journalctl -u octobox -f

# Logs do Nginx
tail -f /var/log/nginx/error.log

# Backup manual agora
sudo -u octobox /srv/octobox/deploy/backup.sh

# Último backup gerado
ls -lh /backups/octobox/
```
