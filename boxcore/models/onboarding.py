"""
ARQUIVO: fachada legada dos models de onboarding dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem o estado historico do Django em boxcore enquanto a implementacao real de intake vive em onboarding.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta enums e model reais de intake.
2. Preserva imports antigos durante a transicao.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar implementacao real dos models.
- O app label continua sendo boxcore nesta etapa para evitar mudanca de schema e de migrations.
"""

from onboarding.model_definitions import IntakeSource, IntakeStatus, StudentIntake


__all__ = ['IntakeSource', 'IntakeStatus', 'StudentIntake']