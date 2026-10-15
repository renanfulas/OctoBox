"""Contratos da extração do catálogo e da política de acesso da Curva."""

import ast
from pathlib import Path
from unittest.mock import patch

from django.http import Http404
from django.test import SimpleTestCase

from public_workouts.catalog import PUBLIC_WORKOUT_LIBRARY, PublicWorkoutPlan
from public_workouts.services import UnknownPlanSlugError, _validate_plan_slug
from student_app.views import public_workout_views
from student_app.views.public_workout_access import _get_public_workout_entry


class PublicWorkoutAccessSplitTests(SimpleTestCase):
    def test_legacy_view_reexports_the_same_catalog_and_access_function(self):
        self.assertIs(public_workout_views.PUBLIC_WORKOUT_LIBRARY, PUBLIC_WORKOUT_LIBRARY)
        self.assertIs(public_workout_views._get_public_workout_entry, _get_public_workout_entry)
        self.assertIsInstance(PUBLIC_WORKOUT_LIBRARY['bruno'], PublicWorkoutPlan)

    def test_services_validates_against_catalog_without_importing_view(self):
        _validate_plan_slug('bruno')
        with self.assertRaises(UnknownPlanSlugError):
            _validate_plan_slug('slug-inexistente')
        source = Path('public_workouts/services.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        imported = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertNotIn('student_app.views.public_workout_views', imported)

    def test_unknown_slug_stays_404_and_published_slug_is_synthesized(self):
        with patch('public_workouts.services.get_active_program', return_value=None):
            with self.assertRaises(Http404):
                _get_public_workout_entry('slug-inexistente')
        with patch('public_workouts.services.get_active_program', return_value=object()):
            plan = _get_public_workout_entry('novo-aluno')
        self.assertEqual(plan.slug, 'novo-aluno')
        self.assertEqual(plan.store_key, 'novo-aluno_v1')

    def test_new_sync_assets_load_before_controllers(self):
        template = Path('templates/public_workouts/workout.html').read_text(encoding='utf-8')
        self.assertLess(template.index('load-sync.js'), template.index('load_tracker.js'))
        self.assertLess(template.index('guided-sync.js'), template.index('workout-guided.js'))
