<!--
ARQUIVO: registro unico de ativacao de ambiente (mergeado != ativado).

TIPO DE DOCUMENTO:
- fonte de verdade operacional (registro + checklist)

AUTORIDADE:
- alta para "o que precisa ser configurado/rodado por ambiente apos o deploy"

DOCUMENTO PAI:
- [README.md](README.md)
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)

QUANDO USAR:
- no go-live de um ambiente (homolog/producao)
- a cada deploy que traga uma feature nova com env var ou comando de ativacao
- quando algo "esta no main mas nao funciona" em um ambiente

POR QUE ELE EXISTE:
- codigo mergeado nao vale nada ate o ambiente ser configurado. Esse gap se
  acumula em silencio: cada feature nova traz 1-2 passos manuais (env var,
  management command) que ninguem lembra na hora H.
- centraliza, em UM lugar, o mapa "feature -> env vars + comandos + verificacao".

O QUE ESTE ARQUIVO FAZ:
1. lista as env vars obrigatorias em producao (o .env.example tem a lista completa).
2. lista os comandos de ativacao idempotentes, quando rodar e como verificar.
3. quebra por capability: o que cada feature exige para sair de "mergeada" para "ativa".

PONTOS CRITICOS:
- este doc liga feature -> ativacao; o .env.example continua sendo a lista
  canonica de TODAS as variaveis. Nao duplicar valores de exemplo aqui.
- toda PR que adiciona env var OU comando de ativacao registra aqui (ver
  "Regra de manutencao"). Senao o gap volta.
- ATIVO.
-->

# Registro de ativação de ambiente — "mergeado ≠ ativado"

Fonte de verdade única para tudo que precisa ser **configurado ou executado por ambiente** depois que o código já está no `main`. Sem isso, a feature está no repositório mas **inerte** no ambiente.

A [first-box-production-execution-checklist.md](first-box-production-execution-checklist.md) (Etapa 1) aponta para cá; este registro é o detalhe app-level que aquele runbook assume pronto.

## Como usar

1. No go-live de um ambiente: rode a seção **Comandos de ativação** de cima a baixo.
2. A cada deploy com feature nova: confira se a feature aparece em **Ativação por capability**; se sim, aplique os passos dela.
3. Se algo "está no main mas não funciona": procure a capability aqui antes de debugar código.

---

## 1. Env vars obrigatórias em produção

> Lista **canônica e completa** em [`.env.example`](../../.env.example). Aqui só o subconjunto que **bloqueia** go-live e o que é **segredo** (nunca no repo).

| Variável | Para quê | Segredo? |
|---|---|---|
| `DJANGO_ENV=production` | Liga modo produção | não |
| `DJANGO_SECRET_KEY` | Assinatura de sessão/CSRF/magic-token | **sim** |
| `PHONE_BLIND_INDEX_KEY` | Blind index de PII (chave separada da secret) | **sim** |
| `DATABASE_URL` | PostgreSQL real (django-tenants exige Postgres) | **sim** |
| `REDIS_URL` | Cache/rate-limit em prod (vazio derruba o boot em prod) | **sim** |
| `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` | Hosts e origens do `app.` | não |
| `BOX_RUNTIME_SLUG` / `CACHE_KEY_PREFIX` | Fronteira de runtime/cache da célula | não |
| `DJANGO_ADMIN_URL_PATH` | Caminho não-óbvio do admin | **sim (por obscuridade)** |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Funil Early Adopter (ver §3) | **sim** |
| `STRIPE_PRICE_EARLY_MONTHLY` / `STRIPE_PRICE_EARLY_ANNUAL` | Price IDs do checkout | não |
| `SUPERDEV_PASSWORD` (env do comando) | Senha da conta de suporte (ver §3) | **sim** |

Regra: **segredo nunca no repositório** — vem do ambiente real / cofre.

---

## 2. Comandos de ativação (idempotentes)

Rodar no ambiente alvo, na ordem. Todos são idempotentes (seguro repetir).

