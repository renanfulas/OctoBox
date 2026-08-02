"""
ARQUIVO: builders de score historico da IA financeira.

POR QUE ELE EXISTE:
- concentra leituras de score derivadas dos analytics historicos.

PONTOS CRITICOS (Onda 9 do plano de ML de leads):
- network_prior_score_map e opcional e por padrao vazio — sem ele, o
  comportamento e IDENTICO ao anterior (fallback 0.0 para acao sem
  historico local). Isso resolve o mesmo problema ja conhecido do piso
  min_realized_count em ai/learning.py: uma acao sem historico local para
  de ser tratada como "0% de sucesso" (falso — so significa "sem dado")
  e passa a herdar o prior da rede via shrinkage, convergindo para o dado
  local conforme ele acumula (ver intelligence_network/shrinkage.py).
- GAP DOCUMENTADO: nao existe ainda uma tabela de rede para desempenho de
  ACOES DE CHURN (o hub da Onda 8 so agrega canal de lead, em
  NetworkChannelAggregate). Este parametro fica pronto para receber esse
  dado quando essa extensao futura existir; ate la, ninguem que nao passar
  network_prior_score_map explicitamente sofre qualquer mudanca.
"""

from intelligence_network.shrinkage import apply_shrinkage


def build_recommendation_historical_score_map(analytics, *, network_prior_score_map=None):
    analytics = analytics or {}
    network_prior_score_map = network_prior_score_map or {}
    score_map = {}
    seen_actions = set()

    for item in analytics.get('recommendation_performance', []):
        recommended_action = item['recommended_action']
        seen_actions.add(recommended_action)
        local_score = item.get('historical_score', 0.0) or 0.0
        prior_rate = network_prior_score_map.get(recommended_action)
        if prior_rate is None:
            score_map[recommended_action] = local_score
            continue
        local_n = item.get('realized_count', 0) or 0
        score_map[recommended_action] = apply_shrinkage(
            local_rate=local_score,
            local_n=local_n,
            prior_rate=prior_rate,
        )

    # acao com prior de rede mas sem NENHUM historico local ainda (nunca
    # apareceu em recommendation_performance): cold start puro, herda o
    # prior por inteiro em vez de cair em 0.0.
    for recommended_action, prior_rate in network_prior_score_map.items():
        if recommended_action not in seen_actions:
            score_map[recommended_action] = round(prior_rate, 1)

    return score_map


__all__ = ['build_recommendation_historical_score_map']
