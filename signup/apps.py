"""
ARQUIVO: configuracao do app signup.

POR QUE ELE EXISTE:
- Concentra o fluxo publico de captura de Early Adopters da landing octoboxfit.com.br.
- Liga o pagamento Stripe ao onboarding de novos donos de box.

O QUE ESTE ARQUIVO FAZ:
1. Registra o app no Django.
2. Mantem o name/label compativel com migrations.
"""
from django.apps import AppConfig


class SignupConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'signup'
    verbose_name = 'Captura de Early Adopters'
