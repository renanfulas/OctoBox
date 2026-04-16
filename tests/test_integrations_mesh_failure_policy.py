"""
ARQUIVO: testes da classificacao minima de falha da Signal Mesh.

POR QUE ELE EXISTE:
- protege a lingua canonica de falhas tecnicas da malha.
"""

from django.test import SimpleTestCase

from integrations.mesh import (
    FAILURE_KIND_DUPLICATE,
    FAILURE_KIND_INVALID_PAYLOAD,
    FAILURE_KIND_RETRYABLE,
    FAILURE_KIND_UNAUTHORIZED,
    classify_duplicate,
    classify_invalid_payload,
    classify_retryable,
    classify_unauthorized,
)


class IntegrationsMeshFailurePolicyTests(SimpleTestCase):
    def test_classify_duplicate_marks_non_retryable_duplicate(self):
        result = classify_duplicate(reason='duplicate-event')

        self.assertEqual(result.kind, FAILURE_KIND_DUPLICATE)
        self.assertFalse(result.retryable)

    def test_classify_invalid_payload_marks_non_retryable_invalid_payload(self):
        result = classify_invalid_payload(reason='invalid-json')

        self.assertEqual(result.kind, FAILURE_KIND_INVALID_PAYLOAD)
        self.assertFalse(result.retryable)

    def test_classify_unauthorized_marks_non_retryable_unauthorized(self):
        result = classify_unauthorized(reason='bad-token')

        self.assertEqual(result.kind, FAILURE_KIND_UNAUTHORIZED)
        self.assertFalse(result.retryable)

    def test_classify_retryable_marks_retryable(self):
        result = classify_retryable(reason='timeout')

        self.assertEqual(result.kind, FAILURE_KIND_RETRYABLE)
        self.assertTrue(result.retryable)
