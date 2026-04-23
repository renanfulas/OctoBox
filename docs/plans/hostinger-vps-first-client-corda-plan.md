<!--
ARQUIVO: C.O.R.D.A. operacional para publicar o primeiro cliente do OctoBOX em Hostinger VPS.

TIPO DE DOCUMENTO:
- plano operacional e prompt reutilizavel

AUTORIDADE:
- alta para a rota Hostinger VPS do primeiro cliente

DOCUMENTOS IRMAOS:
- [../rollout/hostinger-vps-production-deploy.md](../rollout/hostinger-vps-production-deploy.md)
- [../rollout/hostinger-vps-bootstrap-checklist.md](../rollout/hostinger-vps-bootstrap-checklist.md)
- [../rollout/hostinger-vps-post-deploy-smoke-checklist.md](../rollout/hostinger-vps-post-deploy-smoke-checklist.md)
- [../rollout/hostinger-vps-backup-and-restore-runbook.md](../rollout/hostinger-vps-backup-and-restore-runbook.md)
- [../reference/production-security-baseline.md](../reference/production-security-baseline.md)
- [../reference/cloudflare-edge-rules.md](../reference/cloudflare-edge-rules.md)

QUANDO USAR:
- quando a decisao for publicar o primeiro cliente em uma Hostinger VPS
- quando precisarmos revisar se a rota VPS esta madura o suficiente para producao
- quando quisermos orientar um agente ou engenheiro com um contrato completo, sem lacunas operacionais perigosas

POR QUE ELE EXISTE:
- transforma a rota Hostinger VPS em plano executavel, nao em checklist solto
- incorpora os gaps que normalmente ficam escondidos no primeiro deploy real
- aplica o criterio do prompt-engineer: um objetivo principal, contrato explicito, falhas conhecidas e criterio de aceite

O QUE ESTE ARQUIVO FAZ:
1. consolida o contexto oficial da rota Hostinger VPS para o primeiro cliente
2. define objetivo, riscos, direcao e acoes sem deixar decisoes importantes em aberto
3. explicita os gaps corrigidos que faltavam no plano anterior
4. fornece um prompt operacional reutilizavel em formato C.O.R.D.A.

PONTOS CRITICOS:
- este documento assume `octoboxfit.com.br` como host canonico e `app.octoboxfit.com.br` como superficie principal de login e app
- este documento nao autoriza go-live sem TLS na origem, backup com copia externa e restore ensaiado
- este documento nao autoriza `www.octoboxfit.com.br` nem `www.app.octoboxfit.com.br` como host principal, Redis publico, PostgreSQL publico ou deploy com `runserver`
-->

# C.O.R.D.A. - Primeiro cliente em Hostinger VPS

## C - Contexto

O OctoBOX ja tem base de producao para:

1. `DJANGO_ENV=production`
2. `Gunicorn`
3. `PostgreSQL`
4. `Redis`
5. `collectstatic`
6. `healthcheck`
7. endurecimento basico de HTTPS, cookies e throttles

A decisao operacional agora e:

1. usar `octoboxfit.com.br` como host canonico publico
2. usar `app.octoboxfit.com.br` como superficie principal de login e app
3. hospedar o runtime em Hostinger VPS, em Sao Paulo
4. manter `PostgreSQL` e `Redis` na mesma VPS do app no v1
5. usar `Cloudflare` na frente do dominio do app

O plano anterior ja estava bom no esqueleto, mas ainda tinha lacunas importantes:

1. faltava TLS na origem
2. faltava evitar hosts duplicados sem funcao clara
3. faltava hardening explicito de SSH
4. faltava verificacao concreta de `PostgreSQL` e `Redis` ouvindo apenas localmente
5. faltava runbook de update e rollback
6. faltava endurecer o backup para nao depender de cron fragil com senha inline
7. faltava revisar o numero inicial de workers do Gunicorn

Em linguagem simples:

1. a casa ja tinha planta e material
2. faltava instalar fechadura, camera, copia da chave e um manual de como reabrir a porta se algo desse errado

## O - Objetivo

Colocar o primeiro cliente no ar em `octoboxfit.com.br`, com `app.octoboxfit.com.br` para login e superficie autenticada, usando uma topologia simples, legivel e suficientemente segura para producao inicial.

Sucesso significa:

1. a VPS sobe e volta sozinha apos reboot
2. `octoboxfit.com.br` responde via HTTPS fim a fim
3. `app.octoboxfit.com.br` responde via HTTPS fim a fim
4. Cloudflare opera em `Full (strict)`
5. `PostgreSQL` e `Redis` nao estao expostos publicamente
6. o app responde em `health`, login, dashboard, alunos, operacao e grade
7. existe backup diario com copia externa
8. o restore foi ensaiado em banco isolado
9. existe roteiro de update e rollback
10. o deploy pode ser repetido por outra pessoa sem adivinhacao

## R - Riscos

### 1. Risco de HTTPS incompleto

Se o app ficar so com Cloudflare na frente, sem certificado valido na origem:

