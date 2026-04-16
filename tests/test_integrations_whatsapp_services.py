"""
ARQUIVO: testes de blindagem do adaptador de integracao WhatsApp.

POR QUE ELE EXISTE:
- protege que `integrations.whatsapp.services` continue fino e encaminhe para os corredores oficiais.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from integrations.whatsapp.contracts import (
    WhatsAppInboundMessage,
    WhatsAppInboundPollVote,
)
from integrations.whatsapp.services import (
    process_poll_vote_webhook,
    register_inbound_whatsapp_message,
)


class IntegrationsWhatsAppServicesTests(SimpleTestCase):
    @patch('integrations.whatsapp.services.run_register_inbound_whatsapp_message')
    def test_register_inbound_whatsapp_message_uses_communications_facade(self, run_register_mock):
        inbound_message = WhatsAppInboundMessage(
            external_message_id='wamid.1',
            phone='+5511999999999',
            display_name='Renan',
            body='Oi',
        )
        run_register_mock.return_value = type(
            'FacadeResult',
            (),
            {'accepted': True, 'reason': '', 'contact_id': 11, 'message_log_id': 13},
        )()

        result = register_inbound_whatsapp_message(inbound_message=inbound_message)

        self.assertTrue(result.accepted)
        self.assertEqual(result.contact_id, 11)
        run_register_mock.assert_called_once_with(inbound_message=inbound_message)

    @patch('integrations.whatsapp.services.run_process_poll_vote_webhook')
    def test_process_poll_vote_webhook_delegates_to_dedicated_processor(self, run_process_mock):
        poll_vote = WhatsAppInboundPollVote(
            phone='+5511999999999',
            poll_title='Check in - 23.MAR',
            option_voted='18h',
            event_id='evt_123',
        )
        expected = object()
        run_process_mock.return_value = expected

        result = process_poll_vote_webhook(poll_vote=poll_vote)

        self.assertIs(result, expected)
        run_process_mock.assert_called_once_with(poll_vote=poll_vote)
