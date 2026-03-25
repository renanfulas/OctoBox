# Tickets Priorizados — Correções e Melhorias (resumo)

Prioridade: Alta

- [ ] Otimizar consultas em endpoints de listagem
  - Tipo: backend, DB
  - Descrição: adicionar índices, revisar joins e aplicar paginação server-side para `/api/students`, `/api/operations`.
  - Esforço estimado: 3-5 dias

- [ ] Implementar retry/backoff + painel de entregas para webhooks
  - Tipo: infra/backend
  - Descrição: adicionar backoff exponencial, limitar tentativas e painel que liste retries/failures com razão e trace IDs.
  - Esforço estimado: 4-6 dias

- [ ] Feedback de progresso em import/export
  - Tipo: backend/frontend
  - Descrição: jobs assíncronos devem expor progresso (percentual), linhas com erro e permitir reprocessamento parcial.
  - Esforço estimado: 2-4 dias

- [ ] Bulk actions com partial-commit e relatório
  - Tipo: backend/frontend
  - Descrição: em operações em lote, aplicar onde permitido e gerar relatório detalhado para itens que falharam por permissão ou validação.
  - Esforço estimado: 3-5 dias

Prioridade: Média

- [ ] Snapshot: mostrar ETA e pré-validação de schema antes de restore
  - Tipo: backend/frontend
  - Esforço estimado: 2-3 dias

- [ ] Auditoria near-real-time
  - Tipo: backend
  - Descrição: reduzir delay de gravação/consulta nas tabelas de auditoria.
  - Esforço estimado: 3-5 dias

Prioridade: Baixa

- [ ] Quick-add para notas (modo enxuto)
  - Tipo: frontend
  - Esforço estimado: 1-2 dias

- [ ] Preview dinâmico de templates sem reload
  - Tipo: frontend
  - Esforço estimado: 1-2 dias

Observações adicionais
- Cada ticket deve incluir: critérios de aceitação, plano de rollback, e testes automatizados onde aplicável.
- Recomenda-se rodar testes de carga após otimizações de DB e antes de promover para produção.
