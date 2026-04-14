<!--
ARQUIVO: matriz operacional viva da Fase 1 do beta fechado.

TIPO DE DOCUMENTO:
- matriz de acompanhamento

AUTORIDADE:
- alta para fechamento da Fase 1

DOCUMENTOS IRMAOS:
- [first-box-production-execution-checklist.md](first-box-production-execution-checklist.md)
- [restore-and-rollback-drill.md](restore-and-rollback-drill.md)
- [../plans/phase1-closed-beta-20-boxes-corda.md](../plans/phase1-closed-beta-20-boxes-corda.md)

QUANDO USAR:
- para acompanhar a execucao da Fase 1
- antes do primeiro box
- durante os primeiros 7 a 14 dias do piloto

POR QUE ELE EXISTE:
- transforma a Fase 1 em status verificavel, nao em sensacao de progresso.
- deixa explicito o que ja esta pronto, o que esta parcial e o que ainda bloqueia o go-live.
- cria um lugar unico para dono, evidencia e proximo passo.

PONTOS CRITICOS:
- esta matriz so vale se cada status vier acompanhado de evidencia real.
- "parcial" sem proximo passo vira debito tecnico silencioso.
-->

# Matriz operacional da Fase 1

## Regra de uso

Para cada item, registrar:

1. `status`
2. `dono`
3. `evidencia`
4. `proximo passo`

Status permitidos:

1. `nao iniciado`
2. `parcial`
3. `validado`
4. `bloqueador`

---

## Quadro mestre

| Item | Status atual | Dono | Evidencia minima | Proximo passo |
| --- | --- | --- | --- | --- |
| Healthcheck de producao | `validado` | Engenharia | `manage.py check` verde e contrato da API v1 validado em `2026-04-13` | Manter no smoke de go-live |
| Runtime boundary do box | `validado` | Engenharia | `runtime_slug` e `runtime_namespace` coerentes no healthcheck e snapshots emitindo versao em `2026-04-13` | Confirmar slug do box piloto real |
| `intent_id` nos fluxos criticos | `validado` | Engenharia | metadata operacional presente nos fluxos de manager e cobranca | Estender com idempotencia forte na proxima onda |
| `snapshot_version` em `manager`, `reception`, `owner` | `validado` | Engenharia | payload e DOM emitindo versao | Medir comportamento em pico real |
| Fallback por versao em `manager` | `validado` | Engenharia | refresh por versao funcionando | Observar durante war room |
| Fallback por versao em `reception` | `validado` | Engenharia | polling leve + SSE coexistindo | Observar durante war room |
| Fallback por versao em `owner` | `validado` | Engenharia | fragmento oficial + polling leve | Observar durante war room |
| Baseline de throttles | `validado` | Engenharia | settings e docs de seguranca alinhados | Revisar so com telemetria real |
| Admin protegido | `parcial` | Engenharia / Ops | `DJANGO_ADMIN_URL_PATH` definido em producao | Confirmar valor real no ambiente alvo |
| HTTPS e trusted origins | `parcial` | Ops | variaveis de ambiente do deploy | Validar host final do go-live |
| Backup do banco | `parcial` | Ops | backup local SQLite gerado em `backups/db-20260413-050155.sqlite3` em `2026-04-13` | Gerar backup PostgreSQL real do ambiente alvo e registrar timestamp |
| Restore testado | `parcial` | Ops / Engenharia | drill local SQLite validado com `integrity=ok`, `table_count=28` e `django_migrations=40` em `2026-04-13` | Rodar o mesmo drill em PostgreSQL na homologacao/producao |
| Rollback ensaiado | `validado` | Ops / Engenharia | rollback drill executado no worktree limpo entre `dc5ef8a` e `9e0e2bb`, com `manage.py check` verde e smoke central `200` nos dois lados | Repetir o ritual na homologacao oficial quando ela existir |
| Checklist de homologacao | `parcial` | Engenharia | doc existente | Rodar inteiro no ambiente alvo e registrar evidencia |
| Setup interno do primeiro box | `parcial` | Operacao / CS | checklist existente | Executar com o box piloto real |
| Smoke funcional do go-live | `parcial` | Engenharia / Operacao | smoke local validado com `localhost`; `owner`, `reception`, `alunos`, `grade` e `health` em `200`; `manager` tambem validado com `OPERATIONS_MANAGER_WORKSPACE_ENABLED=1` | Repetir no ambiente alvo com a flag do manager ligada se o piloto incluir esse papel |
| War room dos primeiros 7 a 14 dias | `parcial` | Operacao / Engenharia | playbook existente | Definir canal, dono e horario de triagem |
| Isolamento de cache por box | `validado` | Engenharia | prefixo com `BOX_RUNTIME_SLUG` | Expandir a mesma clareza para logs e exports |
| Fronteira de logs/exports/storage por box | `parcial` | Engenharia / Ops | intencao arquitetural definida | Formalizar namespace e evidencia operacional |
| Observabilidade por superficie | `parcial` | Engenharia | healthcheck, logs e playbooks | Registrar latencia/erro por superficie no piloto |

---

## Failure checks do go-live

Se qualquer item abaixo estiver falhando, o primeiro box nao entra:

1. `restore` nao foi testado
2. `rollback` nao foi ensaiado
3. `/api/v1/health/` nao responde `status=ok`
4. `runtime_slug` nao representa claramente a celula ou box piloto
5. `manager`, `reception` ou `owner` parecem mortos quando o barramento quente falha
6. smoke funcional do dia D nao foi executado

---

## Gate de liberacao

### Pode abrir

Somente quando:

1. todos os `bloqueadores` virarem `validado`
2. os `parciais` restantes nao afetarem operacao do dia 1

### Pode abrir com ressalvas

Somente quando:

1. nao houver `bloqueador`
2. os `parciais` estiverem explicitamente aceitos e com workaround claro

### Nao pode abrir ainda

Quando:

1. qualquer `bloqueador` permanecer aberto

---

## Formula curta

Esta matriz existe para responder uma pergunta sem maquiagem:

1. o primeiro box pode entrar hoje ou ainda estamos confiando em sorte?
