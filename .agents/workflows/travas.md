---
description: Protocolo Renanfulas - Governança de Código e Travas de Segurança L7
---

# Protocolo Renanfulas: Regras de Engajamento 🔐🛡️

Este workflow define as permissões do agente de IA para modificar o código do OctoBox. O agente deve consultar o nível atual em `.agents/trava_state.json` antes de qualquer edição.

## Níveis de Travas

### 🟢 Nível 1: VERDE (Padrão)
**Objetivo:** Ajustes visuais, textos e documentação. Zero impacto estrutural.
- **Permitido:** 
  - `templates/*.html` (Apenas visual, sem lógica complexa)
  - `static/css/*.css`
  - `docs/*.md`
  - `tests/*.py`
- **Bloqueado:** Tudo o que não for explicitamente permitido.

### 🟡 Nível 2: ÂMBAR (Desbloqueio Tático)
**Objetivo:** Alteração de lógica de negócio e fluxos de dados.
- **Permitido:**
  - Tudo do Nível 1
  - `views.py`, `urls.py`, `forms.py`
  - `services.py`, `queries.py`
  - `serializers.py`
- **Bloqueado:** Models, Migrations, Settings e Core Security.

### 🔴 Nível 3: VERMELHA (Bypass Total - Renanfulas)
**Objetivo:** Alteração estrutural profunda e acesso ao núcleo do sistema.
- **Permitido:** ACESSO TOTAL ao repositório.
- **Protocolo de Ativação:**
  1. O Renanfulas deve autorizar explicitamente o bypass.
  2. O script `.agents/scripts/trava_ops.py backup` cria um snapshot Git automático.
  3. O `red_beacon.py` monitora a saúde das rotas após cada `replace_file_content`.
  4. Ativação do **Vertical Skybeam**: Se 3+ rotas quebrarem, as mudanças são revertidas (`git stash pop`) e o nível volta para 1.

## Como mudar o nível

Para elevar o nível, o agente deve rodar:
`python .agents/scripts/trava_ops.py unlock <nivel>`

Para voltar ao nível seguro:
`python .agents/scripts/trava_ops.py lock`
