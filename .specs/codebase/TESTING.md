# Testing & Quality Assurance - OctoBOX

O OctoBOX prioriza Segurança e Performance. Nossa suíte de testes é desenhada para ser rigorosa, especialmente em fluxos financeiros e tratamento de dados sensíveis.

## 1. Suíte de Testes (Pytest)

Utilizamos o `pytest` como motor de testes principal. Os testes estão centralizados na pasta `tests/` e seguem a nomenclatura `test_[funcionalidade].py`.

### Comandos Comuns
*   **Executar todos os testes:** `pytest`
*   **Executar teste específico:** `pytest tests/test_blind_index.py`
*   **Modo Verboso:** `pytest -v`

## 2. Auditoria de Segurança (Static Analysis)

Como parte do nosso compromisso com segurança bancária, utilizamos ferramentas de análise estática integradas ao workflow:

*   **Bandit:** Procura por vulnerabilidade comuns em código Python.
    *   Execução: `bandit -r .`
*   **Safety:** Verifica se as dependências do `requirements.txt` possuem vulnerabilidades conhecidas.
    *   Execução: `safety check`
*   **Pip-audit:** Auditoria profunda de pacotes.
*   **Detect-secrets:** Previne o commit acidental de chaves de API ou segredos.

## 3. Testes de Performance (Performance First)

*   **K6:** Utilizado para testes de carga e estresse em endpoints críticos (Checkout, Webhooks).
*   **Prometheus:** Monitoramento de métricas em tempo real durante os testes de integração.

## 4. Fluxo de Trabalho (Quality Gate)

1.  **Desenvolvimento:** Codificação local seguindo `CONVENTIONS.md`.
2.  **Pre-commit:** Hooks automáticos rodam formatadores (Prettier/Black) e linters antes do commit.
3.  **Local Test:** O desenvolvedor roda `pytest` antes de abrir um PR.
4.  **Security Audit:** Rodar `bandit` e `pip-audit` em mudanças que envolvem novas dependências ou lógica de segurança.

## 5. Áreas de Foco para Testes

*   **Idempotência:** Webhooks do Stripe devem ser testados para garantir que não processem o mesmo pagamento duas vezes.
*   **Concorrência:** Testar race conditions na criação de alunos com o mesmo telefone (Blind Index Integrity).
*   **Snapshots:** Verificar se a alteração no BD reflete corretamente no JSON do Redis.
