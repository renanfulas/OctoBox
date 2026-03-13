"""
ARQUIVO: views da area financeira do catalogo.

POR QUE ELE EXISTE:
- Agrupa a camada HTTP de financeiro, exportacoes, planos e comunicacao operacional.

O QUE ESTE ARQUIVO FAZ:
1. Renderiza a central financeira filtrada.
2. Orquestra cadastro e edicao leve de planos.
3. Publica exportacoes e a acao operacional de comunicacao.

PONTOS CRITICOS:
- Qualquer regressao aqui afeta leitura gerencial, portfolio de planos e regua operacional.
"""

from catalog.views.finance_views import *