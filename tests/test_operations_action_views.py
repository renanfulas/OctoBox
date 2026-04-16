"""
ARQUIVO: testes de blindagem das mutacoes expostas em operations.action_views.

POR QUE ELE EXISTE:
- protege que as mutacoes operacionais expostas continuem entrando pelo corredor oficial do workspace facade.

O QUE ESTE ARQUIVO FAZ:
1. valida o encaminhamento da vinculacao de pagamento.
2. valida o encaminhamento da ocorrencia tecnica.
3. valida o encaminhamento da acao de presenca.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpResponseRedirect
from django.test import RequestFactory, SimpleTestCase

from operations.action_views import (
    AttendanceActionView,
    PaymentEnrollmentLinkView,
    TechnicalBehaviorNoteCreateView,
)


class OperationsActionViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model()(id=7, username='ops-user')

    def _attach_messages(self, request):
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        return request

    @patch('operations.action_views.publish_manager_stream_event')
    @patch('operations.action_views.messages.success')
    @patch('operations.action_views.reverse')
    @patch('operations.action_views.run_link_payment_enrollment')
    @patch('operations.action_views.get_object_or_404')
    def test_payment_enrollment_link_view_uses_workspace_facade(
        self,
        get_object_or_404_mock,
        run_link_payment_enrollment_mock,
        reverse_mock,
        messages_success_mock,
        publish_manager_stream_event_mock,
    ):
        request = self._attach_messages(self.factory.post('/operacao/pagamento/13/vincular-matricula/'))
        request.user = self.user
        payment = SimpleNamespace(student_id=11)
        get_object_or_404_mock.return_value = payment
        run_link_payment_enrollment_mock.return_value = SimpleNamespace(payment_id=13, enrollment_id=19)
        reverse_mock.return_value = '/aluno/11/'

        response = PaymentEnrollmentLinkView().post(request, payment_id=13)

        self.assertIsInstance(response, HttpResponseRedirect)
        run_link_payment_enrollment_mock.assert_called_once_with(actor_id=7, payment_id=13)
        publish_manager_stream_event_mock.assert_called_once()
        messages_success_mock.assert_called_once()

    @patch('operations.action_views._redirect_back')
    @patch('operations.action_views.run_create_technical_behavior_note')
    @patch('operations.action_views.get_object_or_404')
    def test_technical_behavior_note_view_uses_workspace_facade(
        self,
        get_object_or_404_mock,
        run_create_technical_behavior_note_mock,
        redirect_back_mock,
    ):
        request = self._attach_messages(
            self.factory.post(
                '/operacao/aluno/11/ocorrencia-tecnica/',
                data={'category': 'support', 'description': 'Ajustar profundidade do agachamento.'},
            )
        )
        request.user = self.user
        get_object_or_404_mock.return_value = SimpleNamespace(id=11)
        redirect_back_mock.return_value = HttpResponseRedirect('/operacao/coach/')

        response = TechnicalBehaviorNoteCreateView().post(request, student_id=11)

        self.assertIsInstance(response, HttpResponseRedirect)
        run_create_technical_behavior_note_mock.assert_called_once_with(
            actor_id=7,
            student_id=11,
            category='support',
            description='Ajustar profundidade do agachamento.',
        )

    @patch('operations.action_views._redirect_back')
    @patch('operations.action_views.run_apply_attendance_action')
    @patch('operations.action_views.get_object_or_404')
    def test_attendance_action_view_uses_workspace_facade(
        self,
        get_object_or_404_mock,
        run_apply_attendance_action_mock,
        redirect_back_mock,
    ):
        request = self._attach_messages(self.factory.post('/operacao/presenca/17/check-in/'))
        request.user = self.user
        get_object_or_404_mock.return_value = SimpleNamespace(id=17)
        run_apply_attendance_action_mock.return_value = SimpleNamespace(attendance_id=17, status='checked-in')
        redirect_back_mock.return_value = HttpResponseRedirect('/operacao/coach/')

        response = AttendanceActionView().post(request, attendance_id=17, action='check-in')

        self.assertIsInstance(response, HttpResponseRedirect)
        run_apply_attendance_action_mock.assert_called_once_with(
            actor_id=7,
            attendance_id=17,
            action='check-in',
        )
