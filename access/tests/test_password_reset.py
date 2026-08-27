"""
ARQUIVO: testes da recuperacao de senha do funcionario.

POR QUE ELE EXISTE:
- O fluxo mexe em credencial de staff: cada garantia aqui e uma porta que fica fechada.

O QUE ESTE ARQUIVO FAZ:
1. Cobre as 4 telas e o despacho pelo gateway de e-mail do projeto.
2. Trava as propriedades de seguranca: nao-enumeracao, single-use, expiracao.
3. Cobre a saida de emergencia do gestor (senha provisoria) e suas travas.

PONTOS CRITICOS:
- `send_html_email` e mockado no namespace de access.password_reset (onde foi
  importado), nao em signup.email_sender — patch no modulo de origem nao pega.
- A propriedade "nao revela se o e-mail existe" e testada comparando as DUAS
  respostas (existente vs inexistente): status e destino tem que bater.
- `cache.clear()` no setUp e OBRIGATORIO: /login/senha/ cai no rate limit de
  scope 'login' (8 POST / 5 min por IP) e o LocMemCache e compartilhado entre
  os testes do processo. Sem o clear, o 9o POST da suite volta 429.
"""

import re
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from access.access_profile_actions import build_provisional_password
from access.roles import ROLE_OWNER


CONFIRM_URL_PATTERN = re.compile(r'/login/senha/redefinir/(?P<uidb64>[^/]+)/(?P<token>[^/\s]+)/')


