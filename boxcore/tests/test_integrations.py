"""
ARQUIVO: testes da fundacao de integracoes externas.

POR QUE ELE EXISTE:
- Protege a identidade de canal e a entrada idempotente de mensagens antes da integracao oficial com WhatsApp.

O QUE ESTE ARQUIVO FAZ:
1. Testa reconciliacao de contato com aluno existente.
2. Testa fallback para intake ainda nao convertido.
3. Testa idempotencia simples por external_message_id.

PONTOS CRITICOS:
- Se estes testes quebrarem, a base de integracao pode criar duplicidade ou perder vinculo de canal.
"""

from django.db import IntegrityError
from django.test import TestCase

from communications.models import MessageDirection, StudentIntake, WhatsAppContact, WhatsAppContactStatus, WhatsAppMessageLog
from integrations.whatsapp.contracts import WhatsAppInboundMessage
from integrations.whatsapp.services import register_inbound_whatsapp_message
from shared_support.phone_numbers import normalize_phone_number
from students.models import Student


class WhatsAppIntegrationFoundationTests(TestCase):
    def test_register_inbound_message_links_existing_student_by_normalized_phone(self):
        student = Student.objects.create(full_name='Carla Souza', phone='5511999998888', status='active')

        result = register_inbound_whatsapp_message(
            inbound_message=WhatsAppInboundMessage(
                external_message_id='wamid-001',
                phone='+55 (11) 99999-8888',
                display_name='Carla',
                body='Oi, quero falar sobre meu plano.',
                raw_payload={'source': 'test'},
            )
        )

        self.assertTrue(result.accepted)
        contact = WhatsAppContact.objects.get(pk=result.contact_id)
        self.assertEqual(contact.phone, normalize_phone_number('+55 (11) 99999-8888'))
        self.assertEqual(contact.linked_student, student)
        self.assertEqual(contact.status, WhatsAppContactStatus.LINKED)
        self.assertTrue(WhatsAppMessageLog.objects.filter(contact=contact, direction=MessageDirection.INBOUND).exists())

    def test_register_inbound_message_preserves_new_contact_when_only_intake_exists(self):
        StudentIntake.objects.create(full_name='Lead Joao', phone='551188887777', source='whatsapp')

        result = register_inbound_whatsapp_message(
            inbound_message=WhatsAppInboundMessage(
                external_message_id='wamid-002',
                phone='55 11 8888-7777',
                display_name='Joao Lead',
                body='Queria saber os valores.',
            )
        )

        self.assertTrue(result.accepted)
        contact = WhatsAppContact.objects.get(pk=result.contact_id)
        self.assertEqual(contact.phone, normalize_phone_number('55 11 8888-7777'))
        self.assertIsNone(contact.linked_student)
        self.assertEqual(contact.status, WhatsAppContactStatus.NEW)
        self.assertIsNotNone(contact.last_inbound_at)

    def test_register_inbound_message_is_idempotent_by_external_message_id(self):
        Student.objects.create(full_name='Marina Costa', phone='551177776666', status='active')
        payload = WhatsAppInboundMessage(
            external_message_id='wamid-003',
            phone='55 (11) 7777-6666',
            display_name='Marina',
            body='Teste de duplicidade.',
        )

        first_result = register_inbound_whatsapp_message(inbound_message=payload)
        second_result = register_inbound_whatsapp_message(inbound_message=payload)

        self.assertTrue(first_result.accepted)
        self.assertTrue(second_result.accepted)
        self.assertEqual(second_result.reason, 'duplicate-message-id')
        self.assertEqual(WhatsAppMessageLog.objects.filter(external_message_id='wamid-003').count(), 1)

    def test_register_inbound_message_stores_structured_payload_and_provider_identity(self):
        result = register_inbound_whatsapp_message(
            inbound_message=WhatsAppInboundMessage(
                external_message_id='wamid-004',
                external_contact_id='wa-contact-004',
                phone='55 11 95555-4444',
                display_name='Lia',
                body='Quero agendar uma aula experimental.',
                raw_payload={
                    'event': 'message',
                    'access_token': 'super-secret',
                    'metadata': {'authorization': 'Bearer abc123', 'phone_number_id': '123'},
                },
            )
        )

        self.assertTrue(result.accepted)
        contact = WhatsAppContact.objects.get(pk=result.contact_id)
        self.assertEqual(contact.phone, normalize_phone_number('55 11 95555-4444'))
        message = WhatsAppMessageLog.objects.get(external_message_id='wamid-004')
        self.assertEqual(contact.external_contact_id, 'wa-contact-004')
        self.assertIsInstance(message.raw_payload, dict)
        self.assertEqual(message.raw_payload['access_token'], '[redacted]')
        self.assertEqual(message.raw_payload['metadata']['authorization'], '[redacted]')

    def test_whatsapp_message_log_enforces_unique_external_message_id(self):
        contact = WhatsAppContact.objects.create(phone='5511991111222', display_name='Contato Teste')
        WhatsAppMessageLog.objects.create(contact=contact, external_message_id='wamid-unique', raw_payload={})

        with self.assertRaises(IntegrityError):
            WhatsAppMessageLog.objects.create(contact=contact, external_message_id='wamid-unique', raw_payload={})
