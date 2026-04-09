"""
ARQUIVO: testes da fundacao de origem comercial na ficha do aluno.

POR QUE ELE EXISTE:
- protege a exigencia de origem operacional no cadastro principal.
- garante que o intake consiga sugerir a origem sem popup ou improviso.
"""

from django.test import TestCase

from catalog.forms import StudentQuickForm
from onboarding.attribution import build_intake_attribution_payload
from onboarding.models import StudentIntake


class StudentAcquisitionFormTests(TestCase):
    def test_student_quick_form_requires_acquisition_source(self):
        form = StudentQuickForm(
            data={
                'full_name': 'Aluno Origem',
                'phone': '5511999991111',
                'status': 'active',
                'acquisition_source': '',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('acquisition_source', form.errors)

    def test_student_quick_form_prefills_acquisition_from_selected_intake(self):
        intake = StudentIntake.objects.create(
            full_name='Lead Origem',
            phone='5511999992222',
            email='lead.origem@example.com',
            source='manual',
            raw_payload=build_intake_attribution_payload(
                source='manual',
                acquisition_channel='instagram',
                acquisition_detail='story da unidade',
                entry_kind='lead',
            ),
        )

        form = StudentQuickForm(initial={'intake_record': intake})

        self.assertEqual(form.fields['acquisition_source'].initial, 'instagram')
        self.assertEqual(form.fields['acquisition_source_detail'].initial, 'story da unidade')
