"""
ARQUIVO: testes da lingua minima de jobs para a Signal Mesh.

POR QUE ELE EXISTE:
- protege o contrato compartilhado entre jobs e o envelope tecnico da malha.
"""

from django.test import SimpleTestCase

from integrations.mesh import SignalEnvelope, build_signal_envelope
from jobs.base import BaseJob, build_job_result


class _FakeJob(BaseJob):
    def run(self, **kwargs):
        return build_job_result(success=True, message='ok', envelope=kwargs.get('envelope'))


class JobsBaseTests(SimpleTestCase):
    def test_build_signal_envelope_returns_common_contract(self):
        envelope = build_signal_envelope(
            correlation_id='corr-1',
            idempotency_key='idem-1',
            source_channel='jobs',
            raw_reference='job:17',
        )

        self.assertIsInstance(envelope, SignalEnvelope)
        self.assertEqual(envelope.correlation_id, 'corr-1')
        self.assertEqual(envelope.idempotency_key, 'idem-1')
        self.assertEqual(envelope.source_channel, 'jobs')
        self.assertEqual(envelope.raw_reference, 'job:17')

    def test_build_job_result_embeds_signal_envelope_metadata(self):
        envelope = _FakeJob.build_signal_envelope(
            correlation_id='corr-2',
            idempotency_key='idem-2',
            source_channel='jobs',
            raw_reference='job:99',
        )

        result = build_job_result(success=True, message='done', envelope=envelope)

        self.assertEqual(result.envelope, envelope)
        self.assertEqual(result.metadata['signal_envelope']['correlation_id'], 'corr-2')
        self.assertEqual(result.metadata['signal_envelope']['idempotency_key'], 'idem-2')
