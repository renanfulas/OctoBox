"""
ARQUIVO: testes da facade publica de atribuicao do app students.

POR QUE ELE EXISTE:
- protege a fronteira publica usada por cascas HTTP para captura declarada de origem.
- evita que `catalog/views` volte a importar `students.infrastructure` diretamente.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from students.facade import run_student_source_capture_token_build, run_student_source_capture_token_read


class StudentsFacadeAttributionTests(SimpleTestCase):
    @patch('students.facade.student_attribution.build_student_source_capture_token')
    def test_run_student_source_capture_token_build_delegates_to_infrastructure(self, build_token_mock):
        build_token_mock.return_value = 'signed-token'

        result = run_student_source_capture_token_build(student_id=17)

        self.assertEqual(result, 'signed-token')
        build_token_mock.assert_called_once_with(student_id=17)

    @patch('students.facade.student_attribution.read_student_source_capture_token')
    def test_run_student_source_capture_token_read_delegates_to_infrastructure(self, read_token_mock):
        read_token_mock.return_value = 23

        result = run_student_source_capture_token_read(token='signed-token', max_age=123)

        self.assertEqual(result, 23)
        read_token_mock.assert_called_once_with(token='signed-token', max_age=123)