1. o deploy parece seguro
2. mas a corrente de confianca fica fraca ou improvisada

Decisao:

1. usar `Cloudflare Full (strict)`
2. instalar certificado na origem
3. Nginx deve responder em `443`
4. `80` deve apenas redirecionar para `https`

### 2. Risco de naming e host duplicado no app

Se tentarmos tratar `www.octoboxfit.com.br` ou `www.app.octoboxfit.com.br` como host principal:

1. o app fica com naming feio e desnecessario
2. a configuracao de host e redirect fica mais fragil

Decisao:

1. o host canonico publico e `octoboxfit.com.br`
2. a superficie principal de login e app e `app.octoboxfit.com.br`
3. variantes com `www` nao serao usadas como host principal
4. se existirem, devem apenas redirecionar

### 3. Risco de operador sem perceber que virou operador

Em VPS, a equipe passa a ser responsavel por:

1. sistema operacional
2. SSH
3. firewall
4. processos
5. banco
6. cache
7. backup
8. logs
9. atualizacoes

Decisao:

1. explicitar isso no plano
2. transformar update e rollback em rotina formal

### 4. Risco de banco e cache expostos

Se `PostgreSQL` ou `Redis` ouvirem em interface publica:

1. a casa fica com janela do cofre aberta

Decisao:

1. bind local apenas
2. validacao explicita com comando de rede

### 5. Risco de backup decorativo

Se o backup depender de cron fragil, senha inline e sem copia externa:

1. a equipe acha que esta protegida
2. mas descobre o contrario no primeiro incidente real

Decisao:

1. preferir `.pgpass` ou secret local seguro
2. usar `root` com permissao explicita ou `systemd timer`
3. enviar copia para fora da VPS
4. ensaiar restore em banco isolado

### 6. Risco de tuning prematuro ou tuning ruim

Se travarmos `3` workers do Gunicorn sem olhar a VPS inicial:

1. podemos desperdiçar RAM
2. podemos matar folga que o Postgres e o Redis precisavam

Decisao:

1. iniciar com `2` workers
2. subir depois com observacao real

### 7. Risco de SSH mal endurecido

Se desligarmos senha ou `root` cedo demais:

1. podemos nos trancar para fora da propria VPS

Decisao:

1. validar chave SSH primeiro
2. so depois endurecer `PasswordAuthentication` e `PermitRootLogin`
3. considerar `fail2ban` como camada adicional

## D - Direcao

### Regra principal

Publicar com o menor passo de maior ROI, mas sem deixar lacunas de seguranca e recuperacao.

### Defaults travados

1. host canonico: `octoboxfit.com.br`
2. login e app: `app.octoboxfit.com.br`
3. sem `www` como host principal
4. Hostinger VPS em Sao Paulo
5. Ubuntu LTS
6. Cloudflare na frente
7. SSL/TLS do Cloudflare em `Full (strict)`
8. certificado valido na origem
9. `Nginx -> Gunicorn -> Django`
10. `PostgreSQL` local
11. `Redis` local
12. `systemd` para processos
13. sem Docker no v1
14. sem SQLite em producao
15. `Gunicorn` inicial com `2` workers
16. backup com copia externa
17. restore em banco isolado

### O que NAO fazer

1. nao usar `octoboxfit.app` como se fosse o host real da operacao atual
2. nao usar `www.octoboxfit.com.br` nem `www.app.octoboxfit.com.br` como host principal
3. nao deixar `PostgreSQL` publico
4. nao deixar `Redis` publico
5. nao usar `runserver`
6. nao depender de backup local unico
7. nao abrir go-live sem runbook de update e rollback

### O que precisa ser tratado como item de primeira classe

1. `TLS` na origem
2. `Cloudflare Full (strict)`
3. `SSH hardening`
4. bind local de `PostgreSQL` e `Redis`
5. backup com copia externa
6. restore ensaiado
7. update e rollback
8. `/api/v1/health/`

## A - Acoes

### Onda 1 - Fechar a infraestrutura minima correta

1. comprar a VPS em Sao Paulo
2. apontar `octoboxfit.com.br` e `app.octoboxfit.com.br` para o IP da VPS no Cloudflare
3. configurar Cloudflare com proxy ativo e `Full (strict)`
4. instalar certificado valido na origem
5. subir Nginx com `443` e redirect de `80`

### Onda 2 - Endurecer a maquina antes do app

1. criar usuario administrativo proprio
2. validar chave SSH
3. endurecer `sshd_config` so depois da chave validada
4. ativar firewall
5. instalar `fail2ban` se a operacao quiser uma camada extra desde o dia 1

### Onda 3 - Fechar runtime, banco e cache

1. criar usuario `octobox`
2. criar estrutura em `/srv/octobox`
3. clonar o projeto
4. criar `venv`
5. instalar dependencias
6. criar banco e usuario dedicados
7. configurar `Redis` local
8. validar bind local:
   - `ss -ltnp | grep 5432`
   - `ss -ltnp | grep 6379`

Estado esperado:

1. `127.0.0.1:5432`
2. `127.0.0.1:6379`

