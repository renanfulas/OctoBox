# Registro de ensaio F2 — restore seletivo de tenant

Use uma cópia fora do repositório, em pasta de evidências com acesso controlado. Não comite
valores preenchidos, dumps, manifests, PII, credenciais, chaves ou payloads de provedores.
Este formulário acompanha o [runbook F2](../rollout/restore-and-rollback-drill.md) e o
[inventário de dependências](tenant-restore-inventory-2026-10-23.md); não autoriza promoção em
produção.

## Identificação e escopo

| Campo | Registro |
|---|---|
| ID da rodada | |
| Data e fuso | |
| Responsável técnico | |
| Responsável pela evidência | |
| Host/ambiente homologação | |
| Release/SHA em execução | |
| PostgreSQL server/client versions | |
| Banco de origem (nome não secreto) | |
| Box A / schema | |
| Box B / schema | |
| Início / fim da janela | |
| Contato de operação/provedores | |

## Gate de entrada

| Verificação | Resultado/evidência |
|---|---|
| Ambiente isolado; acesso de escrita limitado ao operador | |
| Uma ou mais réplicas/hosts de app identificados | |
| PostgreSQL, role de backup/restore e destino novo disponíveis | |
| `pg_dump`, `pg_restore`, `psql` e scripts versionados disponíveis | |
| A e B são caixas descartáveis; nenhum tenant real é canário | |
| Migrations e gate semântico instalados no ambiente | |
| Operador pode pausar ingress, schedulers e webhooks | |
| Procedimento de abortar e retomar serviços foi combinado | |

Se qualquer pré-condição falhar, **não iniciar** e registrar o bloqueador.

## Baseline de A e B

Registre contagens e fingerprints sanitizados. Não inclua nome, email, telefone, ciphertext,
IDs de pessoas, conteúdo de WOD ou query SQL com dados de negócio.

| Evidência antes do freeze | A | B |
|---|---:|---:|
| Schema e status do Box | | |
| Quantidade de tabelas | | |
| Fingerprint semântico | | |
| Contagens de Student / ClassSession / Workout | | |
| FKs externas e não validadas | | |
| Migrations por app | | |
| Domain/Membership/identidades vinculadas | | |
| Filas/retries/outboxes pendentes por classe | | |

## Prova do fence e isolamento de tráfego

| Verificação | Resultado/evidência |
|---|---|
| `write_frozen_at` de A confirmado em `public.control_box` | |
| Escrita canário em A recebeu 503 e `Retry-After` | |
| Escrita canário sem efeito externo em B foi persistida | |
| Ingress restrito ao operador durante os canários | |
| Callbacks de provedores pausados/isolados; procedimento de retry/replay confirmado | |
| IDs opacos/quantidade de eventos aceitos antes da pausa conciliados em registro protegido | |
| Todos os hosts/replicas OctoBox atrás de proxy/LB identificados | |
| Timers/serviços originalmente active/enabled registrados por host | |
| Timers/serviços writers parados; one-shots/leases drenados | |
| Nginx ingress interrompido ou vhosts OctoBox cortados no balanceador | |
| `octobox-gunicorn.service` encerrado sem timeout/kill em todas as réplicas | |
| Processos Gunicorn OctoBox restantes | |
| Sessões PostgreSQL restantes da role da aplicação antes dos dumps | |

### Estado das unidades por host

Registre o estado anterior à janela e a ação efetiva. Inclua qualquer réplica ou unidade fora desta
lista que tenha sido identificada no ambiente. `active/enabled` são estados independentes; deixe
explícito se uma unidade estava ausente.

| Host | Unit/processo | Tipo | Estado `active` antes | Estado `enabled` antes | Ação/parada e drenagem | Retomada conforme estado anterior | Evidência protegida |
|---|---|---|---|---|---|---|---|
| | `nginx.service` ou corte por vhost/LB | ingress | | | | | |
| | `octobox-gunicorn.service` | web | | | | | |
| | `octobox-public-workout-rest-alerts.service` | worker contínuo | | | | | |
| | `octobox-nightly-lead-imports.timer` | timer | | | | | |
| | `octobox-payment-notifications.timer` | timer | | | | | |
| | `octobox-signal-mesh-retries.timer` | timer | | | | | |
| | `octobox-public-workout-metrics.timer` | timer | | | | | |
| | `octobox-public-workout-notices.timer` | timer | | | | | |
| | `octobox-public-workout-operations.timer` | timer | | | | | |
| | `octobox-public-workout-outbox.timer` | timer | | | | | |
| | `octobox-backup.timer` | timer | | | | | |
| | Outra unidade identificada | | | | | | |

Não preencha estados por suposição a partir dos arquivos versionados: confirme no host. O estado
`enabled` não determina se deve iniciar após o drill; a retomada segue o estado `active` anterior e
o procedimento de reconciliação aprovado.

Condição para capturar: **zero processos web OctoBox ativos e zero sessão da role de aplicação**.
Se o emissor não confirmar retry/replay dos callbacks interrompidos, manter a rodada reprovada.

## Backups pareados e restore isolado

| Campo | Dump full | Dump tenant A |
|---|---|---|
| Caminho protegido do archive | | |
| Caminho do manifest | | |
| SHA-256 validado | | |
| Database/schema de origem | | |
| PostgreSQL major/client | | |
| Início/fim da captura | | |
| Tamanho | | |

| Verificação do restore | Resultado/evidência |
|---|---|
| Nome novo `octobox_restore_<run-id>` | |
| Destino inexistente antes da criação | |
| Manifestos/hashes/origem/major aprovados | |
| Restore full e substituição isolada de A concluídos | |
| Tabelas restauradas / FK não validadas | |
| `migrate_schemas --schema=box_<slug_A> --check --noinput` | |
| `smoke_test_tenant --schema-only --restore-semantic` em A | |
| Mesmo smoke semântico em B | |
| Referências Box/Domain/Membership/StudentIdentity verificadas | |
| Fingerprint de B no clone igual ao baseline full | |
| Fingerprint/contagens de A coerentes com o dump tenant | |

## Retomada e reconciliação

| Verificação | Resultado/evidência |
|---|---|
| Hashes/manifests conferidos antes de reabrir ingress | |
| Gunicorn/Nginx reabertos conforme estado anterior | |
| A permaneceu congelado durante o restore/comparação | |
| B aceitou canário na origem após a captura, sem alterar a cópia isolada | |
| Callbacks retry/replay confirmados pelo emissor | |
| Webhook event IDs/fila legacy/outbox conciliados | |
| Mensagens aceitas por provedor e estados `unknown` reconciliados | |
| Timers/serviços retornaram somente se originalmente ativos | |
| Smoke/health após retomada | |
| A descongelado somente após reconciliação | |
| Fingerprint/contagens finais da origem registrados | |

## RTO, RPO e decisão

| Métrica | Início | Fim | Duração/valor | Observação |
|---|---|---|---|---|
| RTO de detecção até app/tenant validado | | | | |
| RTO do início da recuperação até smoke aprovado | | | | |
| RPO: último dado recuperado versus corte/incidente simulado | | | | |
| Indisponibilidade do ingress homologação | | | | |

**Resultado:** `APROVADO` / `REPROVADO` / `ABORTADO`

**Bloqueadores, desvios e falhas:**

**Pendências de reconciliação:**

**Operadores que confirmaram a retomada:**

**Evidências protegidas (paths/IDs opacos, sem conteúdo sensível):**

**Este resultado comprova apenas a rodada e o ambiente registrados. Não libera promoção em
produção nem substitui required checks, QA físico, políticas de retenção ou aceite operacional.**
