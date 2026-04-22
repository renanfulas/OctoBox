# Architecture Overview - OctoBOX

O OctoBOX utiliza um padrão de **Monolito Modular** com uma separação clara de domínios em nível de pasta, mantendo uma estrutura de banco de dados unificada por motivos históricos.

## Camada de Dados (Historical Boxcore)

Uma característica única deste projeto é o uso do `app_label = 'boxcore'` em modelos definidos em outros apps (`students`, `finance`, `communications`).

*   **Por que existe:** Permite que o código seja organizado em domínios lógicos (`students/models.py`, `finance/models.py`) sem quebrar as migrações do banco de dados que foram iniciadas no app `boxcore`.
*   **Implicação:** Todas as migrações de dados desses modelos residem em `boxcore/migrations/`.

## Domínios Funcionais

| App | Responsabilidade |
| :--- | :--- |
| **Students** | Ponto central da identidade do aluno. Gere dados pessoais e saúde. |
| **Finance** | Coração financeiro. Gere `Enrollment` (Matrícula) e `Payment`. Integração Stripe. |
| **Communications** | Gestão de contatos de WhatsApp e logs de mensagens enviados/recebidos. |
| **Integrations** | Camada de tradução para serviços externos (Stripe, WhatsApp Cloud API). |
| **Access** | Controle de acesso baseado em funções (RBAC), login e navegação. |
| **Boxcore** | App "âncora" para o schema do banco de dados e migrações globais. |
| **Shared Support** | Utilitários transversais: Criptografia, Snapshots Redis e Mixins. |

## Shadow State & Performance

O sistema implementa uma arquitetura de **Shadow State** para otimizar a leitura no Dashboard/Cockpit Financeiro.

1.  **Database (SSOT):** O PostgreSQL/SQLite é a Fonte Única da Verdade.
2.  **Redis Snapshots:** Dados agregados de alunos (status financeiro, matrículas ativas) são cacheados em formato JSON no Redis.
3.  **Sincronização:** Gatilhos nos modelos (signals ou métodos `save`) invalidam ou atualizam esses snapshots após mudanças no banco.

## Fluxo de Identidade (Blind Index)

Para garantir busca rápida sem expor dados criptografados (PII), utilizamos:
1.  `phone`: Campo criptografado (ilegível no DB).
2.  `phone_lookup_index`: Hash determinístico (v1:<hash>) do telefone normalizado.
3.  **Unicidade:** Garantida via `UniqueConstraint` no nível do banco de dados sobre o índice.