### Onda 4 - Fechar contrato do Django

Criar `octobox.env` com:

1. `DJANGO_ENV=production`
2. `DJANGO_DEBUG=False`
3. `DJANGO_ALLOWED_HOSTS=octoboxfit.com.br,www.octoboxfit.com.br,app.octoboxfit.com.br`
4. `DATABASE_URL` apontando para `127.0.0.1`
5. `REDIS_URL` apontando para `127.0.0.1`
6. `BOX_RUNTIME_SLUG=box-piloto-octoboxfit`
7. `DJANGO_ADMIN_URL_PATH` longo e nao obvio

### Onda 5 - Bootstrap, publicacao e smoke

1. `migrate`
2. `collectstatic`
3. `bootstrap_roles`
4. `createsuperuser`
5. `manage.py check`
6. subir Gunicorn via `systemd`
7. subir Nginx
8. validar health e rotas centrais

### Onda 6 - Backup, restore, update e rollback

#### Backup

1. usar o script Linux do projeto
2. preferir `.pgpass` ou segredo local seguro em vez de senha inline em cron
3. se usar agendamento simples, usar `root` ou conta com permissao real de escrita nos destinos
4. melhor rota do v1: `systemd timer` ou `cron` com permissao formal e log proprio
5. manter copia fora da VPS

#### Restore

1. criar banco isolado `octobox_restore_test`
2. restaurar dump nele
3. validar conexao e tabelas principais
4. registrar evidencias

#### Update

Ritual canonico:

1. `git pull`
2. `pip install -r requirements.txt`
3. `migrate`
4. `collectstatic`
5. `restart octobox-gunicorn`
6. rodar smoke curto

#### Rollback

Ritual canonico:

1. voltar para o commit anterior conhecido
2. reinstalar dependencias se necessario
3. reexecutar `collectstatic`
4. reiniciar Gunicorn
5. validar `health`
6. se o problema for de dados, acionar restore conforme runbook

---

## Prompt operacional reutilizavel

```text
Voce vai atuar como arquiteto de deploy, seguranca e operacao do OctoBOX para o primeiro cliente em Hostinger VPS.

Missao principal:
publicar o aplicativo com `octoboxfit.com.br` como host canonico e `app.octoboxfit.com.br` como superficie principal de login e app, usando Hostinger VPS em Sao Paulo, Ubuntu LTS, Cloudflare na frente, Nginx, Gunicorn, Django, PostgreSQL local e Redis local, sem Docker no v1.

Contexto obrigatorio:
- host canonico publico: `octoboxfit.com.br`
- superficie principal de login e app: `app.octoboxfit.com.br`
- `www.octoboxfit.com.br` e `www.app.octoboxfit.com.br` nao sao hosts principais
- Cloudflare deve operar em `Full (strict)`
- a origem precisa de certificado valido
- PostgreSQL e Redis devem ouvir apenas localmente
- o deploy deve usar `systemd`
- o backup precisa ter copia externa
- o restore precisa ser ensaiado em banco isolado
- o processo inicial do Gunicorn deve subir com 2 workers

Objetivo:
entregar um deploy de primeiro cliente que seja legivel, repetivel, recuperavel e seguro o suficiente para producao inicial.

Failure checks obrigatorios:
- se o Nginx nao estiver em `443`, o deploy nao esta pronto
- se `Cloudflare Full (strict)` nao estiver fechado, o deploy nao esta pronto
- se `PostgreSQL` ou `Redis` estiverem publicos, o deploy nao esta pronto
- se nao houver backup com copia externa, o deploy nao esta pronto
- se nao houver restore ensaiado, o deploy nao esta pronto
- se nao houver ritual de update e rollback, o deploy nao esta pronto
- se `octoboxfit.app` estiver sendo tratado como host canonico da operacao atual, o plano esta errado

Formato esperado da resposta:
1. diagnostico rapido
2. passos operacionais em ordem
3. comandos concretos
4. checks de validacao
5. riscos restantes

Qualidade minima:
- um objetivo principal
- sem deixar decisoes importantes em aberto
- sem misturar institucional e app
- sem pular seguranca da origem
- sem inventar infraestrutura desnecessaria para o v1
```

---

## Gate final de pronto

Nao abrir o primeiro cliente enquanto qualquer item abaixo estiver falso:

1. `octoboxfit.com.br` responde em HTTPS
2. `app.octoboxfit.com.br` responde em HTTPS
3. origem com certificado valido
4. Cloudflare em `Full (strict)`
5. `DJANGO_ALLOWED_HOSTS` contempla `octoboxfit.com.br` e `app.octoboxfit.com.br`
6. `/api/v1/health/` responde
7. login funciona
8. dashboard, alunos, operacao e grade respondem sem `500`
9. `PostgreSQL` e `Redis` escutam apenas localmente
10. backup diario existe e tem copia externa
11. restore foi ensaiado
12. existe roteiro de update
13. existe roteiro de rollback
14. reboot da VPS nao derruba a aplicacao permanentemente
