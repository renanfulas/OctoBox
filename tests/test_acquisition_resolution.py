"""
ARQUIVO: testes da reconciliacao de origem comercial (operacional x declarada).

POR QUE ELE EXISTE:
- resolve_acquisition_resolution() nao tinha nenhuma cobertura de teste antes
  da correcao do achado M15 (auditoria de leads 2026-07-28): valores sentinela
  ('unidentified'/'legacy') eram tratados como canal real e geravam conflito
  falso quando o outro lado tinha uma origem genuina.
- e' logica pura (sem Django/DB), entao roda como unittest simples.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from students.domain.acquisition_resolution import resolve_acquisition_resolution


class AcquisitionResolutionTest(unittest.TestCase):
    def test_matching_sources_resolve_with_high_confidence(self):
        resolution = resolve_acquisition_resolution(
            operational_source='instagram',
            operational_detail='post da unidade',
            operational_method='intake_auto',
            declared_source='instagram',
            declared_detail='vi no post',
        )
        self.assertEqual(resolution.resolved_acquisition_source, 'instagram')
        self.assertEqual(resolution.source_confidence, 'high')
        self.assertFalse(resolution.source_conflict_flag)
        self.assertEqual(resolution.source_resolution_reason, 'operational_declared_match')

    def test_genuinely_different_sources_conflict(self):
        resolution = resolve_acquisition_resolution(
            operational_source='whatsapp',
            declared_source='instagram',
        )
        self.assertEqual(resolution.resolved_acquisition_source, 'whatsapp')
        self.assertEqual(resolution.source_confidence, 'low')
        self.assertTrue(resolution.source_conflict_flag)
        self.assertEqual(resolution.source_resolution_reason, 'operational_declared_conflict')

    def test_sentinel_operational_with_real_declared_source_does_not_conflict(self):
        """Regressao do achado M15: operacional 'unidentified' + declarado real
        nao pode gerar conflito nem descartar a declaracao boa."""
        resolution = resolve_acquisition_resolution(
            operational_source='unidentified',
            declared_source='instagram',
            declared_detail='vi no post',
        )
        self.assertEqual(resolution.resolved_acquisition_source, 'instagram')
        self.assertEqual(resolution.resolved_source_detail, 'vi no post')
        self.assertEqual(resolution.source_confidence, 'medium')
        self.assertFalse(resolution.source_conflict_flag)

    def test_sentinel_declared_with_real_operational_source_does_not_conflict(self):
        """Regressao do achado M15, lado inverso: aluno responde 'nao sei' e
        o operacional ja tem origem real. Antes isso virava conflito de baixa
        confianca; agora deve ler como operational_only."""
        resolution = resolve_acquisition_resolution(
            operational_source='whatsapp',
            operational_detail='conversa direta',
            operational_method='intake_auto',
            declared_source='unidentified',
        )
        self.assertEqual(resolution.resolved_acquisition_source, 'whatsapp')
        self.assertEqual(resolution.source_confidence, 'high')
        self.assertFalse(resolution.source_conflict_flag)
        self.assertEqual(resolution.source_resolution_reason, 'operational_only')

    def test_both_sides_sentinel_resolves_as_unknown(self):
        resolution = resolve_acquisition_resolution(
            operational_source='legacy',
            declared_source='unidentified',
        )
        self.assertEqual(resolution.resolved_acquisition_source, '')
        self.assertEqual(resolution.source_confidence, 'unknown')
        self.assertFalse(resolution.source_conflict_flag)

    def test_operational_only_uses_medium_confidence_without_intake_auto(self):
        resolution = resolve_acquisition_resolution(
            operational_source='walk_in',
            operational_method='manual_form',
        )
        self.assertEqual(resolution.resolved_acquisition_source, 'walk_in')
        self.assertEqual(resolution.source_confidence, 'medium')

    def test_declared_only_resolves_with_medium_confidence(self):
        resolution = resolve_acquisition_resolution(declared_source='referral', declared_detail='amiga')
        self.assertEqual(resolution.resolved_acquisition_source, 'referral')
        self.assertEqual(resolution.resolved_source_detail, 'amiga')
        self.assertEqual(resolution.source_confidence, 'medium')
        self.assertEqual(resolution.source_resolution_reason, 'declared_only')

    def test_no_evidence_resolves_as_unknown(self):
        resolution = resolve_acquisition_resolution()
        self.assertEqual(resolution.resolved_acquisition_source, '')
        self.assertEqual(resolution.source_confidence, 'unknown')
        self.assertFalse(resolution.source_conflict_flag)


if __name__ == '__main__':
    unittest.main()
