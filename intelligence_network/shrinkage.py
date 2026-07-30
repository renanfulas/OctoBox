"""
ARQUIVO: correcao local por shrinkage (partial pooling) — Onda 9.

POR QUE ELE EXISTE:
- box nova (n_local=0) nao tem historico proprio suficiente para uma
  leitura confiavel. Em vez de nascer sem nada ou tratar uma amostra
  minuscula como se fosse sinal solido, ela comeca lendo o prior da rede
  (Onda 8) e vai convergindo para o proprio dado conforme acumula volume.
- resolve o problema ja conhecido no churn: min_realized_count=5 em
  catalog/finance_snapshot/ai/learning.py e uma gambiarra de amostra
  pequena (descarta a celula inteira). Com shrinkage, celula pequena e
  ENCOLHIDA na direcao do prior coletivo, nunca descartada nem tratada
  como 100% confiavel — sem caixa-preta, formula auditavel.
"""

from __future__ import annotations

DEFAULT_PRIOR_WEIGHT = 10


def apply_shrinkage(*, local_rate, local_n, prior_rate, prior_weight=DEFAULT_PRIOR_WEIGHT):
    """leitura_ajustada = (n_local*taxa_local + m*prior) / (n_local + m).

    Com local_n=0, a leitura E o prior (cold start). Com local_n >> prior_weight,
    o prior vira ruido de fundo e a leitura local domina. Transicao continua
    e monotonica — nunca um salto abrupto entre "so prior" e "so local".
    """
    if local_n <= 0:
        return round(prior_rate, 1)
    return round(
        (local_n * local_rate + prior_weight * prior_rate) / (local_n + prior_weight), 1
    )


__all__ = ['DEFAULT_PRIOR_WEIGHT', 'apply_shrinkage']
