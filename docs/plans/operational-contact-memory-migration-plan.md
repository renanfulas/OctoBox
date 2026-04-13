<!--
ARQUIVO: plano de migracao da memoria curta de contato operacional.

POR QUE ELE EXISTE:
- registra a saida planejada do uso de AuditEvent como base de leitura do workspace.
- evita que a v1 server-driven vire dependencia estrutural silenciosa.

O QUE ESTE ARQUIVO FAZ:
1. define o escopo temporario da v1 em AuditEvent.
2. descreve o read model alvo.
3. lista os gatilhos de migracao e o roteiro de dual write.
-->

# Operational Contact Memory Migration Plan

## Objetivo

Usar `AuditEvent` apenas como trilho rapido da v1 para:

1. registrar primeiro toque e follow-up operacional
2. sustentar cooldown curto do manager
3. alimentar o card de `Historico` do workspace

O destino final **nao** e manter essa leitura no `AuditEvent`.
O destino final e promover um read model dedicado, pensado para workspace e ownership operacional.

## Motivo da migracao

`AuditEvent` e excelente como livro-caixa da portaria.
Ele nao e o melhor armario para guardar roupa do dia a dia.

Riscos de manter a leitura operacional nele por tempo demais:

1. semantica frouxa demais para UX operacional
2. queries cada vez mais dependentes de `action` e `metadata`
3. dificuldade de evoluir `stage`, `ownership` e `cooldown`
4. mistura entre trilha forense e memoria de trabalho

## Read model alvo

Nome sugerido:

- `operational_contact_memory`

Campos minimos sugeridos:

1. `actor_id`
2. `actor_role`
3. `subject_type`
4. `subject_id`
5. `subject_label`
6. `student_id`
7. `payment_id`
8. `intake_id`
9. `channel`
10. `action_kind`
11. `stage_before`
12. `stage_after`
13. `ownership_scope`
14. `cooldown_until`
15. `created_at`

## Fases

### Fase A — Agora

Fonte de leitura:

- `AuditEvent`

Uso permitido:

1. card `Historico` do manager
2. cooldown curto de 3 dias
3. transicao de ownership da recepcao para manager

Guardrail:

- nao crescer consultas novas sobre `AuditEvent` fora desse fluxo sem revisar este plano

### Fase B — Dual write

Criar tabela nova e comecar a escrever em duas trilhas:

1. `AuditEvent`
2. `operational_contact_memory`

Objetivo:

- manter rastreabilidade historica
- validar consistencia do modelo novo sem desligar a v1

### Fase C — Switch de leitura

Trocar as queries do workspace para lerem do read model novo:

1. manager history
2. cooldown pessoal
3. ownership compartilhado do primeiro toque

Depois disso:

- `AuditEvent` volta a ser trilha de auditoria e prova operacional
- o workspace deixa de depender dele como motor semantico

## Gatilhos de migracao

Promover a migracao quando pelo menos um destes sinais aparecer:

1. o card de historico precisar de filtros mais ricos
2. o ownership ganhar mais de dois estados
3. outras telas alem de manager e recepcao consumirem a mesma memoria
4. a leitura em `AuditEvent` exigir query pesada ou indexacao especifica

## Regra de ouro

`AuditEvent` pode abrir a estrada.
Ele nao deve virar a cidade inteira.
