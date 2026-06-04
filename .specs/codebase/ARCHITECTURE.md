# Architecture Overview - OctoBOX

O OctoBOX utiliza um padrao de monolito modular com separacao clara de dominios em nivel de pasta, mantendo uma estrutura de banco de dados historicamente unificada.

## Camada de Dados (Historical Boxcore)

Uma caracteristica importante deste projeto e o uso de `app_label = 'boxcore'` em modelos definidos em outros apps (`students`, `finance`, `communications`).

- **Por que existe:** permite que o codigo seja organizado em dominios logicos sem quebrar as migracoes iniciadas no app `boxcore`.
- **Implicacao:** varias migracoes de dados desses modelos ainda residem em `boxcore/migrations/`.

## Banco Padrao

PostgreSQL e a fonte unica da verdade em desenvolvimento, testes, homologacao e producao.

O motivo tecnico e simples: `django-tenants` depende de schemas PostgreSQL. SQLite nao representa esse contrato e so pode ser usado como escape legado de diagnostico via `OCTOBOX_ALLOW_SQLITE_FALLBACK=1`.

## Dominios Funcionais

| App | Responsabilidade |
| :--- | :--- |
| **Students** | Ponto central da identidade do aluno, dados pessoais e saude |
| **Finance** | Matricula, pagamentos e integracao Stripe |
| **Communications** | Contatos de WhatsApp e logs de mensagens |
| **Integrations** | Traducao para servicos externos |
| **Access** | RBAC, login e navegacao |
| **Boxcore** | App ancora para schema historico e migrations |
| **Shared Support** | Utilitarios transversais, criptografia, snapshots Redis e mixins |

## Shadow State & Performance

O sistema implementa uma arquitetura de shadow state para otimizar leituras no dashboard e nas superficies operacionais.

1. **PostgreSQL (SSOT):** fonte unica da verdade transacional.
2. **Redis snapshots:** dados agregados ficam cacheados em JSON.
3. **Sincronizacao:** signals, services ou invalidacoes limpam/atualizam snapshots apos mudancas no banco.

## Fluxo de Identidade (Blind Index)

Para garantir busca rapida sem expor dados criptografados:

1. `phone`: campo criptografado.
2. `phone_lookup_index`: hash deterministico do telefone normalizado.
3. **Unicidade:** garantida por constraint no banco sobre o indice.
