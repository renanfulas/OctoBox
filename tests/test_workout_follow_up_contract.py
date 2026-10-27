from django.test import SimpleTestCase

from access.roles import ROLE_MANAGER, ROLE_OWNER
from operations.forms import WorkoutFollowUpResolutionForm


class WorkoutFollowUpContractTests(SimpleTestCase):
    def test_client_label_is_ignored_and_owner_label_is_server_derived(self):
        form = WorkoutFollowUpResolutionForm(
            {
                'action_key': 'desk-follow-up',
                'action_label': 'pessoa.private@example.invalid',
                'result_status': 'completed',
                'outcome_note': '',
            },
            current_role_slug=ROLE_OWNER,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.build_result_payload()['action_label'], 'Acompanhar recepcao')
        self.assertNotIn('action_label', form.cleaned_data)

    def test_manager_label_is_server_derived_and_unknown_action_is_rejected(self):
        form = WorkoutFollowUpResolutionForm(
            {
                'action_key': 'desk-follow-up',
                'action_label': 'label-forjado',
                'result_status': 'completed',
                'outcome_note': '',
            },
            current_role_slug=ROLE_MANAGER,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.build_result_payload()['action_label'], 'Acompanhar operacao agora')

        invalid_form = WorkoutFollowUpResolutionForm(
            {
                'action_key': 'arbitrary-action',
                'action_label': 'pessoa.private@example.invalid',
                'result_status': 'completed',
                'outcome_note': '',
            },
            current_role_slug=ROLE_MANAGER,
        )
        self.assertFalse(invalid_form.is_valid())
