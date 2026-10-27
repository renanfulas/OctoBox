from pathlib import Path

from django.test import SimpleTestCase
import yaml


class DeployWorkflowSchemaTests(SimpleTestCase):
    def test_ssh_parameters_are_action_inputs_and_release_variables_are_forwarded(self):
        workflow = yaml.safe_load(
            (Path(__file__).resolve().parents[1] / '.github/workflows/deploy-vps.yml').read_text(encoding='utf-8')
        )
        step = next(item for item in workflow['jobs']['deploy']['steps'] if item.get('uses', '').startswith('appleboy/ssh-action@'))
        allowed_step_keys = {'id', 'if', 'name', 'uses', 'run', 'with', 'env', 'working-directory', 'shell', 'continue-on-error', 'timeout-minutes'}
        self.assertFalse(set(step) - allowed_step_keys, 'Action inputs must be nested under with')
        forwarded = set(step['with']['envs'].split(','))
        self.assertEqual(forwarded, {'DEPLOY_TARGET_SHA', 'DEPLOY_RUN_ID'})
        self.assertTrue(forwarded.issubset(step['env']))