class StaffPasswordResetFlowTests(TestCase):
    """Fluxo feliz e propriedades de seguranca do reset por e-mail."""

    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username='recepcao.ana',
            password='senha-antiga-123',
            email='ana@boxexemplo.com.br',
        )

    def _request_reset(self, email):
        return self.client.post(reverse('password-reset'), data={'email': email})

    def _extract_confirm_path(self, send_mock):
        """Le o link de confirmacao do corpo de texto que foi despachado."""
        self.assertTrue(send_mock.called, 'nenhum e-mail foi despachado')
        text_body = send_mock.call_args.kwargs['text_body']
        match = CONFIRM_URL_PATTERN.search(text_body)
        self.assertIsNotNone(match, f'link de confirmacao ausente no corpo:\n{text_body}')
        return match.group(0)

    # ------------------------------------------------------------------
    # entrada
    # ------------------------------------------------------------------

    def test_login_page_offers_password_recovery(self):
        response = self.client.get(reverse('login-staff'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('password-reset'))
        self.assertContains(response, 'Esqueci minha senha')

    def test_request_page_renders(self):
        response = self.client.get(reverse('password-reset'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Esqueci minha senha')

    # ------------------------------------------------------------------
    # despacho
    # ------------------------------------------------------------------

    @patch('access.password_reset.send_html_email')
    def test_known_email_dispatches_through_project_gateway(self, send_mock):
        response = self._request_reset('ana@boxexemplo.com.br')

        self.assertRedirects(response, reverse('password-reset-sent'))
        self.assertEqual(send_mock.call_count, 1)
        self.assertEqual(send_mock.call_args.kwargs['to_email'], 'ana@boxexemplo.com.br')
        # HTML e texto sao obrigatorios: cliente legacy sem HTML tem que ler algo.
        self.assertTrue(send_mock.call_args.kwargs['text_body'].strip())
        self.assertIn('<!doctype html>', send_mock.call_args.kwargs['html_body'].lower())

    @patch('access.password_reset.send_html_email')
    def test_email_identifies_which_account_it_belongs_to(self, send_mock):
        self._request_reset('ana@boxexemplo.com.br')

        self.assertIn('recepcao.ana', send_mock.call_args.kwargs['text_body'])
        self.assertIn('recepcao.ana', send_mock.call_args.kwargs['html_body'])
        self.assertIn('recepcao.ana', send_mock.call_args.kwargs['subject'])

    @patch('access.password_reset.send_html_email')
    def test_unknown_email_is_indistinguishable_from_known_email(self, send_mock):
        known = self._request_reset('ana@boxexemplo.com.br')
        send_mock.reset_mock()
        unknown = self._request_reset('ninguem@boxexemplo.com.br')

        self.assertEqual(unknown.status_code, known.status_code)
        self.assertEqual(unknown['Location'], known['Location'])
        self.assertFalse(send_mock.called)

    @patch('access.password_reset.send_html_email')
    def test_inactive_user_gets_no_link(self, send_mock):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])

        response = self._request_reset('ana@boxexemplo.com.br')

        self.assertRedirects(response, reverse('password-reset-sent'))
        self.assertFalse(send_mock.called)

    @patch('access.password_reset.send_html_email')
    def test_shared_email_sends_one_message_per_account(self, send_mock):
        """auth.User.email nao e unique: cada conta precisa do proprio link."""
        get_user_model().objects.create_user(
            username='gestor.ana',
            password='senha-antiga-456',
            email='ana@boxexemplo.com.br',
        )

        self._request_reset('ana@boxexemplo.com.br')

        self.assertEqual(send_mock.call_count, 2)
        usernames_citados = {
            username
            for call in send_mock.call_args_list
            for username in ('recepcao.ana', 'gestor.ana')
            if username in call.kwargs['text_body']
        }
        self.assertEqual(usernames_citados, {'recepcao.ana', 'gestor.ana'})

    @patch('access.password_reset.send_html_email', side_effect=RuntimeError('resend caiu'))
    def test_delivery_failure_does_not_leak_to_the_screen(self, send_mock):
        """Gateway fora do ar nao pode virar 500 nem oraculo de e-mail valido."""
        response = self._request_reset('ana@boxexemplo.com.br')

        self.assertRedirects(response, reverse('password-reset-sent'))

    # ------------------------------------------------------------------
    # consumo do link
    # ------------------------------------------------------------------

    @patch('access.password_reset.send_html_email')
    def test_link_lets_user_set_a_new_password(self, send_mock):
        self._request_reset('ana@boxexemplo.com.br')
        confirm_path = self._extract_confirm_path(send_mock)

        landing = self.client.get(confirm_path)
        self.assertEqual(landing.status_code, 302)

        form_page = self.client.get(landing['Location'])
        self.assertEqual(form_page.status_code, 200)
        self.assertTrue(form_page.context['validlink'])

        response = self.client.post(
            landing['Location'],
            data={'new_password1': 'Senha-Nova-Forte-99', 'new_password2': 'Senha-Nova-Forte-99'},
        )
        self.assertRedirects(response, reverse('password-reset-complete'))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Senha-Nova-Forte-99'))

    @patch('access.password_reset.send_html_email')
    def test_link_dies_after_the_password_changes(self, send_mock):
        """Single-use por construcao: o token assina o hash da senha atual."""
        self._request_reset('ana@boxexemplo.com.br')
        confirm_path = self._extract_confirm_path(send_mock)

        landing = self.client.get(confirm_path)
        self.client.post(
            landing['Location'],
            data={'new_password1': 'Senha-Nova-Forte-99', 'new_password2': 'Senha-Nova-Forte-99'},
        )

        replay = self.client.get(confirm_path)
        self.assertEqual(replay.status_code, 200)
        self.assertFalse(replay.context['validlink'])

    @patch('access.password_reset.send_html_email')
    def test_expired_link_is_refused(self, send_mock):
        """Adianta o relogio do gerador em vez de zerar PASSWORD_RESET_TIMEOUT.

        Com timeout=0 o token gerado no mesmo segundo AINDA passa (a checagem e
        `agora - ts > timeout`, e 0 > 0 e falso). Empurrar o relogio na hora da
        conferencia e o unico jeito deterministico de provar a expiracao.
        """
        self._request_reset('ana@boxexemplo.com.br')
        confirm_path = self._extract_confirm_path(send_mock)

        expirado_em = datetime.now() + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT + 60)
        with patch.object(PasswordResetTokenGenerator, '_now', return_value=expirado_em):
            expired = self.client.get(confirm_path)

        self.assertEqual(expired.status_code, 200)
        self.assertFalse(expired.context['validlink'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('senha-antiga-123'))

    @patch('access.password_reset.send_html_email')
    def test_setting_a_new_password_does_not_log_the_user_in(self, send_mock):
        """post_reset_login=False: provar acesso ao e-mail nao e provar a conta."""
        self._request_reset('ana@boxexemplo.com.br')
        confirm_path = self._extract_confirm_path(send_mock)
        landing = self.client.get(confirm_path)

        self.client.post(
            landing['Location'],
            data={'new_password1': 'Senha-Nova-Forte-99', 'new_password2': 'Senha-Nova-Forte-99'},
        )

        complete = self.client.get(reverse('password-reset-complete'))
        self.assertFalse(complete.context['user'].is_authenticated)

    def test_tampered_token_is_refused(self):
        response = self.client.get(
            reverse('password-reset-confirm', kwargs={'uidb64': 'MQ', 'token': 'aaaaaa-bbbbbbbbbbbbbbbbbbbbbb'})
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['validlink'])

    # ------------------------------------------------------------------
    # abuso
    # ------------------------------------------------------------------

    @override_settings(LOGIN_RATE_LIMIT_MAX_REQUESTS=3, LOGIN_RATE_LIMIT_WINDOW_SECONDS=300)
    @patch('access.password_reset.send_html_email')
    def test_reset_requests_are_throttled_like_login(self, send_mock):
        """A rota mora sob /login/ justamente para herdar o throttle de scope 'login'.

        Sem isso, /login/senha/ seria um gerador de e-mail gratuito para
        qualquer IP — spam no funcionario e custo no gateway.
        """
        for _ in range(3):
            self.assertEqual(self._request_reset('ana@boxexemplo.com.br').status_code, 302)

        blocked = self._request_reset('ana@boxexemplo.com.br')

        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(send_mock.call_count, 3)


class ProvisionalPasswordTests(TestCase):
    """Gerador da senha provisoria usada pelo gestor."""

    def test_avoids_ambiguous_characters(self):
        # 0/O e 1/l/I fora: a senha e lida em voz alta no balcao.
        gerados = ''.join(build_provisional_password() for _ in range(50))

        self.assertFalse(set(gerados) & set('0O1lI'))

    def test_is_not_predictable(self):
        amostras = {build_provisional_password() for _ in range(50)}

        self.assertEqual(len(amostras), 50)


class ManagerPasswordResetTests(TestCase):
    """Saida de emergencia: gestor redefine a senha de quem nao tem e-mail."""

    def setUp(self):
        cache.clear()
        call_command('bootstrap_roles')
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username='owner.box',
            password='senha-owner-123',
            email='owner@boxexemplo.com.br',
        )
        self.owner.groups.add(Group.objects.get(name=ROLE_OWNER))
        self.funcionario = user_model.objects.create_user(
            username='recepcao.sem.email',
            password='senha-antiga-123',
        )
        self.client.force_login(self.owner)

    def _reset(self, target_id):
        return self.client.post(
            reverse('access-overview'),
            data={'access_action': 'reset_password', 'target_profile_id': target_id},
        )

    def test_manager_can_issue_a_provisional_password(self):
        response = self._reset(self.funcionario.pk)

        self.assertRedirects(response, reverse('access-overview'))
        self.funcionario.refresh_from_db()
        self.assertFalse(self.funcionario.check_password('senha-antiga-123'))

        mensagem = ' '.join(str(m) for m in get_messages(response.wsgi_request))
        self.assertIn('recepcao.sem.email', mensagem)
        # A senha exibida tem que ser a que de fato ficou valendo.
        senha_exibida = mensagem.split('recepcao.sem.email: ', 1)[1].split(' ', 1)[0]
        self.assertTrue(self.funcionario.check_password(senha_exibida))

    def test_reset_is_audited_without_leaking_the_password(self):
        from auditing.models import AuditEvent

        response = self._reset(self.funcionario.pk)

        mensagem = ' '.join(str(m) for m in get_messages(response.wsgi_request))
        senha_exibida = mensagem.split('recepcao.sem.email: ', 1)[1].split(' ', 1)[0]

        evento = AuditEvent.objects.filter(action='access_profile_password_reset').first()
        self.assertIsNotNone(evento, 'reset de credencial tem que deixar trilha')
        self.assertEqual(evento.actor_id, self.owner.pk)
        self.assertIn('recepcao.sem.email', evento.description)
        # A senha em claro nao pode vazar para a trilha.
        self.assertNotIn(senha_exibida, evento.description)
        self.assertNotIn(senha_exibida, str(evento.metadata))

    def test_manager_cannot_reset_their_own_password(self):
        response = self._reset(self.owner.pk)

        self.assertRedirects(response, reverse('access-overview'))
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password('senha-owner-123'))

    def test_unknown_profile_is_rejected(self):
        response = self._reset(999999)

        self.assertRedirects(response, reverse('access-overview'))

    def test_non_manager_role_cannot_reset(self):
        user_model = get_user_model()
        coach = user_model.objects.create_user(
            username='coach.box',
            password='senha-coach-123',
            email='coach@boxexemplo.com.br',
        )
        # Onda 1c: Membership.role agora e autoritativo (nao so Group). O
        # fixture de teste (conftest._auto_membership_for_test_users) da
        # Membership(role=OWNER) por padrao a todo user — atribuir o Group
        # Coach aqui sincroniza o Membership.role para 'coach' via
        # m2m_changed, senao este user seria Owner e o teste não provaria
        # nada sobre restricao de papel.
        coach.groups.add(Group.objects.get(name='Coach'))
        self.client.force_login(coach)

        response = self._reset(self.funcionario.pk)

        self.assertRedirects(response, reverse('access-overview'))
        self.funcionario.refresh_from_db()
        self.assertTrue(self.funcionario.check_password('senha-antiga-123'))

    def test_provisional_password_kills_a_pending_email_link(self):
        """Reset presencial cancela o reset por e-mail que estava em voo."""
        self.funcionario.email = 'sem-email-antes@boxexemplo.com.br'
        self.funcionario.save(update_fields=['email'])

        with patch('access.password_reset.send_html_email') as send_mock:
            self.client.post(
                reverse('password-reset'),
                data={'email': 'sem-email-antes@boxexemplo.com.br'},
            )
            text_body = send_mock.call_args.kwargs['text_body']
        confirm_path = CONFIRM_URL_PATTERN.search(text_body).group(0)

        self.client.force_login(self.owner)
        self._reset(self.funcionario.pk)

        replay = self.client.get(confirm_path)
        self.assertEqual(replay.status_code, 200)
        self.assertFalse(replay.context['validlink'])


class AccessProfileEmailRequirementTests(TestCase):
    """E-mail virou obrigatorio: sem ele nao existe auto-recuperacao."""

    def setUp(self):
        cache.clear()
        call_command('bootstrap_roles')
        self.owner = get_user_model().objects.create_user(
            username='owner.email',
            password='senha-owner-123',
            email='owner.email@boxexemplo.com.br',
        )
        self.owner.groups.add(Group.objects.get(name=ROLE_OWNER))
        self.client.force_login(self.owner)

    def test_creating_a_profile_without_email_is_refused(self):
        response = self.client.post(
            reverse('access-overview'),
            data={
                'access_action': 'create',
                'full_name': 'Sem Email',
                'username': 'sem.email',
                'email': '',
                'password': 'Senha-temporaria-123',
                'role': ROLE_OWNER,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='sem.email').exists())

    def test_creating_a_profile_with_email_still_works(self):
        response = self.client.post(
            reverse('access-overview'),
            data={
                'access_action': 'create',
                'full_name': 'Com Email',
                'username': 'com.email',
                'email': 'com.email@boxexemplo.com.br',
                'password': 'Senha-temporaria-123',
                'role': ROLE_OWNER,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user_model().objects.filter(username='com.email').exists())
