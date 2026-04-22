# Technical Concerns & Debt - OctoBOX

Este documento registra áreas de risco, dívidas técnicas e pontos de atenção crítica que devem ser considerados em qualquer nova implementação.

## 1. Dívida Evolutiva: Ownership de Modelos

*   **Problema:** Os modelos de `students`, `finance` e `communications` ainda usam `app_label = 'boxcore'`.
*   **Risco:** Isso centraliza todas as migrations em um único app, dificultando a modularização completa no futuro.
*   **Ação:** Qualquer mudança em modelos deve ser refletida na pasta `boxcore/migrations/`, e não na pasta de migrations do app de origem.

## 2. Integridade de Dados: Dual-Write (Blind Index)

*   **Problema:** O `phone_lookup_index` depende do método `.save()` para ser gerado.
*   **Risco:** O uso de `.update()`, `.bulk_update()` ou migrations de dados que não chamam `.save()` deixará o índice defasado, quebrando a busca e a unicidade lógica.
*   **Ação:** Sempre usar `services` que garantam a sincronização ou atualizar o índice manualmente em operações em lote.

## 3. Divergência de Shadow State (Redis)

*   **Problema:** O Dashboard lê do Redis, mas a verdade está no DB.
*   **Risco:** Se um processo de atualização do snapshot falhar (ex: queda do Redis no momento do save), o Dashboard mostrará dados obsoletos ou incorretos (ex: aluno ativo que já cancelou).
*   **Ação:** Implementar um "reconciliation job" periódico para re-sincronizar snapshots críticos.

## 4. Segurança de PII e Chaves de Criptografia

*   **Problema:** O sistema depende fortemente de `PHONE_BLIND_INDEX_KEY`.
*   **Risco:** A perda dessa chave torna todos os telefones e índices de busca inúteis. A troca da chave exige um re-hash de toda a base de dados.
*   **Ação:** Armazenar segredos em Vaults de produção e manter documentado o procedimento de "Key Rotation".

## 5. Performance de Consultas Financeiras

*   **Problema:** Relatórios financeiros complexos exigem muitos JOINS (`Student` -> `Enrollment` -> `Payment`).
*   **Risco:** Lentidão conforme a base cresce (Escalabilidade).
*   **Ação:** Mover agregados financeiros para campos desnormalizados no `Student` ou snapshots dedicados no Redis.

## 6. Saneamento e Duplicatas

*   **Problema:** Condições de corrida em Webhooks podem gerar registros duplicados antes da constraint de banco atuar.
*   **Risco:** Poluição da base e confusão no atendimento.
*   **Ação:** Manter a auditoria `audit_blind_index` como parte do health check do sistema.
