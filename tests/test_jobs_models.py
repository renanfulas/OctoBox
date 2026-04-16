"""
ARQUIVO: testes de alinhamento do tracking de AsyncJob.

POR QUE ELE EXISTE:
- protege o saneamento do drift entre writer e model surface de AsyncJob.
"""

from django.test import SimpleTestCase

from jobs.models import AsyncJob


class JobsModelsTests(SimpleTestCase):
    def test_async_job_exposes_writer_fields_used_by_api(self):
        job_type_field = AsyncJob._meta.get_field('job_type')
        created_by_id_field = AsyncJob._meta.get_field('created_by_id')
        attempts_field = AsyncJob._meta.get_field('attempts')
        max_retries_field = AsyncJob._meta.get_field('max_retries')
        next_retry_at_field = AsyncJob._meta.get_field('next_retry_at')
        last_failure_kind_field = AsyncJob._meta.get_field('last_failure_kind')

        self.assertEqual(job_type_field.max_length, 64)
        self.assertTrue(job_type_field.db_index)
        self.assertTrue(created_by_id_field.null)
        self.assertTrue(created_by_id_field.db_index)
        self.assertEqual(attempts_field.default, 0)
        self.assertEqual(max_retries_field.default, 3)
        self.assertTrue(next_retry_at_field.null)
        self.assertEqual(last_failure_kind_field.max_length, 32)
