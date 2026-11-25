"""Coach de voz do treino guiado: chave do servidor e integridade do pacote de áudio.

O comportamento (o que falar e quando) é coberto em tests/js/curva_guided_voice.test.js.
Aqui: o lançador só oferece a voz com CURVA_COACH_VOICE_ENABLED, e o pacote
publicado tem todos os arquivos e ids que guided-voice.js procura.
"""

import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from public_workouts.models import PublicWorkoutLoginToken
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program
from public_workouts.test_curva_rest_alerts import _student

PACK = Path(settings.BASE_DIR) / 'static' / 'audio' / 'coach' / 'v3'


class CoachVoiceLauncherTest(TestCase):
    def setUp(self):
        from shared_support.platform_cache import platform_cache

        platform_cache.clear()
        publish_program(slug='bruno', payload=build_example_payload())
        account, _ = _student()
        token = PublicWorkoutLoginToken.objects.create(account=account, expires_at=timezone.now() + timedelta(minutes=15))
        self.client.post(reverse('public-workout-login'), {
            'action': 'entrar_link', 'token': str(token.token), 'next': '/renan/bruno',
        })

    @override_settings(CURVA_COACH_VOICE_ENABLED=False)
    def test_off_by_default_the_page_has_no_trace_of_the_voice(self):
        page = self.client.get('/renan/bruno')
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'data-coach-voice')
        self.assertNotContains(page, 'guided-voice.js')

    @override_settings(CURVA_COACH_VOICE_ENABLED=True)
    def test_on_the_launcher_offers_the_toggle_and_points_to_the_pack(self):
        page = self.client.get('/renan/bruno')
        self.assertContains(page, 'data-coach-voice-manifest="/static/audio/coach/v3/manifest.json"')
        self.assertContains(page, 'data-coach-voice-base="/static/audio/coach/v3/"')
        self.assertContains(page, 'data-coach-voice-toggle')
        self.assertContains(page, 'guided-voice.js')
        self.assertContains(page, 'data-guided-count-start')

    @override_settings(CURVA_COACH_VOICE_ENABLED=False, CURVA_COACH_VOICE_PLANS=['bruno'])
    def test_beta_list_turns_the_voice_on_only_for_the_listed_plan(self):
        page = self.client.get('/renan/bruno')
        self.assertContains(page, 'data-coach-voice-toggle')
        self.assertContains(page, 'guided-voice.js')

    @override_settings(CURVA_COACH_VOICE_ENABLED=False, CURVA_COACH_VOICE_PLANS=['andressa-cristina'])
    def test_beta_list_leaves_other_plans_without_the_voice(self):
        page = self.client.get('/renan/bruno')
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'data-coach-voice')
        self.assertNotContains(page, 'guided-voice.js')

    @override_settings(CURVA_COACH_VOICE_ENABLED=False)
    def test_off_the_focus_screen_has_no_count_button(self):
        page = self.client.get('/renan/bruno')
        # "data-guided-count" sozinho casaria com o data-guided-countdown do 3-2-1 do treino.
        self.assertNotContains(page, 'data-guided-count ')
        self.assertNotContains(page, 'data-guided-count-start')


class CoachVoicePackTest(TestCase):
    def setUp(self):
        self.manifest = json.loads((PACK / 'manifest.json').read_text(encoding='utf-8'))

    def test_every_clip_and_the_beep_exist_and_are_not_empty(self):
        files = [clip['file'] for clip in self.manifest['clips'].values()] + [
            self.manifest['beep'], self.manifest['tick'], self.manifest['go']]
        missing = [name for name in files if not (PACK / name).is_file() or (PACK / name).stat().st_size < 1000]
        self.assertEqual(missing, [])

    def test_fallbacks_and_fixed_events_that_the_player_uses_are_present(self):
        clips = self.manifest['clips']
        for event in ('workout_start', 'exercise_start', 'set_prep', 'set_prep_loaded', 'set_feeder', 'set_max',
                      'set_plain', 'set_top_noload', 'load_unknown', 'set_last', 'set_logged', 'superset_next',
                      'workout_end'):
            self.assertTrue(any(key.startswith(f'{event}__v') for key in clips), event)

    def test_every_clip_went_through_transcription_qa(self):
        # build_coach_voice.py --qa: fala sem nota não foi checada (VoiceStudio fora no meio do lote).
        self.assertEqual([key for key, clip in self.manifest['clips'].items() if 'qa' not in clip], [])

    def test_count_covers_every_rep_up_to_thirty_with_the_ids_the_player_uses(self):
        clips = self.manifest['clips']
        for event in ('count_setup_top', 'count_setup_max', 'count_go', 'count_push', 'count_done_top'):
            self.assertTrue(any(key.startswith(f'{event}__v') for key in clips), event)
        for n in (1, 8, 30):
            for variant in range(1, 5):
                self.assertIn(f'count__r{n}_v{variant}', clips)
            for event in ('count_last', 'count_goal', 'count_stop'):
                self.assertIn(f'{event}__r{n}', clips)
        self.assertIn('count_half__r15', clips)
        self.assertIn('count_left2__r28', clips)
        self.assertIn('count_left1__r29', clips)
        self.assertIn('count_safety__r30', clips)
        self.assertIn('count_beyond__r30_v3', clips)

    def test_loads_cover_dumbbells_by_the_kilo_and_barbells_by_two_and_a_half(self):
        clips = self.manifest['clips']
        for kg in ('13', '27', '22_5', '82_5', '300'):
            self.assertIn(f'set_top__kg{kg}', clips)
            self.assertIn(f'load__kg{kg}', clips)
