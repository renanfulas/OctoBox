"""
ARQUIVO: testes de integracao do handler apply_smartplan_paste.

POR QUE ELE EXISTE:
- _handle_apply_smartplan_paste e o codigo mais critico da Onda E.1 e o menos
  protegido. Qualquer refatoracao em _hydrate_workout_from_payload,
  route_workout_submission ou no parser precisa quebrar estes testes
  intencionalmente para o autor perceber o impacto.

O QUE ESTE ARQUIVO FAZ:
1. Caminho A: paste canonico -> blocos hidratados, is_normalized=True, publicacao roteada.
2. Caminho B: paste invalido + confirm_raw -> tier cru, blocos antigos removidos.
3. Caminho C: paste invalido sem confirmacao -> popup renderizado, nenhum workout criado.
4. Guardas de borda: paste vazio, usuario nao autenticado.

PONTOS CRITICOS:
- A policy de aprovacao afeta o status final. Os testes usam
  @override_settings(WOD_APPROVAL_POLICY='trusted_template') para publicacao direta
  em path A (SmartPlan e tratado como fonte confiavel sob essa politica).
- Path B nao bypassa trusted_template (source='smartplan_raw') — vai para aprovacao.
- Mudancas no CANONICAL_PAYLOAD exigem rever fixtures aqui.
"""

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_COACH
from operations.models import ClassSession
from student_app.models import (
    SessionWorkout,
    SessionWorkoutBlock,
    SessionWorkoutMovement,
    SessionWorkoutStatus,
    WorkoutBlockKind,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CANONICAL_PAYLOAD = {
    'version': '1.0',
    'blocks': [
        {
            'order': 1,
            'type': 'strength',
            'title': 'Forca principal',
            'duration_min': None,
            'rounds': 5,
            'is_partner': False,
            'is_synchro': False,
            'scaling_notes': '',
            'movements': [
                {
                    'order': 1,
                    'slug': 'deadlift',
                    'label_pt': 'Deadlift',
                    'label_en': 'Deadlift',
                    'reps': 5,
                    'load_kg': None,
                    'load_note': '',
                    'load_pct_rm': 75,
                    'load_pct_rm_exercise': 'deadlift',
                }
            ],
            'warnings': [],
        }
    ],
    'session_warnings': [],
}

INVALID_PASTE = 'AMRAP 12: 30 thruster, 20 hspu, 10 box jump'


def _canonical_paste(payload: dict | None = None) -> str:
    payload_json = json.dumps(payload or CANONICAL_PAYLOAD)
    return (
        '=== WOD NORMALIZADO ===\n'
        'Forca 5x5 Deadlift 75%\n'
        '\n'
        '=== JSON ESTRUTURADO ===\n'
        '```json\n'
        f'{payload_json}\n'
        '```\n'
        '\n'
        '=== FIM ==='
    )


# ---------------------------------------------------------------------------
# Setup base
# ---------------------------------------------------------------------------

class SmartPlanActionTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command('bootstrap_roles', verbosity=0)
        User = get_user_model()
        self.coach = User.objects.create_user('coach-smartplan', password='senha-forte-123')
        self.coach.groups.add(Group.objects.get(name=ROLE_COACH))
        self.session = ClassSession.objects.create(
            title='WOD SmartPlan Test',
            scheduled_at=timezone.now(),
        )
        self.url = reverse('coach-session-workout-editor', kwargs={'session_id': self.session.id})

    def _post(self, data):
        self.client.force_login(self.coach)
        return self.client.post(self.url, data)


# ---------------------------------------------------------------------------
# Caminho A — paste canonico valido
# ---------------------------------------------------------------------------

class SmartPlanPathATests(SmartPlanActionTests):

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_creates_blocks_and_marks_is_normalized(self):
        self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': _canonical_paste()})

        workout = SessionWorkout.objects.get(session=self.session)
        self.assertTrue(workout.is_normalized)
        self.assertEqual(SessionWorkoutBlock.objects.filter(workout=workout).count(), 1)

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_creates_movements_under_block(self):
        self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': _canonical_paste()})

        workout = SessionWorkout.objects.get(session=self.session)
        block = SessionWorkoutBlock.objects.get(workout=workout)
        self.assertEqual(block.kind, WorkoutBlockKind.STRENGTH)
        movement = SessionWorkoutMovement.objects.get(block=block)
        self.assertEqual(movement.movement_slug, 'deadlift')

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_stores_structured_payload_snapshot(self):
        self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': _canonical_paste()})

        workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(len(workout.structured_payload.get('blocks', [])), 1)
        self.assertEqual(workout.structured_payload['blocks'][0]['type'], 'strength')

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_saves_normalized_text_to_coach_notes(self):
        self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': _canonical_paste()})

        workout = SessionWorkout.objects.get(session=self.session)
        self.assertIn('Forca 5x5 Deadlift 75%', workout.coach_notes)

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_publishes_directly_under_trusted_template_policy(self):
        # source='smartplan' bypassa aprovacao sob trusted_template (nossa correcao).
        self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': _canonical_paste()})

        workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(workout.status, SessionWorkoutStatus.PUBLISHED)

    @override_settings(WOD_APPROVAL_POLICY='strict')
    def test_sends_for_approval_under_strict_policy(self):
        self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': _canonical_paste()})

        workout = SessionWorkout.objects.get(session=self.session)
        # Blocos e is_normalized corretos mesmo pendente de aprovacao.
        self.assertTrue(workout.is_normalized)
        self.assertEqual(workout.status, SessionWorkoutStatus.PENDING_APPROVAL)
        self.assertEqual(SessionWorkoutBlock.objects.filter(workout=workout).count(), 1)

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_is_idempotent_on_reapplication(self):
        """Re-aplicar SmartPlan apaga blocos antigos e cria novos sem duplicar."""
        self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': _canonical_paste()})
        self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': _canonical_paste()})

        workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(SessionWorkoutBlock.objects.filter(workout=workout).count(), 1)

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_redirects_to_editor_after_publish(self):
        response = self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': _canonical_paste()})

        self.assertRedirects(response, self.url)


# ---------------------------------------------------------------------------
# Caminho B — paste invalido + confirmacao de publicacao cru
# ---------------------------------------------------------------------------

class SmartPlanPathBTests(SmartPlanActionTests):

    def _post_raw(self, paste=INVALID_PASTE):
        return self._post({
            'intent': 'apply_smartplan_paste',
            'smartplan_paste': paste,
            'confirm_publish_raw': '1',
        })

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_saves_raw_text_to_coach_notes(self):
        self._post_raw()

        workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(workout.coach_notes, INVALID_PASTE)

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_marks_is_normalized_false(self):
        self._post_raw()

        workout = SessionWorkout.objects.get(session=self.session)
        self.assertFalse(workout.is_normalized)

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_does_not_create_blocks(self):
        self._post_raw()

        workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(SessionWorkoutBlock.objects.filter(workout=workout).count(), 0)

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_clears_stale_blocks_from_previous_smartplan(self):
        """Se o coach re-publicar cru apos um SmartPlan anterior, blocos antigos
        devem ser removidos — is_normalized=False sem lixo relacional no banco."""
        # 1. Aplica SmartPlan (cria blocos).
        self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': _canonical_paste()})
        workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(SessionWorkoutBlock.objects.filter(workout=workout).count(), 1)

        # 2. Confirma publicacao cru — blocos antigos devem sumir.
        self._post_raw()
        workout.refresh_from_db()
        self.assertFalse(workout.is_normalized)
        self.assertEqual(SessionWorkoutBlock.objects.filter(workout=workout).count(), 0)

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_submits_for_approval_because_raw_is_not_trusted(self):
        # source='smartplan_raw' NAO bypassa trusted_template — vai para aprovacao.
        self._post_raw()

        workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(workout.status, SessionWorkoutStatus.PENDING_APPROVAL)

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_redirects_to_editor_after_save(self):
        response = self._post_raw()

        self.assertRedirects(response, self.url)


# ---------------------------------------------------------------------------
# Caminho C — paste invalido sem confirmacao (popup)
# ---------------------------------------------------------------------------

class SmartPlanPathCTests(SmartPlanActionTests):

    def test_returns_200_with_popup_markup(self):
        self.client.force_login(self.coach)
        response = self.client.post(self.url, {
            'intent': 'apply_smartplan_paste',
            'smartplan_paste': INVALID_PASTE,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'wod-smartplan-popup')

    def test_does_not_create_workout(self):
        self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': INVALID_PASTE})

        self.assertFalse(SessionWorkout.objects.filter(session=self.session).exists())

    def test_echoes_paste_value_so_coach_does_not_lose_content(self):
        """O texto colado deve aparecer no popup para o coach poder corrigir e re-enviar."""
        self.client.force_login(self.coach)
        response = self.client.post(self.url, {
            'intent': 'apply_smartplan_paste',
            'smartplan_paste': INVALID_PASTE,
        })

        self.assertContains(response, INVALID_PASTE)

    def test_includes_invalid_reason_in_context(self):
        self.client.force_login(self.coach)
        response = self.client.post(self.url, {
            'intent': 'apply_smartplan_paste',
            'smartplan_paste': INVALID_PASTE,
        })

        # O reason 'markers_missing' e traduzido no popup para a mensagem humana.
        # Verificamos o texto renderizado, nao o codigo interno.
        self.assertContains(response, 'marcadores')


# ---------------------------------------------------------------------------
# Guardas de borda
# ---------------------------------------------------------------------------

class SmartPlanEdgeCaseTests(SmartPlanActionTests):

    def test_empty_paste_redirects_with_error_message(self):
        response = self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': ''})

        self.assertRedirects(response, self.url)
        self.assertFalse(SessionWorkout.objects.filter(session=self.session).exists())

    def test_whitespace_only_paste_redirects_with_error(self):
        response = self._post({'intent': 'apply_smartplan_paste', 'smartplan_paste': '   \n   '})

        self.assertRedirects(response, self.url)

    def test_unauthenticated_post_does_not_reach_handler(self):
        response = self.client.post(self.url, {
            'intent': 'apply_smartplan_paste',
            'smartplan_paste': _canonical_paste(),
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(SessionWorkout.objects.filter(session=self.session).exists())
