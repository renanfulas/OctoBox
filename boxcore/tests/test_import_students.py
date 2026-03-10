"""
ARQUIVO: testes do importador de alunos.

POR QUE ELE EXISTE:
- Garante que a importação em lote continue funcionando sem duplicidade indevida.

O QUE ESTE ARQUIVO FAZ:
1. Cria um aluno pré-existente.
2. Importa um CSV de teste.
3. Confirma atualização pelo WhatsApp.
4. Confirma criação de novo aluno.

PONTOS CRITICOS:
- Se esse teste falhar, provavelmente a regra de deduplicação foi alterada.
"""

import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from boxcore.models import Student


class ImportStudentsCsvCommandTests(TestCase):
    def test_import_creates_and_updates_students_by_phone(self):
        Student.objects.create(full_name='Aluno Antigo', phone='5511911111111')

        csv_content = (
            'full_name,whatsapp,email,status,gender,health_issue_status,cpf\n'
            'Ana Nova,5511911111111,ana@example.com,active,female,no,12345678900\n'
            'Bruno Lima,5511922222222,bruno@example.com,paused,male,yes,98765432100\n'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / 'students.csv'
            csv_path.write_text(csv_content, encoding='utf-8')

            call_command('import_students_csv', str(csv_path))

        self.assertEqual(Student.objects.count(), 2)
        updated_student = Student.objects.get(phone='5511911111111')
        new_student = Student.objects.get(phone='5511922222222')

        self.assertEqual(updated_student.full_name, 'Ana Nova')
        self.assertEqual(updated_student.email, 'ana@example.com')
        self.assertEqual(updated_student.gender, 'female')
        self.assertEqual(new_student.status, 'paused')
        self.assertEqual(new_student.health_issue_status, 'yes')