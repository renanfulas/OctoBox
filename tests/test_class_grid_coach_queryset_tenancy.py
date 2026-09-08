"""
ARQUIVO: testes de isolamento por box do seletor de coach da grade de aulas.

POR QUE ELE EXISTE:
- Achados B2/B3 do relatorio de simulacao de 30 dias
  (docs/reports/simulation_30_days_e2e_box.md): `_get_class_coach_queryset()`
  filtrava so por Django Group. Group e auth_user vivem no schema `public`
  (compartilhado por TODOS os boxes nesta arquitetura multi-tenant) — sem
  filtro por box, um usuario com o Group Coach em QUALQUER box aparecia na
  lista de coaches de TODOS os boxes (vazamento entre tenants). Alem disso
  o papel "de verdade" vem de Membership (o que o checkout/onboarding cria),
  nao de Group — um Owner sem Group nunca aparecia como coach.
- Fix: catalog/form_definitions/class_grid_forms.py agora filtra por
  Membership do box ATIVO (connection.schema_name), nao por Group.

SOURCE-UNDER-TEST: catalog/form_definitions/class_grid_forms.py
(_get_class_coach_queryset, ClassGridFilterForm).

@pytest.mark.public_schema: precisa criar um SEGUNDO Box — django-tenants
exige que criacao de tenant rode em schema public (mesmo padrao de
access/tests/test_access_boundary.py::CrossBoxAccessGuardTests).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django_tenants.utils import schema_context

from access.roles import ROLE_COACH
from catalog.form_definitions.class_grid_forms import _get_class_coach_queryset
from control.models import Box, Membership


@pytest.mark.public_schema
class ClassGridCoachQuerysetTenancyTests(TestCase):
    def setUp(self):
        call_command('bootstrap_roles')
        user_model = get_user_model()

        self.test_tenant = Box.objects.get(slug='test')

        owner_b = user_model.objects.create_user(
            username='owner-outro-box-coach-leak',
            password='senha-forte-123',
            email='owner@outrobox.example.com',
        )
        self.box_b = Box.objects.create(
            slug='outro-box-coach-leak',
            schema_name='box_outro_box_coach_leak',
            display_name='Outro Box',
            status=Box.Status.ACTIVE,
            owner_user=owner_b,
        )

    def test_coach_with_group_but_membership_in_another_box_does_not_leak(self):
        """Reproducao literal do achado B2: Group Coach + zero Membership no
        box ativo NAO deve aparecer na lista de coaches desse box."""
        user_model = get_user_model()
        coach_de_outro_box = user_model.objects.create_user(
            username='coach_de_outro_box',
            password='senha-forte-123',
            email='coach@outrobox.example.com',
        )
        coach_de_outro_box.groups.add(Group.objects.get(name=ROLE_COACH))
        # Remove a Membership(test_tenant) que o conftest da de brinde a todo
        # User criado em teste — sem isto o teste passaria artificialmente
        # mesmo com o vazamento (ver docstring de
        # access/tests/test_access_boundary.py).
        Membership.objects.filter(user=coach_de_outro_box, box=self.test_tenant).delete()
        Membership.objects.create(
            user=coach_de_outro_box,
            box=self.box_b,
            role=Membership.Role.COACH,
            is_primary_box=True,
        )

        with schema_context(self.test_tenant.schema_name):
            coach_ids = set(_get_class_coach_queryset().values_list('id', flat=True))

        self.assertNotIn(coach_de_outro_box.id, coach_ids)

    def test_coach_with_membership_in_active_box_appears_even_without_group(self):
        """Contraprova de B3: o papel de verdade vem de Membership — um
        coach sem Group nao pode ficar invisivel no proprio box."""
        user_model = get_user_model()
        coach_sem_group = user_model.objects.create_user(
            username='coach_sem_group',
            password='senha-forte-123',
            email='coach2@test.example.com',
        )
        Membership.objects.update_or_create(
            user=coach_sem_group,
            box=self.test_tenant,
            defaults={'role': Membership.Role.COACH, 'is_primary_box': True},
        )

        with schema_context(self.test_tenant.schema_name):
            coach_ids = set(_get_class_coach_queryset().values_list('id', flat=True))

        self.assertIn(coach_sem_group.id, coach_ids)

    def test_superuser_remains_eligible_in_every_box(self):
        """is_superuser continua elegivel em qualquer box (suporte/DEV)."""
        user_model = get_user_model()
        support_user = user_model.objects.create_user(
            username='suporte-superuser',
            password='senha-forte-123',
            email='suporte@octobox.example.com',
            is_superuser=True,
        )
        Membership.objects.filter(user=support_user, box=self.test_tenant).delete()

        with schema_context(self.test_tenant.schema_name):
            coach_ids = set(_get_class_coach_queryset().values_list('id', flat=True))

        self.assertIn(support_user.id, coach_ids)
