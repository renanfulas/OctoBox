"""
ARQUIVO: testes do workflow superdev — comando de bootstrap + seletor de box.

CAMADAS:
- bootstrap_superdev: cria/garante a conta de suporte (idempotente, senha via env).
- BoxSwitchView: lista boxes com Membership, seta active_box_id, barra sem acesso.

@pytest.mark.public_schema onde ha criacao de Box (modelo tenant) — provibido fora
do schema public. _run_step e mockado para nao exigir DDL real (CREATE SCHEMA).
"""

from __future__ import annotations

import os

import pytest
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings


# ---------------------------------------------------------------------------
# bootstrap_superdev
# ---------------------------------------------------------------------------

@pytest.mark.public_schema
@override_settings(SUPERDEV_USERNAME='superdev', SUPERDEV_EMAIL='superdev@octoboxfit.com.br')
class BootstrapSuperdevCommandTest(TestCase):

    def test_creates_superdev_idempotently(self):
        User = get_user_model()

        call_command('bootstrap_superdev')
        user = User.objects.get(username='superdev')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.email, 'superdev@octoboxfit.com.br')
        self.assertFalse(user.has_usable_password(), 'Sem SUPERDEV_PASSWORD a senha deve ser inutilizavel')

        # Segunda execucao nao duplica
        call_command('bootstrap_superdev')
        self.assertEqual(User.objects.filter(username='superdev').count(), 1)

    def test_sets_password_from_env(self):
        User = get_user_model()
        os.environ['SUPERDEV_PASSWORD'] = 'Str0ng!Pass123'
        try:
            call_command('bootstrap_superdev')
        finally:
            del os.environ['SUPERDEV_PASSWORD']

        user = User.objects.get(username='superdev')
        self.assertTrue(user.check_password('Str0ng!Pass123'))

    def test_repairs_demoted_flags(self):
        User = get_user_model()
        User.objects.create_user(
            username='superdev', email='superdev@octoboxfit.com.br',
            is_staff=False, is_superuser=False, is_active=False,
        )

        call_command('bootstrap_superdev')

        user = User.objects.get(username='superdev')
        self.assertTrue(user.is_staff and user.is_superuser and user.is_active)


# ---------------------------------------------------------------------------
# BoxSwitchView (/box/)
# ---------------------------------------------------------------------------

@pytest.mark.public_schema
@override_settings(SUPERDEV_USERNAME='superdev', SUPERDEV_AUTO_ATTACH=True)
class BoxSwitchViewTest(TestCase):

    def setUp(self):
        User = get_user_model()
        # Superdev criado ANTES do provisionamento para ser anexado aos boxes.
        self.superdev = User.objects.create_user(
            username='superdev', email='superdev@octoboxfit.com.br',
            is_staff=True, is_superuser=True,
        )
        self.owner = User.objects.create_user('bs_owner', 'bs_owner@test.com', 'pw-forte-123')
        self.other = User.objects.create_user('bs_other', 'bs_other@test.com', 'pw-forte-123')

        # provision_box exige schema public (django-tenants proibe criar Box fora
        # dele). O opt-out public_schema do conftest nao reseta o search_path, entao
        # fixamos public explicitamente aqui para nao depender da ordem dos testes.
        from django_tenants.utils import schema_context, get_public_schema_name
        with patch('control.services._run_step', return_value=None):
            from control.services import provision_box
            with schema_context(get_public_schema_name()):
                self.box_a = provision_box(owner_user=self.owner, display_name='Box A', slug='box-a-sw')
                self.box_b = provision_box(owner_user=self.other, display_name='Box B', slug='box-b-sw')

    def test_get_lists_only_membership_boxes(self):
        self.client.force_login(self.owner)
        resp = self.client.get('/box/')
        self.assertEqual(resp.status_code, 200)
        boxes = list(resp.context['boxes'])
        self.assertIn(self.box_a, boxes)
        self.assertNotIn(self.box_b, boxes)  # owner nao tem Membership em box_b

    def test_superdev_sees_all_boxes(self):
        self.client.force_login(self.superdev)
        resp = self.client.get('/box/')
        self.assertEqual(resp.status_code, 200)
        boxes = list(resp.context['boxes'])
        self.assertIn(self.box_a, boxes)
        self.assertIn(self.box_b, boxes)  # superdev foi anexado a ambos

    def test_post_sets_active_box_and_redirects(self):
        self.client.force_login(self.owner)
        resp = self.client.post('/box/', {'box_id': self.box_a.pk})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.client.session['active_box_id'], self.box_a.pk)

    def test_post_without_membership_is_blocked(self):
        self.client.force_login(self.owner)
        resp = self.client.post('/box/', {'box_id': self.box_b.pk})
        self.assertEqual(resp.status_code, 302)
        self.assertIsNone(self.client.session.get('active_box_id'))
