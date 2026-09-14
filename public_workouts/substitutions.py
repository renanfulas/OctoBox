"""
ARQUIVO: sugestao de substituicao de exercicio por movement_pattern
(Onda A3 do CORDA — docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- "UI de troca de exercicio" (Frente B, tabela da Onda A3/B4) depende
  disto: o aluno sem o equipamento prescrito precisa de uma alternativa
  do MESMO padrao biomecanico, nao uma reescrita manual do treino.
- So' foi possivel construir depois da revisao manual dos 82 movimentos
  extraidos (Onda A0) — sugerir a partir de `movement_pattern` nao
  revisado seria a mesma "advinhacao silenciosa" que o proprio modelo
  (PublicWorkoutMovement.movement_pattern) documenta como proibida.

PONTOS CRITICOS:
- So sugere entre movimentos ACTIVE (revisados). `pending`/sem padrao
  (protocolos de cardio, vaga livre, ou essenciais de CrossFit — que nao
  usam esta taxonomia) nunca aparecem como sugestao.
- Decisao do Renan registrada no CORDA (secao A3/B4): CURTO PRAZO sugere
  por `movement_pattern` sem diferenciar equipamento — inclui
  maquina->maquina. Priorizar alternativa de peso livre (que resolve o
  caso mais comum de "a academia nao tem esse equipamento") fica pro
  MEDIO/LONGO PRAZO, quando o schema ganhar um jeito de marcar "e
  exercicio livre" por movimento — campo que nao existe ainda de
  proposito: essa decisao de schema e' da onda que prioriza equipamento,
  nao desta.
- Nunca sugere o proprio movimento.
"""

from __future__ import annotations

from .models import PublicWorkoutMovement, PublicWorkoutMovementStatus


def suggest_substitutes(*, movement_slug: str, limit: int | None = None) -> list[dict]:
    """Alternativas ativas do mesmo `movement_pattern` de `movement_slug`.

    Lista vazia (nunca None) quando: o slug nao existe no catalogo, ainda
    nao tem `movement_pattern` classificado (pending ou crossfit — fora
    desta taxonomia), ou nao ha outro movimento ACTIVE no mesmo padrao.
    Ordenado por `label_pt` (estavel, sem noção de "melhor" sugestão —
    isso e' julgamento de treino, nao desta funcao).
    """
    movement = PublicWorkoutMovement.objects.filter(slug=movement_slug).first()
    if movement is None or not movement.movement_pattern:
        return []

    queryset = (
        PublicWorkoutMovement.objects.filter(
            movement_pattern=movement.movement_pattern,
            status=PublicWorkoutMovementStatus.ACTIVE,
        )
        .exclude(slug=movement_slug)
        .order_by('label_pt')
    )
    if limit is not None:
        queryset = queryset[:limit]

    return [
        {'slug': m.slug, 'label_pt': m.label_pt, 'reference_url': m.reference_url or None}
        for m in queryset
    ]


__all__ = ['suggest_substitutes']
