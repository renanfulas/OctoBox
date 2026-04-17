"""
ARQUIVO: testes do inspetor leve de importacao de leads.

POR QUE ELE EXISTE:
- protege a contagem valida e o stop-early antes da orquestracao HTTP e dos jobs.

O QUE ESTE ARQUIVO FAZ:
1. valida contagem de CSV nas tres faixas declaradas.
2. valida que linhas invalidas nao contam.
3. valida suporte ao VCF de iPhone.
4. valida que o stream volta ao inicio apos a inspecao.

PONTOS CRITICOS:
- se estes testes quebrarem, a policy pode receber contagem errada e mandar o arquivo para o trilho incorreto.
"""

from io import BytesIO

from django.test import SimpleTestCase

from operations.models import LeadImportDeclaredRange, LeadImportSourceType
from operations.services.lead_import_inspector import inspect_lead_import_stream


def _build_csv_stream(rows: list[str]) -> BytesIO:
    content = 'Nome,Telefone,Email\n' + '\n'.join(rows) + '\n'
    return BytesIO(content.encode('utf-8'))


class LeadImportInspectorTests(SimpleTestCase):
    def test_inspector_counts_valid_csv_rows_up_to_200_without_crossing_threshold(self):
        rows = [f'Aluno {index},(11) 90000-{index:04d},lead{index}@example.com' for index in range(1, 201)]
        stream = _build_csv_stream(rows)

        result = inspect_lead_import_stream(
            file_stream=stream,
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            declared_range=LeadImportDeclaredRange.UP_TO_200,
        )

        self.assertEqual(result.detected_lead_count, 200)
        self.assertTrue(result.inspection_complete)
        self.assertFalse(result.threshold_crossed)

    def test_inspector_stops_early_when_declared_up_to_200_crosses_threshold(self):
        rows = [f'Aluno {index},(11) 91000-{index:04d},lead{index}@example.com' for index in range(1, 260)]
        stream = _build_csv_stream(rows)

        result = inspect_lead_import_stream(
            file_stream=stream,
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            declared_range=LeadImportDeclaredRange.UP_TO_200,
        )

        self.assertEqual(result.detected_lead_count, 201)
        self.assertFalse(result.inspection_complete)
        self.assertTrue(result.threshold_crossed)

    def test_inspector_stops_early_at_501_for_medium_declared_range(self):
        rows = [f'Aluno {index},(11) 92000-{index:04d},lead{index}@example.com' for index in range(1, 800)]
        stream = _build_csv_stream(rows)

        result = inspect_lead_import_stream(
            file_stream=stream,
            source_type=LeadImportSourceType.TECNOFIT_EXPORT,
            declared_range=LeadImportDeclaredRange.FROM_201_TO_500,
        )

        self.assertEqual(result.detected_lead_count, 501)
        self.assertFalse(result.inspection_complete)
        self.assertTrue(result.threshold_crossed)

    def test_inspector_stops_early_at_2001_for_large_declared_range(self):
        rows = [f'Aluno {index},(11) 93000-{index:04d},lead{index}@example.com' for index in range(1, 2300)]
        stream = _build_csv_stream(rows)

        result = inspect_lead_import_stream(
            file_stream=stream,
            source_type=LeadImportSourceType.NEXTFIT_EXPORT,
            declared_range=LeadImportDeclaredRange.FROM_501_TO_2000,
        )

        self.assertEqual(result.detected_lead_count, 2001)
        self.assertFalse(result.inspection_complete)
        self.assertTrue(result.threshold_crossed)

    def test_inspector_ignores_rows_without_valid_phone(self):
        stream = _build_csv_stream(
            [
                'Aluno 1,(11) 94000-0001,lead1@example.com',
                'Aluno 2,,lead2@example.com',
                'Aluno 3,abc,lead3@example.com',
                'Aluno 4,(11) 94000-0004,lead4@example.com',
            ]
        )

        result = inspect_lead_import_stream(
            file_stream=stream,
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            declared_range=LeadImportDeclaredRange.UP_TO_200,
        )

        self.assertEqual(result.detected_lead_count, 2)
        self.assertTrue(result.inspection_complete)

    def test_inspector_counts_vcf_contacts_with_valid_phone_only(self):
        vcf_content = '\n'.join(
            [
                'BEGIN:VCARD',
                'FN:Maria Silva',
                'TEL;TYPE=CELL:(11) 95555-1111',
                'END:VCARD',
                'BEGIN:VCARD',
                'FN:Sem Telefone',
                'EMAIL:sem.telefone@example.com',
                'END:VCARD',
                'BEGIN:VCARD',
                'FN:Joao Lima',
                'TEL;TYPE=CELL:(11) 95555-2222',
                'END:VCARD',
            ]
        )
        stream = BytesIO(vcf_content.encode('utf-8'))

        result = inspect_lead_import_stream(
            file_stream=stream,
            source_type=LeadImportSourceType.IPHONE_VCF,
            declared_range=LeadImportDeclaredRange.UP_TO_200,
        )

        self.assertEqual(result.detected_lead_count, 2)
        self.assertTrue(result.inspection_complete)
        self.assertFalse(result.threshold_crossed)

    def test_inspector_rewinds_stream_after_inspection(self):
        stream = _build_csv_stream(['Aluno 1,(11) 95000-0001,lead1@example.com'])

        inspect_lead_import_stream(
            file_stream=stream,
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            declared_range=LeadImportDeclaredRange.UP_TO_200,
        )

        self.assertEqual(stream.tell(), 0)
        self.assertTrue(stream.read().startswith(b'Nome,Telefone,Email'))
