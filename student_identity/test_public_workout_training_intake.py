"""
ARQUIVO: testes de PublicWorkoutTrainingIntakeView (/treinos/anamnese).

POR QUE ELE EXISTE:
- diferente das outras views de API deste modulo, esta e' pagina HTML —
  precisa provar que sessao ausente REDIRECIONA pro login (nunca 401 cru),
  e que consentimento ausente re-renderiza o formulario com erro, nunca
  cria linha (mesma trava de TrainingIntakeValidationError em services.py).
"""

from django.test import TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutTrainingProfile

from .public_workout_session import PUBLIC_WORKOUT_SESSION_COOKIE_NAME, build_public_workout_session_value

_VALID_POST_DATA = {
    'goal': 'hypertrophy',
    'physical_restrictions': ['joelho'],
    'physical_restrictions_detail': 'dor leve',
    'training_experience': 'less_than_6_months',
    'days_per_week': '3',
    'training_location': 'full_gym',
    'motivation': 'quero mudar',
    'biggest_difficulty': 'consistencia',
    'consent': 'on',
}


class PublicWorkoutTrainingIntakeViewTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')

    def _login(self):
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=self.account.pk
        )

    def test_get_without_session_redirects_to_login_with_next(self):
        response = self.client.get(reverse('public-workout-training-intake'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('next=/treinos/anamnese', response['Location'])

    def test_post_without_session_redirects_to_login(self):
        response = self.client.post(reverse('public-workout-training-intake'), _VALID_POST_DATA)

        self.assertEqual(response.status_code, 302)
        self.assertIn('next=/treinos/anamnese', response['Location'])
        self.assertFalse(PublicWorkoutTrainingProfile.objects.exists())

    def test_get_with_session_renders_form(self):
        self._login()

        response = self.client.get(reverse('public-workout-training-intake'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Anamnese de treino')

    def test_post_without_consent_does_not_create_profile(self):
        self._login()
        data = {**_VALID_POST_DATA}
        del data['consent']

        response = self.client.post(reverse('public-workout-training-intake'), data)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PublicWorkoutTrainingProfile.objects.exists())

    def test_post_valid_data_creates_profile_with_consent_timestamp(self):
        self._login()

        response = self.client.post(reverse('public-workout-training-intake'), _VALID_POST_DATA)

        self.assertRedirects(response, '/treinos/minha-conta?anamnese=salva', fetch_redirect_response=False)
        profile = PublicWorkoutTrainingProfile.objects.get(account=self.account)
        self.assertEqual(profile.goal, 'hypertrophy')
        self.assertEqual(profile.physical_restrictions, ['joelho'])
        self.assertIsNotNone(profile.consent_ai_processing_at)

    def test_post_invalid_choice_value_re_renders_with_error(self):
        self._login()
        data = {**_VALID_POST_DATA, 'goal': 'algo-que-nao-existe'}

        response = self.client.post(reverse('public-workout-training-intake'), data)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PublicWorkoutTrainingProfile.objects.exists())
