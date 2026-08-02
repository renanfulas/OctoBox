"""
ARQUIVO: testes da separacao entre leitura operacional e leitura analitica
da Central de Intake (Onda 5).

POR QUE ELE EXISTE:
- antes da Onda 5, radar e metricas por canal comecavam do MESMO queryset
  operacional (aberto + sem vinculo), entao todo lead convertido sumia dos
  agregados (achado A6) e o filtro 'Resolvido' sempre retornava vazio
  (achado M2). Sem teste direto, a regressao volta silenciosamente.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from onboarding.attribution import build_intake_attribution_payload
from onboarding.models import IntakeStatus, StudentIntake
from onboarding.queries import build_intake_center_snapshot
from students.models import Student


class OnboardingQueriesAnalyticsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='onboarding-analytics-actor',
            email='onboarding-analytics@example.com',
            password='senha-forte-123',
        )

    def _create_intake(self, *, full_name, phone, status, acquisition_channel='', linked_student=None):
        return StudentIntake.objects.create(
            full_name=full_name,
            phone=phone,
            source='manual',
            status=status,
            linked_student=linked_student,
            raw_payload=build_intake_attribution_payload(
                source='manual',
                acquisition_channel=acquisition_channel,
                entry_kind='lead',
            ),
        )

    def test_cards_soma_com_missing_e_legacy_inferred_fecha_com_total(self):
        self._create_intake(full_name='Lead Instagram', phone='5511910000001', status=IntakeStatus.NEW, acquisition_channel='instagram')
        self._create_intake(full_name='Lead Evento', phone='5511910000002', status=IntakeStatus.REVIEWING, acquisition_channel='event')
        self._create_intake(full_name='Lead Nao Identificado', phone='5511910000003', status=IntakeStatus.NEW, acquisition_channel='unidentified')
        self._create_intake(full_name='Lead Legado', phone='5511910000004', status=IntakeStatus.NEW, acquisition_channel='legacy')
        self._create_intake(full_name='Lead Sem Canal', phone='5511910000005', status=IntakeStatus.NEW, acquisition_channel='')
        StudentIntake.objects.create(
            full_name='Lead Legado Sem Payload',
            phone='5511910000006',
            source='csv',
            status=IntakeStatus.NEW,
        )

        snapshot = build_intake_center_snapshot(params={'source_period': 'all'})
        radar_board = snapshot['radar_board']

        cards_total = sum(card['value'] for card in radar_board['cards'])
        missing_total = radar_board['analytics']['missing_attribution_total']
        legacy_inferred_total = radar_board['analytics']['legacy_inferred_total']

        self.assertEqual(cards_total + missing_total + legacy_inferred_total, radar_board['total'])
        self.assertEqual(radar_board['total'], 6)
        # os 3 canais que antes nao tinham card (achado M9) agora aparecem.
        card_by_key = {card['key']: card['value'] for card in radar_board['cards']}
        self.assertEqual(card_by_key['event'], 1)
        self.assertEqual(card_by_key['unidentified'], 1)
        self.assertEqual(card_by_key['legacy'], 1)
        self.assertEqual(missing_total, 1)
        self.assertEqual(legacy_inferred_total, 1)

    def test_filtro_resolvido_retorna_linhas_em_vez_de_vazio(self):
        """Regressao do achado M2: o filtro antigo intersectava com uma base
        que ja excluia APPROVED/REJECTED por construcao e sempre voltava
        vazio."""
        self._create_intake(full_name='Lead Aprovado', phone='5511910000011', status=IntakeStatus.APPROVED)
        self._create_intake(full_name='Lead Rejeitado', phone='5511910000012', status=IntakeStatus.REJECTED)
        self._create_intake(full_name='Lead Ainda Aberto', phone='5511910000013', status=IntakeStatus.NEW)

        snapshot = build_intake_center_snapshot(params={'semantic_stage': 'resolved'})

        self.assertEqual(snapshot['queue_total_count'], 2)
        resolved_names = {item['object'].full_name for item in snapshot['queue_items']}
        self.assertEqual(resolved_names, {'Lead Aprovado', 'Lead Rejeitado'})

    def test_leitura_analitica_inclui_lead_convertido(self):
        """Regressao do achado A6: lead convertido nao pode sumir do
        agregado por canal so porque saiu da fila operacional."""
        student = Student.objects.create(full_name='Aluno Convertido', phone='5511910000021')
        self._create_intake(
            full_name='Lead Convertido Instagram',
            phone='5511910000022',
            status=IntakeStatus.APPROVED,
            acquisition_channel='instagram',
            linked_student=student,
        )

        snapshot = build_intake_center_snapshot()
        channel_by_key = {c['key']: c for c in snapshot['channel_analytics']['channels']}

        self.assertEqual(channel_by_key['instagram']['captured_total'], 1)
        self.assertEqual(channel_by_key['instagram']['converted_total'], 1)
        self.assertEqual(channel_by_key['instagram']['open_total'], 0)

    def test_fila_operacional_continua_excluindo_convertido(self):
        """A fila de trabalho (o time olha isso todo dia) precisa continuar
        mostrando so o que ainda pede acao — convertido nao deve reaparecer
        la so porque a leitura analitica passou a enxerga-lo."""
        student = Student.objects.create(full_name='Aluno Convertido 2', phone='5511910000031')
        self._create_intake(
            full_name='Lead Convertido Solo',
            phone='5511910000032',
            status=IntakeStatus.APPROVED,
            linked_student=student,
        )

        snapshot = build_intake_center_snapshot()

        self.assertEqual(snapshot['visible_queue_count'], 0)
        self.assertEqual(snapshot['queue_total_count'], 0)
