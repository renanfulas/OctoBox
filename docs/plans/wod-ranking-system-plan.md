<!--
ARQUIVO: plano de implementação do sistema de ranking semanal de WOD por categoria.

TIPO DE DOCUMENTO:
- plano ativo (futuro próximo)

AUTORIDADE:
- alta para a frente de engajamento do aluno

DOCUMENTO PAI:
- [friction-resolution-5-waves-plan.md](friction-resolution-5-waves-plan.md)

QUANDO USAR:
- quando for abrir a frente de ranking semanal no app do aluno

POR QUE ELE EXISTE:
- Substitui a aposta de "timeline social" (rejeitada por violar Front Display Wall e identidade do produto)
  por um sistema de ranking semanal que entrega o mesmo gatilho psicológico de vício com custo
  arquitetural drasticamente menor.
- Alinhado à cultura competitiva nativa do CrossFit.

PONTOS CRITICOS:
- Categoria é campo do resultado, não do aluno.
- Captura via auto-report do aluno — não tocar no Coach Wall (Beto tem nota 9.0).
- Não virar Instagram fitness (sem fotos, sem comentários, sem likes).
- Pré-requisito: Ondas 0–2 do plano principal concluídas.
-->

# Sistema de ranking semanal de WOD

## Tese

Um sistema de ranking read-only baseado em snapshot público que entrega engajamento competitivo
ao aluno sem adicionar UGC, moderação ou complexidade de timeline social.

É o mesmo gatilho psicológico de vício que o Tecnofit entrega, com fração do custo e alinhado
à identidade do produto OctoBox.

## Pré-requisito arquitetural

- Ondas 0–2 do [plano de atritos](friction-resolution-5-waves-plan.md) concluídas
- Signal Mesh com baseline implementado (evento `wod_result_recorded` precisa existir)
- Padrão de snapshots públicos consolidado em student_app

## Camadas

| Camada | Responsabilidade |
|--------|------------------|
| Domínio | Nova capacidade `WODResult` com `time_seconds`, `category`, `wod_session_id`, `student_id` |
| Captura | Auto-report do aluno via `/aluno/wod/resultado/` (coach pode ratificar — opcional) |
| Application | Use case `RecordWODResult` valida invariantes (categoria válida, tempo razoável, sessão existe) |
| Snapshot público | `WeeklyBoxRankingSnapshot` por box × semana × categoria, regenerado por evento `wod_result_recorded` |
| Surface | Nova rota `/aluno/ranking/` no shell student_app existente |
| Privacidade | Flag `appear_in_ranking` no perfil do aluno (default: True, opt-out) |

## Categorias

A categoria pertence ao **resultado**, não ao aluno. A mesma aluna pode fazer RX numa semana e
Scaled em outra.

1. RX
2. Scaled
3. Iniciante

## UX anti-desmotivação

- Top 10 visível com nome e tempo
- Para os demais: card "Sua posição: 23º de 47" sem expor lista intermediária
- Histórico próprio: "Você melhorou 4 posições em relação à semana passada"

## Captura de tempo

**Decisão:** começar com auto-report do aluno após o WOD.

Júlia já abre o app pós-treino — fricção mínima do lado dela. Coach Wall ganha um botão
"validar resultado" opcional, não obrigatório. Não alterar fluxo principal do Beto.

Proteção contra fraude: auto-report permitido por até 24h após a sessão.

## Critérios de aceite

- Júlia consegue registrar tempo em ≤ 3 taps após o WOD
- Ranking semanal aparece em ≤ 1.5s (snapshot quente no Redis)
- Aluno opt-out não aparece no ranking público mas continua vendo o próprio histórico
- Roberto vê no Owner workspace a métrica "% de alunos engajados com ranking" como KPI de retenção

## O que NÃO fazer

1. Feed social, fotos, comentários, likes
2. Auto-report retroativo além de 24h
3. Ranking global cross-box (tenancy não está pronta)
4. Pontos/moeda virtual (cria expectativa de loja)

## Documentação a atualizar após implementação

- Criar `docs/experience/student-engagement-mechanics.md` cobrindo ranking + opt-out
- Registrar `RecordWODResult` em [promoted-public-facades-map.md](../architecture/promoted-public-facades-map.md)
