"""
ARQUIVO: resolucao de cohort de box para benchmark de rede (Onda 8).

POR QUE ELE EXISTE:
- mediar box premium de capital com box pequeno de bairro produz prior
  enganoso. O benchmark de rede so compara dentro do MESMO cohort, nunca
  com a rede inteira.

PONTOS CRITICOS:
- nao existe campo "porte"/"ticket medio"/"regiao" em control.Box hoje.
  Ticket medio e regiao exigiriam schema novo em control.Box — decisao de
  produto, fora do escopo tecnico desta onda. O cohort nesta primeira
  rodada usa SO porte (alunos ativos), a unica dimensao ja computavel sem
  mudar o modelo Box. Ver desvio registrado em
  docs/plans/leads-ml-technical-execution-guide.md, Onda 8.
"""

from __future__ import annotations

# (limite superior exclusivo, rotulo do cohort) em ordem crescente.
BOX_COHORT_BANDS = (
    (30, 'micro'),
    (80, 'pequeno'),
    (200, 'medio'),
)
BOX_COHORT_LARGE = 'grande'


def resolve_box_cohort(*, active_student_count: int) -> str:
    for threshold, label in BOX_COHORT_BANDS:
        if active_student_count < threshold:
            return label
    return BOX_COHORT_LARGE


__all__ = ['BOX_COHORT_BANDS', 'BOX_COHORT_LARGE', 'resolve_box_cohort']
