"""
ARQUIVO: superficie publica transitoria dos modelos de onboarding.

POR QUE ELE EXISTE:
- Cria um ponto de importacao estavel para intake e seus enums sem expor boxcore.models.onboarding como API publica.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os modelos e enums de intake usados pela aplicacao.
2. Mantem a transicao segura enquanto schema, migrations e app_label continuam ancorados em boxcore.

PONTOS CRITICOS:
- O ownership de codigo do intake ja saiu de boxcore, mas o estado do Django ainda permanece historico nesta fase.
"""

from onboarding.model_definitions import IntakeSource, IntakeStatus, StudentIntake

__all__ = [
    'IntakeSource',
    'IntakeStatus',
    'StudentIntake',
]