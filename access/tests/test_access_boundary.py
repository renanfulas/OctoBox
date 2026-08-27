"""
ARQUIVO: testes de gate da Onda 1 — escalada de privilégio cross-box.

POR QUE EXISTE:
- Prova a correção do achado crítico: Owner do box A podia listar, resetar
  senha e editar staff de QUALQUER box (inclusive superusuário), porque a
  listagem de /acessos/ não tinha filtro de box e os handlers resolviam o
  alvo por pk cru, sem checar propriedade. Ver
  docs/plans/ondas-correcao-tenancy-billing-2026-08-25.md, Onda 1.

CAVEAT DO CONFTEST (documentado no próprio plano — não pular):
- conftest.py instala um post_save que dá Membership(box=test_tenant,
  role=OWNER) a TODO User criado durante o teste, para tenant-resolution
  (evitar 403). Isso significa que um usuário "de outro box" criado aqui
  AINDA GANHA uma Membership em test_tenant de brinde — o que é inofensivo
  para os testes de reset/toggle (o guard nega por "tem Membership em
  OUTRO box além do do ator", e ter a extra em test_tenant não anula isso),
  mas é FATAL para o teste de listagem: sem remover essa Membership extra
  explicitamente, o usuário SEMPRE apareceria na listagem escopada por
  test_tenant, e o teste passaria mesmo se o filtro de 1b estivesse quebrado
  ou nunca tivesse sido escrito. Ver test_listing_excludes_user_exclusive_to_other_box.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from control.models import Box, Membership


@pytest.mark.public_schema
class CrossBoxAccessGuardTests(TestCase):
    """Owner do box de teste não gerencia usuário de outro box nem superusuário.

    @pytest.mark.public_schema: cria um segundo Box (box_b) — django-tenants
    exige que criação de tenant rode em schema public (mesmo padrão de
    tests/test_control_services.py::ProvisionBoxTest).

    ORDEM IMPORTA: `self.client.force_login` dispara o signal de login que
    resolve o tenant e comuta `connection.schema_name` para o box do ator
    (comportamento de produção legítimo — replica o que
    TenantBySessionMiddleware faria numa request real). Por isso toda
    criação de objeto em schema public (Box, User) tem que vir ANTES do
    force_login nesta setUp — depois dele a conexão não está mais em public.
    """

    def setUp(self):
        call_command('bootstrap_roles')
        user_model = get_user_model()

        self.test_tenant = Box.objects.get(slug='test')

        self.owner = user_model.objects.create_user(
            username='box-a-owner',
            password='senha-forte-123',
            email='owner@boxa.example.com',
        )
        self.owner.groups.add(Group.objects.get(name=ROLE_OWNER))

        # Box B: um segundo tenant, genuinamente diferente do test_tenant.
        # Precisa vir ANTES do force_login abaixo — ver docstring da classe.
        self.box_b = Box.objects.create(
            slug='outro-box',
            schema_name='box_outro_box',
            display_name='Outro Box',
            status=Box.Status.ACTIVE,
            owner_user=self.owner,
        )

        self.client.force_login(self.owner)

    def _reset(self, target_pk):
        return self.client.post(
            reverse('access-overview'),
            {'access_action': 'reset_password', 'target_profile_id': str(target_pk)},
            follow=True,
        )

    def test_owner_cannot_reset_password_of_user_in_another_box(self):
        user_model = get_user_model()
        target = user_model.objects.create_user(
            username='staff-box-b',
            password='senha-antiga-123',
            email='staff@boxb.example.com',
        )
        # Membership real do target é em box_b — a Membership(test_tenant)
        # que o conftest também deu é a extra "de brinde" descrita no
        # docstring do módulo; não invalida o teste (ver caveat acima).
        Membership.objects.update_or_create(
            user=target, box=self.box_b,
            defaults={'role': Membership.Role.OWNER, 'is_primary_box': True},
        )

        response = self._reset(target.pk)

        target.refresh_from_db()
        self.assertTrue(
            target.check_password('senha-antiga-123'),
            'senha do usuário de outro box foi trocada — guarda cross-box não funcionou',
        )
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('outro box' in m for m in messages))

    def test_owner_cannot_reset_password_of_superuser(self):
        user_model = get_user_model()
        target = user_model.objects.create_user(
            username='super-alvo',
            password='senha-antiga-456',
            email='super@example.com',
        )
        target.is_superuser = True
        target.is_staff = True
        target.save(update_fields=['is_superuser', 'is_staff'])

        response = self._reset(target.pk)

        target.refresh_from_db()
        self.assertTrue(
            target.check_password('senha-antiga-456'),
            'senha do superusuário foi trocada — guarda anti-superuser não funcionou',
        )
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('superusuário' in m for m in messages))

    def test_listing_excludes_user_exclusive_to_other_box(self):
        user_model = get_user_model()
        exclusive_to_b = user_model.objects.create_user(
            username='exclusivo-box-b',
            password='x',
            email='exclusivo@boxb.example.com',
        )
        # Remove a Membership(test_tenant) que o conftest deu de brinde —
        # sem isto o teste passaria artificialmente mesmo com o filtro
        # de 1b quebrado (ver docstring do módulo).
        Membership.objects.filter(user=exclusive_to_b, box=self.test_tenant).delete()
        Membership.objects.create(
            user=exclusive_to_b, box=self.box_b,
            role=Membership.Role.MANAGER, is_primary_box=True,
        )
        self.assertFalse(
            Membership.objects.filter(user=exclusive_to_b, box=self.test_tenant).exists(),
            'setup inválido: usuário ainda tem Membership em test_tenant',
        )

        response = self.client.get(reverse('access-overview') + '?manage_profiles=1')

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'exclusivo-box-b')

    def test_listing_includes_owner_who_belongs_to_this_box(self):
        """Contraprova do teste acima: o próprio ator (que pertence ao box) aparece."""
        response = self.client.get(reverse('access-overview') + '?manage_profiles=1')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'box-a-owner')


class RolePerBoxRenderingTests(TestCase):
    """1c fim-a-fim: 4 usuários de papéis distintos resolvem 4 role_slug diferentes."""

    def setUp(self):
        call_command('bootstrap_roles')
        user_model = get_user_model()

        self.owner = user_model.objects.create_user(
            username='painel-owner', password='x', email='owner@painel.example.com',
        )
        self.owner.groups.add(Group.objects.get(name=ROLE_OWNER))

        self.manager = user_model.objects.create_user(
            username='painel-manager', password='x', email='manager@painel.example.com',
        )
        self.manager.groups.add(Group.objects.get(name=ROLE_MANAGER))

        self.reception = user_model.objects.create_user(
            username='painel-recepcao', password='x', email='recepcao@painel.example.com',
        )
        self.reception.groups.add(Group.objects.get(name=ROLE_RECEPTION))

        self.coach = user_model.objects.create_user(
            username='painel-coach', password='x', email='coach@painel.example.com',
        )
        self.coach.groups.add(Group.objects.get(name=ROLE_COACH))

        self.client.force_login(self.owner)

    def test_four_distinct_roles_resolve_to_four_distinct_slugs(self):
        from access.roles import get_user_role

        # Recarrega do banco (get_user_role usa cache de instância — objetos
        # frescos garantem que estamos lendo o Membership sincronizado, não
        # um cache de um objeto Python anterior à atribuição do Group).
        user_model = get_user_model()
        users = [
            user_model.objects.get(pk=self.owner.pk),
            user_model.objects.get(pk=self.manager.pk),
            user_model.objects.get(pk=self.reception.pk),
            user_model.objects.get(pk=self.coach.pk),
        ]

        slugs = {getattr(get_user_role(u), 'slug', None) for u in users}

        self.assertEqual(
            len(slugs), 4,
            f'esperava 4 role_slug distintos, resolveu {slugs}',
        )
        self.assertEqual(slugs, {ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION, ROLE_COACH})

    def test_overview_page_renders_all_four_role_labels(self):
        response = self.client.get(reverse('access-overview') + '?manage_profiles=1')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'painel-owner')
        self.assertContains(response, 'painel-manager')
        self.assertContains(response, 'painel-recepcao')
        self.assertContains(response, 'painel-coach')
