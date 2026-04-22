---
description: Ghost Audit - Protocolo de Excelência Técnica e Performance OctoBox
---

# 👻 Ghost Audit: Protocolo de Excelência 175 QI

Este workflow é invocado quando o OctoBox precisa de um diagnóstico profundo de "saúde técnica". Ele foca em encontrar **puxadinhos** (dívida técnica visual) e **gargalos fantasma** (N+1 queries ou buscas lentas).

## Quando usar:
- Antes de qualquer deploy para produção.
- Após grandes refatorações de UI ou Backend.
- Sempre que o sistema parecer "pesado" ou "fragmentado".

## Passo 1: Varredura de Estilos Hardcoded (CSS Sweep)
O agente deve executar uma busca por estilos inline que ignoram o Design System:
```powershell
grep -r "style=" ./templates --exclude-dir=node_modules
```
**Critério de Limpeza:** Todo `style=` que defina `margin`, `padding`, `color`, `font-size` ou `display` deve ser migrado para `tokens.css`. Estilos dinâmicos (ex: width de barra de progresso) são permitidos.

## Passo 2: Detecção de Gargalos Fantasma (Backend)
O agente deve auditar os arquivos de query:
1. Buscar loops (`for`) que contenham chamadas a `.count()`, `.exists()` ou acessos a chaves estrangeiras sem `select_related`/`prefetch_related`.
2. Verificar se agregações complexas no Dashboard estão utilizando cache ou se podem ser unificadas em um único `aggregate`.

## Passo 3: Verificação de "Silêncio que Acolhe" (UI/UX)
1. Validar se novos componentes estão usando os tokens de vidro (`glass-card`, `glass-panel`).
2. Checar se existem IDs repetidos ou falta de `aria-labels` em elementos interativos.

## Passo 4: Relatório do Fantasma
Ao final da auditoria, o agente deve gerar um sumário no chat:
- 🟢 **Limpo:** Nada encontrado. OctoBox em Performance Elite.
- 🟡 **Alerta:** Pequenos detalhes encontrados (pode aguardar).
- 🔴 **Crítico:** Dívida técnica grave ou N+1 detectado em área quente.

---
// turbo-all
