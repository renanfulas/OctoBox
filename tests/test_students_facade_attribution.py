"""
ARQUIVO: testes da facade publica de atribuicao do app students.

POR QUE ELE EXISTE:
- protege a fronteira publica usada por cascas HTTP para captura declarada de origem.
- evita que `catalog/views` volte a importar `students.infrastructure` diretamente.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from students.facade import (
    SourceCaptureTokenPayload,
    run_student_source_capture_token_build,
    run_student_source_capture_token_read,
    run_student_source_capture_token_read_payload,
)


class StudentsFacadeAttributionTests(SimpleTestCase):
    @patch('students.facade.student_attribution.build_student_source_capture_token')
    def test_run_student_source_capture_token_build_delegates_to_infrastructure(self, build_token_mock):
        build_token_mock.return_value = 'signed-token'

        result = run_student_source_capture_token_build(student_id=17)

        self.assertEqual(result, 'signed-token')
        build_token_mock.assert_called_once_with(student_id=17, box_root_slug='')

    @patch('students.facade.student_attribution.build_student_source_capture_token')
    def test_run_student_source_capture_token_build_forwards_box_root_slug(self, build_token_mock):
        build_token_mock.return_value = 'signed-token'

        run_student_source_capture_token_build(student_id=17, box_root_slug='box_acme')

        build_token_mock.assert_called_once_with(student_id=17, box_root_slug='box_acme')

    @patch('students.facade.student_attribution.read_student_source_capture_token')
    def test_run_student_source_capture_token_read_delegates_to_infrastructure(self, read_token_mock):
        read_token_mock.return_value = 23

        result = run_student_source_capture_token_read(token='signed-token', max_age=123)

        self.assertEqual(result, 23)
        read_token_mock.assert_called_once_with(token='signed-token', max_age=123)

    @patch('students.facade.student_attribution.read_student_source_capture_token_payload')
    def test_run_student_source_capture_token_read_payload_delegates_to_infrastructure(self, read_payload_mock):
        read_payload_mock.return_value = SourceCaptureTokenPayload(student_id=23, box_root_slug='box_acme')

        result = run_student_source_capture_token_read_payload(token='signed-token', max_age=123)

        self.assertEqual(result, SourceCaptureTokenPayload(student_id=23, box_root_slug='box_acme'))
        read_payload_mock.assert_called_once_with(token='signed-token', max_age=123)
