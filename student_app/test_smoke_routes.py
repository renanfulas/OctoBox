"""
ARQUIVO: smoke tests de roteamento do app do aluno.

POR QUE ELE EXISTE:
- O tests.py legado cobre telas individuais a fundo, mas nao havia um sweep
  sistematico que garantisse que TODA rota `student-app-*` continua wired ao
  backend (sem 500) e que o gating de autenticacao continua de pe.
- Como o sweep descobre as rotas por introspeccao do resolver, rotas novas
  entram automaticamente na cobertura — um smoke a prova de regressao.

O QUE ESTE ARQUIVO TESTA:
1. Nenhuma rota sem-argumento estoura erro de servidor (>=500) para um aluno
   ativo e onboarded — pega imports quebrados, template error e query morta.
2. As telas-nucleo (home, grade, wod, rm, settings, etc.) renderizam 200.
3. Rotas protegidas redirecionam o visitante anonimo para o login do aluno.
4. Os endpoints abertos de PWA (manifest, service worker, offline) respondem
   sem cookie.

PONTO CRITICO:
- Exige PostgreSQL + django-tenants (conftest cria o schema box_test). Em
  SQLite o app do aluno da falso negativo.
"""

from __future__ import annotations

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import NoReverseMatch, get_resolver, reverse

from student_app._test_fixtures import (
    STUDENT_SESSION_COOKIE,
    auth_cookie_value,
    create_onboarded_student,
)


def discover_student_app_route_names():
    """Todos os nomes de rota `student-app-*` registrados no resolver."""
    resolver = get_resolver()
    return sorted(
        name
        for name in resolver.reverse_dict.keys()
        if isinstance(name, str) and name.startswith('student-app-')
    )


class StudentAppRouteSmokeTests(TestCase):
    """Sweep de fumaca: o app inteiro do aluno continua falando com o backend."""

    # Telas GET que devem renderizar 200 para um aluno ativo e onboarded.
    CORE_SCREEN_ROUTES = (
        'student-app-home',
        'student-app-grade',
        'student-app-wod',
        'student-app-workout',
        'student-app-rm',
        'student-app-settings',
        'student-app-membership-pending',
        'student-app-suspended-financial',
        'student-app-no-active-box',
    )

    # Telas/endpoints atras do gating de identidade: anonimo -> login.
    PROTECTED_ROUTES = (
        'student-app-home',
        'student-app-grade',
        'student-app-wod',
        'student-app-rm',
        'student-app-settings',
    )

    # Endpoints abertos do PWA: respondem mesmo sem sessao de aluno.
    OPEN_PWA_ROUTES = (
        'student-app-manifest',
        'student-app-sw',
        'student-app-offline',
    )

    def setUp(self):
        cache.clear()  # evita vazamento de snapshots cacheados entre testes
        self.client = Client()
        self.student, self.identity = create_onboarded_student()
        self.client.cookies[STUDENT_SESSION_COOKIE] = auth_cookie_value(self.identity)

    def test_every_no_arg_route_avoids_server_error_for_authenticated_student(self):
        checked = []
        for name in discover_student_app_route_names():
            try:
                url = reverse(name)
            except NoReverseMatch:
                # Rotas com argumentos (rm-update, session-attendees) sao
                # exercitadas pelos testes dedicados em tests.py.
                continue
            response = self.client.get(url)
            checked.append(name)
            self.assertLess(
                response.status_code,
                500,
                msg=f'{name} ({url}) retornou {response.status_code} (>=500)',
            )
        # Garante que a introspeccao realmente varreu o app (e nao 0 rotas).
        self.assertGreaterEqual(
            len(checked),
            15,
            msg=f'sweep cobriu poucas rotas, algo mudou no urlconf: {checked}',
        )

    def test_core_screens_render_for_authenticated_student(self):
        for name in self.CORE_SCREEN_ROUTES:
            with self.subTest(route=name):
                response = self.client.get(reverse(name))
                self.assertEqual(
                    response.status_code,
                    200,
                    msg=f'{name} retornou {response.status_code}',
                )

    def test_protected_routes_redirect_anonymous_to_student_login(self):
        anonymous = Client()
        login_url = reverse('student-identity-login')
        for name in self.PROTECTED_ROUTES:
            with self.subTest(route=name):
                response = anonymous.get(reverse(name))
                self.assertEqual(
                    response.status_code,
                    302,
                    msg=f'{name} nao redirecionou anonimo (status {response.status_code})',
                )
                self.assertIn(
                    login_url,
                    response.headers.get('Location', ''),
                    msg=f'{name} redirecionou para {response.headers.get("Location")!r}, esperado login',
                )

    def test_open_pwa_routes_serve_without_authentication(self):
        anonymous = Client()
        for name in self.OPEN_PWA_ROUTES:
            with self.subTest(route=name):
                response = anonymous.get(reverse(name))
                self.assertEqual(
                    response.status_code,
                    200,
                    msg=f'{name} retornou {response.status_code} sem cookie',
                )
