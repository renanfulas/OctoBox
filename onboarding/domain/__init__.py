"""Superficie publica das regras de dominio de onboarding."""

from .intake_semantics import (
    IntakeConversionDecision,
    IntakeSemanticState,
    build_intake_conversion_decision,
    build_intake_semantic_state,
    resolve_intake_action_permissions,
)

__all__ = [
    'IntakeConversionDecision',
    'IntakeSemanticState',
    'build_intake_conversion_decision',
    'build_intake_semantic_state',
    'resolve_intake_action_permissions',
]