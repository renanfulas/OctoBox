"""
ARQUIVO: testes do helper de payload das workspace views de operations.

POR QUE ELE EXISTE:
- protege a montagem do envelope de workspace por papel sem acoplar o teste ao fluxo completo de TemplateView.

O QUE ESTE ARQUIVO FAZ:
1. valida o scope propagado no payload.
2. valida o role_slug propagado no payload.
3. valida que o helper anexa `operation_page` ao contexto.
"""

from django.test import SimpleTestCase

from operations.workspace_views import _attach_operation_workspace_payload


class _Role:
    def __init__(self, slug):
        self.slug = slug


class OperationsWorkspaceViewsTests(SimpleTestCase):
    def test_attach_operation_workspace_payload_keeps_scope_and_role_slug(self):
        context = {
            'current_role': _Role('dev'),
        }
        snapshot = {
            'transport_payload': {},
            'snapshot_version': 'test-version',
        }

        payload = _attach_operation_workspace_payload(
            context,
            page_key='operations-dev',
            title='Minha operacao',
            subtitle='Rastros, fronteiras e manutencao.',
            scope='operations-dev',
            snapshot=snapshot,
            focus_key='dev_operational_focus',
        )

        self.assertIs(context['operation_page'], payload)
        self.assertEqual(payload['behavior']['scope'], 'operations-dev')
        self.assertEqual(payload['context']['role_slug'], 'dev')
        self.assertEqual(payload['behavior']['snapshot_version'], 'test-version')
