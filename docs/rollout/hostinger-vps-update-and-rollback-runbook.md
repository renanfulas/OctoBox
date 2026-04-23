<!--
ARQUIVO: runbook de update e rollback para Hostinger VPS.

TIPO DE DOCUMENTO:
- runbook operacional

AUTORIDADE:
- alta para manutencao da rota Hostinger VPS em producao

DOCUMENTOS IRMAOS:
- [hostinger-vps-production-deploy.md](hostinger-vps-production-deploy.md)
- [hostinger-vps-post-deploy-smoke-checklist.md](hostinger-vps-post-deploy-smoke-checklist.md)
- [hostinger-vps-backup-and-restore-runbook.md](hostinger-vps-backup-and-restore-runbook.md)
- [restore-and-rollback-drill.md](restore-and-rollback-drill.md)

QUANDO USAR:
- antes de atualizar a app em producao
- quando for preciso voltar rapidamente para uma release anterior
- quando a equipe quiser reduzir improviso em manutencao de VPS

POR QUE ELE EXISTE:
- deploy inicial sem ritual de update e rollback deixa a operacao vulneravel no segundo dia
- ajuda a equipe a trocar pneu com o carro parado, em vez de tentar aprender isso no meio da curva

PONTOS CRITICOS:
- este runbook cobre rollback de aplicacao; rollback de dados continua dependendo do runbook de backup e restore
- nao pular o smoke pos-update
- nao fazer rollback sem registrar o commit de retorno
-->

# Runbook de update e rollback para Hostinger VPS

## Objetivo

Atualizar e, se necessario, voltar o OctoBOX em uma Hostinger VPS sem improviso e com o menor risco possivel.

## Defaults desta rota

1. host canonico em `octoboxfit.com.br`
2. superficie de login e app em `app.octoboxfit.com.br`
3. VPS com `/srv/octobox/app`
4. `venv` em `/srv/octobox/venv`
5. env file em `/srv/octobox/shared/octobox.env`
6. Gunicorn via `octobox-gunicorn.service`
7. Nginx na frente

---

## Parte A. Update canonico

### Precondicoes

Antes de atualizar, confirme:

1. ultimo backup existe
2. o commit alvo esta identificado
3. a janela de manutencao esta clara
4. o responsavel tecnico esta definido
5. o rollback target esta definido

### Passo 1. Registrar o ponto atual

```bash
cd /srv/octobox/app
git rev-parse HEAD
```

Anote:

1. commit atual
2. commit alvo
3. horario de inicio

### Passo 2. Fazer backup preventivo

Antes de atualizar, gere um backup novo do banco.

Referencia:

1. [hostinger-vps-backup-and-restore-runbook.md](hostinger-vps-backup-and-restore-runbook.md)

### Passo 3. Atualizar o codigo

```bash
cd /srv/octobox/app
sudo -u octobox git fetch --all
sudo -u octobox git checkout <COMMIT_OU_BRANCH_ALVO>
sudo -u octobox /srv/octobox/venv/bin/pip install -r /srv/octobox/app/requirements.txt
```

### Passo 4. Aplicar migrações e static files

```bash
cd /srv/octobox/app
sudo -u octobox bash -lc 'set -a && source /srv/octobox/shared/octobox.env && set +a && /srv/octobox/venv/bin/python manage.py migrate'
sudo -u octobox bash -lc 'set -a && source /srv/octobox/shared/octobox.env && set +a && /srv/octobox/venv/bin/python manage.py collectstatic --noinput'
sudo -u octobox bash -lc 'set -a && source /srv/octobox/shared/octobox.env && set +a && /srv/octobox/venv/bin/python manage.py check'
```

### Passo 5. Reiniciar o runtime

```bash
sudo systemctl restart octobox-gunicorn
sudo systemctl status octobox-gunicorn
sudo systemctl status nginx
```

### Passo 6. Rodar smoke curto

Checklist minimo:

1. `https://octoboxfit.com.br/api/v1/health/`
2. `https://app.octoboxfit.com.br/login/`
3. dashboard
4. alunos
5. operacao
6. grade

