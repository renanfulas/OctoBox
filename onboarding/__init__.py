"""
ARQUIVO: pacote leve da fronteira de onboarding.

POR QUE ELE EXISTE:
- Expõe uma porta estável para intake sem obrigar imports de aplicação a dependerem de boxcore.models.onboarding.

O QUE ESTE ARQUIVO FAZ:
1. Marca onboarding como namespace próprio para a transição arquitetural.

PONTOS CRITICOS:
- Este pacote ainda não assume migrations nem app_label próprios.
"""
