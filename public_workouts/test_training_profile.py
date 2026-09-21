"""
ARQUIVO: testes de PublicWorkoutTrainingProfile + save_training_profile/
get_training_profile/serialize_training_profile/flag_movements_against_restrictions.

POR QUE ELE EXISTE:
- save_training_profile e' a UNICA porta de entrada pra este model —
  precisa provar que consentimento ausente ou valor de escolha invalido
  NUNCA cria/atualiza uma linha (N4/D2 do plano de produto: campo de
  restricao/motivacao pode conter dado de saude sensivel indo pra API da
  Anthropic, exige consentimento explicito).
- flag_movements_against_restrictions e' a heuristica determinista de
  seguranca que reforca o gate de revisao humana — precisa provar que
  aponta candidato quando o slug bate e fica vazia quando nao ha' nada
  pra apontar.
"""

from django.test import SimpleTestCase, TestCase

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutTrainingProfile
from public_workouts.services import (
    TrainingIntakeValidationError,
    flag_movements_against_restrictions,
    get_training_profile,
    save_training_profile,
    serialize_training_profile,
)

_VALID_KWARGS = dict(
    goal='hypertrophy',
    physical_restrictions=['joelho'],
    physical_restrictions_detail='dor leve ao agachar',
    training_experience='less_than_6_months',
    days_per_week=3,
    training_location='full_gym',
    motivation='quero mudar de vida',
    biggest_difficulty='consistencia',
    consent_given=True,
)


class SaveTrainingProfileTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')

    def test_without_consent_raises_and_creates_nothing(self):
        kwargs = {**_VALID_KWARGS, 'consent_given': False}
        with self.assertRaises(TrainingIntakeValidationError):
            save_training_profile(account_id=self.account.pk, **kwargs)
        self.assertFalse(PublicWorkoutTrainingProfile.objects.filter(account=self.account).exists())

    def test_invalid_goal_raises(self):
        kwargs = {**_VALID_KWARGS, 'goal': 'ficar-forte'}
        with self.assertRaises(TrainingIntakeValidationError):
            save_training_profile(account_id=self.account.pk, **kwargs)

    def test_invalid_days_per_week_raises(self):
        kwargs = {**_VALID_KWARGS, 'days_per_week': 8}
        with self.assertRaises(TrainingIntakeValidationError):
            save_training_profile(account_id=self.account.pk, **kwargs)

    def test_invalid_restriction_tag_raises(self):
        kwargs = {**_VALID_KWARGS, 'physical_restrictions': ['cotovelo-de-tenista']}
        with self.assertRaises(TrainingIntakeValidationError):
            save_training_profile(account_id=self.account.pk, **kwargs)

    def test_valid_call_creates_profile_with_consent_timestamp(self):
        profile = save_training_profile(account_id=self.account.pk, **_VALID_KWARGS)

        self.assertEqual(profile.goal, 'hypertrophy')
        self.assertEqual(profile.physical_restrictions, ['joelho'])
        self.assertIsNotNone(profile.consent_ai_processing_at)

    def test_second_call_updates_same_row_not_a_duplicate(self):
        save_training_profile(account_id=self.account.pk, **_VALID_KWARGS)
        updated_kwargs = {**_VALID_KWARGS, 'days_per_week': 5}

        save_training_profile(account_id=self.account.pk, **updated_kwargs)

        self.assertEqual(PublicWorkoutTrainingProfile.objects.filter(account=self.account).count(), 1)
        self.assertEqual(PublicWorkoutTrainingProfile.objects.get(account=self.account).days_per_week, 5)

    def test_get_training_profile_returns_none_when_absent(self):
        self.assertIsNone(get_training_profile(account_id=self.account.pk))

    def test_get_training_profile_returns_saved_profile(self):
        save_training_profile(account_id=self.account.pk, **_VALID_KWARGS)
        profile = get_training_profile(account_id=self.account.pk)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.account_id, self.account.pk)


class SerializeTrainingProfileTests(TestCase):
    def test_serializes_raw_enum_keys_not_display_labels(self):
        account = PublicWorkoutAccount.objects.create(email='raw@example.com')
        profile = save_training_profile(account_id=account.pk, **_VALID_KWARGS)

        serialized = serialize_training_profile(profile)

        self.assertEqual(serialized['goal'], 'hypertrophy')  # chave crua, nunca 'Hipertrofia'
        self.assertEqual(serialized['physical_restrictions'], ['joelho'])
        self.assertEqual(serialized['days_per_week'], 3)


class FlagMovementsAgainstRestrictionsTests(SimpleTestCase):
    _PAYLOAD = {
        'days': [
            {
                'day_id': 'seg',
                'blocks': [
                    {
                        'movements': [
                            {'movement_slug': 'agachamento-livre', 'reference_url': None},
                            {'movement_slug': 'supino-reto', 'reference_url': None},
                        ]
                    }
                ],
            }
        ]
    }

    def test_flags_movement_matching_declared_restriction(self):
        flags = flag_movements_against_restrictions(payload=self._PAYLOAD, physical_restrictions=['joelho'])
        slugs = [f['movement_slug'] for f in flags]
        self.assertIn('agachamento-livre', slugs)

    def test_empty_when_no_restriction_declared(self):
        flags = flag_movements_against_restrictions(payload=self._PAYLOAD, physical_restrictions=[])
        self.assertEqual(flags, [])

    def test_empty_when_restriction_has_no_matching_movement(self):
        flags = flag_movements_against_restrictions(payload=self._PAYLOAD, physical_restrictions=['tornozelo'])
        slugs = [f['movement_slug'] for f in flags]
        self.assertNotIn('supino-reto', slugs)