Referencia:

1. [hostinger-vps-post-deploy-smoke-checklist.md](hostinger-vps-post-deploy-smoke-checklist.md)

### Failure checks do update

Se qualquer item abaixo acontecer, o update falhou:

1. `migrate` falha
2. `collectstatic` falha
3. Gunicorn nao volta
4. healthcheck falha
5. login quebra
6. uma rota central retorna `500`

---

## Parte B. Rollback canonico de aplicacao

### Quando usar

Use rollback quando:

1. a release nova sobe mas o comportamento ficou quebrado
2. a app nao volta saudavel apos update
3. o smoke funcional reprova

### Passo 1. Voltar para o commit anterior bom

```bash
cd /srv/octobox/app
sudo -u octobox git checkout <COMMIT_ANTERIOR_BOM>
sudo -u octobox /srv/octobox/venv/bin/pip install -r /srv/octobox/app/requirements.txt
```

### Passo 2. Reaplicar static files

```bash
cd /srv/octobox/app
sudo -u octobox bash -lc 'set -a && source /srv/octobox/shared/octobox.env && set +a && /srv/octobox/venv/bin/python manage.py collectstatic --noinput'
```

### Passo 3. Reiniciar o Gunicorn

```bash
sudo systemctl restart octobox-gunicorn
sudo systemctl status octobox-gunicorn
```

### Passo 4. Validar o retorno

Checklist minimo:

1. `https://octoboxfit.com.br/api/v1/health/`
2. `https://app.octoboxfit.com.br/login/`
3. dashboard
4. operacao

### Quando subir para rollback de dados

Se o problema estiver nos dados e nao apenas na release:

1. parar
2. nao improvisar
3. seguir [hostinger-vps-backup-and-restore-runbook.md](hostinger-vps-backup-and-restore-runbook.md)

### Failure checks do rollback

Se qualquer item abaixo falhar, o rollback deve ser considerado reprovado:

1. a equipe nao sabe qual e o ultimo commit bom
2. o app volta mas o health continua falhando
3. login continua quebrado
4. rotas centrais continuam retornando `500`

---

## Registro minimo da manutencao

Sempre registrar:

1. commit anterior
2. commit novo
3. horario de inicio
4. horario de fim
5. operador
6. resultado
7. se houve rollback

## Incidente de referencia: mismatch de interface de rede

Em `2026-04-15`, a VPS do OctoBox ficou fora do ar nao por falha do Django, mas por mismatch entre a interface real da maquina e a interface declarada na configuracao de rede.

Leitura objetiva do incidente:

1. a interface publica viva da VPS era `ens3`
2. o `netplan` ativo e o `cloud-init` legado ainda apontavam para `ens4`
3. apos reboot, `ens3` ficou `unmanaged`, sem IPv4 e sem rota default
4. com isso, SSH `22022` e HTTPS `443` ficaram indisponiveis ao mesmo tempo
5. `nginx` e `octobox-gunicorn` continuavam saudaveis localmente, mas isolados da rede

Correcao aplicada:

1. corrigir `/etc/netplan/50-cloud-init.yaml` para `ens3`
2. corrigir `/etc/cloud/cloud.cfg.d/90-installer-network.cfg` para `ens3`
3. alinhar o backup local `/etc/netplan/50-cloud-init.yaml.bak`
4. aplicar `netplan generate` e `netplan apply`
5. validar `ip a`, `ip route`, `ping 8.8.8.8`, SSH, HTTPS e healthcheck

Checklist de prevencao antes de qualquer reboot:

1. `ip a` confirma a interface publica real
2. `cat /etc/netplan/*.yaml` e `grep -R "ens3\|ens4\|network:" -n /etc/cloud /etc/netplan` nao mostram nome legado conflitante
3. `networkctl status <interface>` nao mostra `unmanaged`
4. SSH e HTTPS sao testados novamente apos reboot controlado

## Formula curta

Se a equipe nao consegue atualizar e voltar sem panico, a operacao ainda nao esta pronta para producao assistida.
