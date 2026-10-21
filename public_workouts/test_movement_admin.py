"""
ARQUIVO: testes do admin de PublicWorkoutMovement (Onda A0 do CORDA).

POR QUE ELE EXISTE:
- a tela existe pra revisar as 82 sugestoes de movement_pattern (extraidas
  do HTML legado) sem depender de shell/SQL direto — vale testar o
  comportamento customizado (link do MuscleWiki, acao de promover em
  lote), nao so a config declarativa.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutMovement, PublicWorkoutMovementModality


def _make_movement(slug='barbell-squat', movement_pattern='squat', status='pending', reference_url=''):
    return PublicWorkoutMovement.objects.create(
        slug=slug,
        label_pt='Agachamento livre',
        modality=PublicWorkoutMovementModality.STRENGTH,
        movement_pattern=movement_pattern,
        status=status,
        reference_url=reference_url,
    )


class PublicWorkoutMovementAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='senha-forte-123',
        )
        self.client.force_login(self.superuser)

    def test_changelist_loads_and_lists_pending_movements(self):
        _make_movement()

        response = self.client.get(reverse('admin:public_workouts_publicworkoutmovement_changelist'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'barbell-squat')

    def test_reference_link_renders_anchor_when_url_present(self):
        movement = _make_movement(reference_url='https://musclewiki.com/exercise/barbell-squat')

        response = self.client.get(reverse('admin:public_workouts_publicworkoutmovement_changelist'))

        self.assertContains(response, 'href="https://musclewiki.com/exercise/barbell-squat"')

    def test_reference_link_shows_dash_when_url_missing(self):
        _make_movement(reference_url='')

        response = self.client.get(reverse('admin:public_workouts_publicworkoutmovement_changelist'))

        self.assertContains(response, '—')

    def test_promote_to_active_action_updates_status(self):
        movement = _make_movement(status='pending')

        response = self.client.post(
            reverse('admin:public_workouts_publicworkoutmovement_changelist'),
            data={
                'action': 'promote_to_active',
                '_selected_action': [str(movement.pk)],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        movement.refresh_from_db()
        self.assertEqual(movement.status, 'active')

    def test_promote_to_active_does_not_touch_unselected_rows(self):
        selected = _make_movement(slug='barbell-squat', status='pending')
        other = _make_movement(slug='barbell-bench-press', status='pending')

        self.client.post(
            reverse('admin:public_workouts_publicworkoutmovement_changelist'),
            data={
                'action': 'promote_to_active',
                '_selected_action': [str(selected.pk)],
            },
            follow=True,
        )

        other.refresh_from_db()
        self.assertEqual(other.status, 'pending')

    def test_movement_pattern_and_status_are_list_editable(self):
        movement = _make_movement(movement_pattern='squat', status='pending')

        response = self.client.post(
            reverse('admin:public_workouts_publicworkoutmovement_changelist'),
            data={
                'form-TOTAL_FORMS': '1',
                'form-INITIAL_FORMS': '1',
                'form-MIN_NUM_FORMS': '0',
                'form-MAX_NUM_FORMS': '1000',
                'form-0-id': str(movement.pk),
                'form-0-label_pt': movement.label_pt,
                'form-0-movement_pattern': 'hip-hinge',
                'form-0-status': 'active',
                '_save': 'Save',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        movement.refresh_from_db()
        self.assertEqual(movement.movement_pattern, 'hip-hinge')
        self.assertEqual(movement.status, 'active')
