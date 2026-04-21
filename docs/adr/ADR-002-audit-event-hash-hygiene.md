# ADR-002 — Hash de tokens e IPs em AuditEvent

**Status:** Aceito  
**Data:** 2026-04-21  
**Contexto:** Student OAuth onboarding polish

## Decisão

Todo `AuditEvent` relacionado ao corredor do aluno deve usar:
- `target_label` = `hashlib.sha256(token.encode()).hexdigest()[:16]`
- `metadata['token_hash']` (nunca `'token'` com valor cru)
- `metadata['ip_hash']` = `hashlib.sha256(ip.encode()).hexdigest()[:8]` (nunca `'client_ip'`)

## Por quê

Um log que grava o token cru vira oráculo de enumeração: qualquer pessoa com acesso ao log pode usar tokens válidos ou testar a validade de tokens suspeitos. O hash SHA-256 truncado preserva rastreabilidade (correlação de eventos do mesmo token) sem expor o valor.

## Consequências

- Correlação de eventos do mesmo token é possível comparando hashes
- Recuperação do token original a partir do log é computacionalmente inviável
- Logs de acesso ao sistema de auditoria não precisam de controles especiais para tokens
