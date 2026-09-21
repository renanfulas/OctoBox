"""
ARQUIVO: testes de GET /aluno/consultoria/ (Onda B3, resto do item 5 —
docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- ponte entre aluno de box (StudentIdentity, tenant) e conta do corredor
  (PublicWorkoutAccount, schema public) — precisa provar que o
  get_or_create por e-mail nao duplica, nunca sobrescreve
  student_identity_id de conta ja existente, e concede sessao do
  corredor so quando ha assinatura ativa pra redirecionar.
"""

from types import SimpleNamespace

from django.test import TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription
from student_app._test_fixtures import STUDENT_SESSION_COOKIE, auth_cookie_value, create_onboarded_student
from student_identity.public_workout_session import get_public_workout_account_id_from_request


class StudentPublicWorkoutLinkViewTests(TestCase):
    def _url(self):
        return reverse('student-app-consultoria')

    def test_requires_box_login(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_creates_account_and_redirects_when_subscription_exists(self):
        student, identity = create_onboarded_student(email='aluno@example.com')
        self.client.cookies[STUDENT_SESSION_COOKIE] = auth_cookie_value(identity)
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com', student_identity_id=identity.id)
        PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/renan/bruno')
        self.assertEqual(PublicWorkoutAccount.objects.count(), 1)

    def test_grants_corridor_session_cookie_on_redirect(self):
        student, identity = create_onboarded_student(email='aluno@example.com')
        self.client.cookies[STUDENT_SESSION_COOKIE] = auth_cookie_value(identity)
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com', student_identity_id=identity.id)
        PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')

        response = self.client.get(self._url())

        raw_cookies = {name: morsel.value for name, morsel in response.cookies.items()}
        cookie_account_id = get_public_workout_account_id_from_request(
            SimpleNamespace(COOKIES=raw_cookies)
        )
        self.assertEqual(cookie_account_id, account.pk)

    def test_creates_public_workout_account_when_none_exists_yet(self):
        student, identity = create_onboarded_student(email='novo@example.com')
        self.client.cookies[STUDENT_SESSION_COOKIE] = auth_cookie_value(identity)

        self.assertEqual(PublicWorkoutAccount.objects.count(), 0)

        response = self.client.get(self._url())

        account = PublicWorkoutAccount.objects.get(email='novo@example.com')
        self.assertEqual(account.student_identity_id, identity.id)
        # sem assinatura ainda -- nao ha pra onde redirecionar
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'consultoria ativa', response.content)

    def test_does_not_duplicate_or_overwrite_existing_account(self):
        # Conta ja existia (ex.: criada via /treinos/login antes do aluno
        # nunca ter passado por aqui) com student_identity_id diferente --
        # get_or_create nunca deve sobrescrever isso na resolucao por e-mail.
        student, identity = create_onboarded_student(email='aluno@example.com')
        self.client.cookies[STUDENT_SESSION_COOKIE] = auth_cookie_value(identity)
        existing = PublicWorkoutAccount.objects.create(email='aluno@example.com', student_identity_id=999999)

        self.client.get(self._url())

        existing.refresh_from_db()
        self.assertEqual(PublicWorkoutAccount.objects.count(), 1)
        self.assertEqual(existing.student_identity_id, 999999)

    def test_no_subscription_returns_informative_page_not_error(self):
        student, identity = create_onboarded_student(email='aluno@example.com')
        self.client.cookies[STUDENT_SESSION_COOKIE] = auth_cookie_value(identity)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'consultoria ativa', response.content)
