"""
ARQUIVO: fachada de compatibilidade para regras puras de conversao de intake.

POR QUE ELE EXISTE:
- Preserva imports historicos enquanto a politica de conversao migra para a camada de dominio explicita.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a nota padrao e as decisoes puras de lookup e conversao.

PONTOS CRITICOS:
- Nova regra deve nascer em students.domain, nao aqui.
"""

from students.domain import (
	DEFAULT_INTAKE_CONVERSION_NOTE,
	IntakeConversionDecision,
	IntakeLookupDecision,
	append_intake_note,
	build_intake_conversion_decision,
	build_intake_lookup_decision,
)

__all__ = [
	'DEFAULT_INTAKE_CONVERSION_NOTE',
	'IntakeConversionDecision',
	'IntakeLookupDecision',
	'append_intake_note',
	'build_intake_conversion_decision',
	'build_intake_lookup_decision',
]