| # | Comando | Quando | Verificação |
|---|---|---|---|
| 1 | `migrate_schemas --shared` | todo deploy com migration shared | sem migration pendente em `public` |
| 2 | `bootstrap_roles` | 1ª vez por ambiente | grupos Owner/Manager/Coach/Recepcao existem |
| 3 | `createsuperuser` | 1ª vez por ambiente | login no admin |
| 4 | `bootstrap_superdev` (com `SUPERDEV_PASSWORD=...`) | 1ª vez por ambiente | conta `superdev` existe e ativa |
| 5 | `attach_superdev_to_boxes [--dry-run]` | após criar/ligar o superdev, e após provisionar boxes em lote | todo box ACTIVE tem Membership do superdev |
| 6 | `provision_box` / `reprovision_box` | por cliente (ou via funil Stripe) | `Box.status=ACTIVE`, schema migrado |

> Boxes novos provisionados pelo funil já anexam o superdev automaticamente (`reprovision_box`). O comando 5 é para **backfill** de boxes que existiam antes da conta superdev.

---

## 3. Ativação por capability

### Acesso de suporte (superdev)
- **Vars:** `SUPERDEV_USERNAME` (default `superdev`), `SUPERDEV_EMAIL`, `SUPERDEV_AUTO_ATTACH` (kill-switch), + `SUPERDEV_PASSWORD` no env do comando.
- **Comandos:** `bootstrap_superdev` → `attach_superdev_to_boxes`.
- **Verificar:** `/box/` lista os boxes; superdev entra em um box de cliente sem credencial do cliente.
- **Decisão:** [../adr/ADR-013-superdev-support-access-per-box.md](../adr/ADR-013-superdev-support-access-per-box.md) (feature: PR #131).

### Funil Early Adopter (Stripe → Owner → Box)
- **Vars:** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_EARLY_MONTHLY`, `STRIPE_PRICE_EARLY_ANNUAL`.
- **Fora do código:** registrar o endpoint do webhook `/financeiro/stripe/webhook/` no painel da Stripe e colar o signing secret em `STRIPE_WEBHOOK_SECRET`.
- **Verificar:** checkout em test mode → webhook `checkout.session.completed` → e-mail de ativação → onboarding cria Owner + Box. Sem as vars, a view degrada para "vamos chamar no WhatsApp" (não quebra).

### Papéis & admin
- **Comandos:** `bootstrap_roles`, `createsuperuser`. **Var:** `DJANGO_ADMIN_URL_PATH`.

### Workspace do Manager (piloto)
- **Var:** `OPERATIONS_MANAGER_WORKSPACE_ENABLED=True` quando o papel Manager faz parte do pacote do dia 1.

### Push web do aluno (pagamento confirmado)
- **Vars:** `STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY`, `STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY` (**segredo**), `STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT` (`mailto:suporte@octoboxfit.com.br`, não é segredo).
- **Como gerar:** par de chaves VAPID (`py_vapid`, já é dependência via `pywebpush`). A privada precisa estar em **formato PEM** — `_build_vapid_private_key()` em `student_identity/push_notifications.py` usa `Vapid02.from_pem(...)`, não `Vapid02.from_string(...)` (bug real documentado ali: `from_string`/passar a chave crua tenta decodificar os cabeçalhos `-----BEGIN...-----` como base64url e quebra). A pública precisa estar em base64url do ponto EC não-comprimido (formato `applicationServerKey` do Push API do navegador), não em PEM.
- **Fora do código:** colar as 3 vars no `octobox.env` da VPS e reiniciar `octobox-gunicorn.service` (as vars só são lidas no boot do processo).
- **Verificar:** `is_student_web_push_configured()` deve retornar `True`; sem as vars, `send_student_web_push_notification()` retorna `False` em silêncio (a confirmação de pagamento continua funcionando, só sem o push).
- **Por quê existe:** feature mergeada no PR #175 (payment-confirmed push) sem nenhuma das 3 vars configuradas em produção — `is_student_web_push_configured()` ficava sempre `False`, então `webpush()` nunca chegou a rodar. Sintoma de "está no `main` mas não funciona" que este registro existe para prevenir.

### Backup do PostgreSQL (diário)
- **Vars:** `OCTOBOX_BACKUP_REMOTE` (ex. `r2:octobox`, não é segredo — a credencial do provedor fica só no `rclone.conf` da VPS, nunca em env var), `OCTOBOX_BACKUP_REMOTE_PREFIX`, `OCTOBOX_BACKUP_RETENTION_DAYS`.
- **Fora do código:** `rclone config create r2 s3 provider Cloudflare access_key_id ... secret_access_key ...` na VPS (ou `setup_r2_backup.sh`, que faz isso). A credencial do R2 nasce no painel Cloudflare, nunca no repo.
- **Comandos:** `systemctl enable --now octobox-backup.timer` (diário, 03:15).
- **Verificar:** `systemctl list-timers octobox-backup.timer`; `deploy-state/last_backup_remote_path` aponta pro remote configurado.
- **Por quê existe:** este registro nunca tinha sido escrito, apesar do timer/service já existirem em `infra/hostgator-vps/systemd/` desde a criação da VPS — mesmo gap de "mergeado ≠ ativado" do resto deste arquivo. Achado em 2026-08 durante uma auditoria: os units nunca tinham sido copiados pra `/etc/systemd/system/`, então nenhum backup automático rodava desde o setup inicial (só 2 dumps manuais, de 19 dias antes da auditoria).

### Backup cifrado do `octobox.env`
- **Vars:** `OCTOBOX_ENV_BACKUP_AGE_RECIPIENT` (chave pública age, não é segredo), `OCTOBOX_ENV_BACKUP_RETENTION_DAYS`.
- **Comandos:** `setup_env_secrets_backup.sh` (1ª vez — a chave privada nasce FORA da VPS, via `age-keygen` local) → timer `octobox-env-backup.timer` (a cada 10 dias — cadência menor que o Postgres porque o env muda com pouca frequência).
- **Verificar:** `systemctl status octobox-env-backup.timer`; `deploy-state/last_env_backup_remote_path` aponta pro R2.
- **Por quê existe:** incidente de 2026-08 — VPS falhou antes de qualquer backup do `octobox.env` sobreviver, perdendo `DJANGO_SECRET_KEY` (também usada para cifrar PII, ver `shared_support/crypto_fields.py`) e todos os segredos de terceiros de uma vez. Ver [hostgator/backup-env-secrets.md](hostgator/backup-env-secrets.md).

### Segundo destino de backup (redundância de provedor)
- **Var:** `OCTOBOX_BACKUP_REMOTE_SECONDARY` — opcional; quando definida, os dois scripts de backup (Postgres e env) sincronizam pra esse remote também, além do `OCTOBOX_BACKUP_REMOTE` primário.
- **Fora do código:** `rclone authorize "drive" --drive-scope drive.file` rodado **na máquina do operador** (nunca na VPS — o OAuth exige navegador), gera um token que é aplicado via `rclone config create gdrive drive scope drive.file token '<json>'` na VPS.
- **Por quê existe:** não depender de um único provedor de nuvem — se a conta R2 tiver problema, o Google Drive é uma cópia independente dos mesmos backups.

---

## Regra de manutenção

1. **Toda PR** que adiciona uma env var **ou** um comando de ativação: registra aqui (tabela §1/§2 ou nova subseção §3) **e** no `.env.example`.
2. Comandos de ativação devem nascer **idempotentes** — este registro assume que repetir é seguro.
3. Se uma capability for desativada/removida, marcar a subseção como `REMOVIDO em <data>` em vez de apagar (preserva contexto de migração).
4. Manter o link da Etapa 1 do `first-box-production-execution-checklist.md` apontando para cá.

## Referências

- [`.env.example`](../../.env.example) — lista canônica de variáveis.
- [first-box-production-execution-checklist.md](first-box-production-execution-checklist.md) — runbook ordenado de go-live.
- [../adr/ADR-013-superdev-support-access-per-box.md](../adr/ADR-013-superdev-support-access-per-box.md) — superdev.
- `control/management/commands/` — `bootstrap_superdev`, `attach_superdev_to_boxes`, `provision_box`, `reprovision_box`.
