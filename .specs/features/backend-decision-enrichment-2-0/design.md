## Design

- Financeiro: `entry_surface`, `entry_href`, `entry_data_action`, `entry_reason`, `secondary_surface`
- Dashboard: prioridade principal e superficie secundaria mais explicitas
- Operations: motivo de prioridade e proximo movimento dominante por papel

## Ordem oficial por ROI

1. Financeiro
   - melhor relacao entre impacto e simplicidade
   - snapshot ja possui `priority_context`, mas ainda deixa o presenter completar a primeira entrada
2. Operations
   - ja possui `priority_context` por papel, mas ainda nao sobe um contrato explicito de `entry_surface` e `secondary_surface`
3. Dashboard
   - semantica ja e mais madura; ganho agora e mais refinamento do que destravamento estrutural

## Regra de execucao

- primeira onda: mover handoff de entrada do presenter financeiro para o snapshot
- segunda onda: explicitar entrada e segundo movimento nas leituras operacionais
- terceira onda: reduzir composicao semantica residual dos cards do dashboard
