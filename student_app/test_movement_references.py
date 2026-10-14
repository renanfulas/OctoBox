from unittest.mock import patch

from django.test import SimpleTestCase

from student_app.application.movement_references import (
    lookup_movement_catalog_status,
    lookup_movement_reference_urls,
)


class MovementReferenceLookupTests(SimpleTestCase):
    def test_resolves_legacy_hyphen_slug_without_changing_canonical_key(self):
        with patch('student_app.application.movement_references.MovementLibrary.objects.filter') as lookup:
            lookup.return_value.values_list.return_value = [
                ('back-squat', 'https://example.test/back-squat'),
            ]

            result = lookup_movement_reference_urls({'back_squat'})

        self.assertEqual(result, {'back_squat': 'https://example.test/back-squat'})
        lookup.assert_called_once()
        self.assertEqual(
            lookup.call_args.kwargs['slug__in'],
            {'back_squat', 'back-squat'},
        )

    def test_preserves_missing_reference_as_empty_string(self):
        with patch('student_app.application.movement_references.MovementLibrary.objects.filter') as lookup:
            lookup.return_value.values_list.return_value = [('back-squat', '')]

            result = lookup_movement_reference_urls({'back_squat'})

        self.assertEqual(result, {'back_squat': ''})

    def test_empty_input_does_not_query_database(self):
        with patch('student_app.application.movement_references.MovementLibrary.objects.filter') as lookup:
            self.assertEqual(lookup_movement_reference_urls(set()), {})

        lookup.assert_not_called()


class MovementCatalogStatusTests(SimpleTestCase):
    def test_distinguishes_registered_without_video_from_missing_catalog_entry(self):
        with patch('student_app.application.movement_references.MovementLibrary.objects.filter') as lookup:
            lookup.return_value.values_list.return_value = [('back-squat', '')]

            result = lookup_movement_catalog_status({'back_squat', 'custom_move'})

        self.assertEqual(result['back_squat'], {'is_registered': True, 'demo_video_url': ''})
        self.assertEqual(result['custom_move'], {'is_registered': False, 'demo_video_url': ''})
