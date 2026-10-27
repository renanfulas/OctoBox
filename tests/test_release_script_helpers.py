"""Execute release shell helpers without SSH, root, services or a database."""

import os
import hashlib
from pathlib import Path
import re
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


def bash_path():
    git_bash = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Git/bin/bash.exe'
    executable = str(git_bash) if os.name == 'nt' and git_bash.is_file() else shutil.which('bash')
    if not executable:
        pytest.skip('Bash is required to exercise the release helpers')
    return executable


def shell_function(script_name, name):
    source = (ROOT / 'scripts/linux' / script_name).read_text(encoding='utf-8')
    match = re.search(rf'(?ms)^{name}\(\) \{{\n.*?^\}}', source)
    assert match, f'Missing shell helper: {name}'
    return match.group(0)


@pytest.mark.parametrize('script_name', ('deploy_octobox.sh', 'rollback_octobox.sh'))
def test_write_atomic_initializes_its_path_before_using_it(script_name, tmp_path):
    target = tmp_path / 'release state'
    target.write_text('old-sha\n', encoding='utf-8')
    # Ownership calls are deliberately stubbed; actual write + rename run in
    # a temporary directory. This checks nounset and content, not Linux ACLs.
    script = '\n'.join((
        'set -euo pipefail',
        'chmod() { :; }; chown() { :; }',
        'OCTOBOX_APP_GROUP=test-group',
        shell_function(script_name, 'write_atomic'),
        'write_atomic "$REVIEW_OUTPUT" new-sha',
    ))
    result = subprocess.run(
        [bash_path(), '--noprofile', '--norc', '-s'], input=script, text=True,
        capture_output=True, timeout=15,
        env={**os.environ, 'REVIEW_OUTPUT': target.as_posix()},
    )
    assert result.returncode == 0, result.stderr
    assert target.read_text(encoding='utf-8') == 'new-sha\n'
    assert sorted(path.name for path in tmp_path.iterdir()) == [target.name]


@pytest.mark.parametrize('scenario,expected_code,allows_preparation', (
    ('fresh', 0, True),
    ('active_healthy', 0, False),
    ('active_unhealthy', 1, False),
    ('inactive', 1, False),
    ('incomplete', 1, False),
    ('wrong_sha', 1, False),
    ('damaged_assets', 1, False),
))
def test_existing_release_is_never_prepared_in_place(scenario, expected_code, allows_preparation, tmp_path):
    release = tmp_path / 'release'
    sha = 'a' * 40
    if scenario != 'fresh':
        (release / 'venv/bin').mkdir(parents=True)
        python = release / 'venv/bin/python'
        python.write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
        python.chmod(0o755)
        (release / '.git').write_text('gitdir: synthetic\n', encoding='utf-8')
        (release / 'staticfiles').mkdir()
        asset_bytes = b'{"paths": {}}'
        (release / 'staticfiles/staticfiles.json').write_bytes(asset_bytes)
        manifest_sha = 'b' * 40 if scenario == 'wrong_sha' else sha
        manifest = release / '.release-manifest'
        manifest.write_text(
            f'release_sha={manifest_sha}\nasset_manifest_sha256={hashlib.sha256(asset_bytes).hexdigest()}\n',
            encoding='utf-8',
        )
        if scenario == 'incomplete':
            manifest.unlink()
        if scenario == 'damaged_assets':
            (release / 'staticfiles/staticfiles.json').write_bytes(b'changed')
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    script = '\n'.join((
        'set -euo pipefail',
        'RELEASE_DIR="$REVIEW_RELEASE"',
        f'TARGET_SHA={sha}',
        'current_sha="$TARGET_SHA"',
        'current_release="$(readlink -f "$RELEASE_DIR")"',
        'current_release=""' if scenario == 'inactive' else ':',
        'health_matches() { return ' + ('1' if scenario == 'active_unhealthy' else '0') + '; }',
        shell_function('deploy_octobox.sh', 'guard_existing_release'),
        'guard_existing_release',
        'echo PREPARE_ALLOWED',
    ))
    result = subprocess.run(
        [bash_path(), '--noprofile', '--norc', '-s'], input=script, text=True,
        capture_output=True, timeout=15,
        env={**os.environ, 'REVIEW_RELEASE': release.as_posix()},
    )
    assert result.returncode == expected_code, result.stderr
    assert ('PREPARE_ALLOWED' in result.stdout) == allows_preparation
    after = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    assert after == before


def test_release_guard_runs_before_preparation():
    source = (ROOT / 'scripts/linux/deploy_octobox.sh').read_text(encoding='utf-8')
    guard = source.index('\nguard_existing_release\n')
    for operation in ('git_as_app worktree add', '-m pip install', 'cat > "${RELEASE_DIR}/.release-manifest"'):
        assert guard < source.index(operation)


@pytest.mark.parametrize('had_predecessor', (True, False))
def test_failed_activation_restores_rollback_predecessor(had_predecessor, tmp_path):
    active = tmp_path / 'release-a'
    active.mkdir()
    previous_sha = 'c' * 40
    active_sha = 'a' * 40
    if had_predecessor:
        (tmp_path / 'previous_commit').write_text(previous_sha + '\n', encoding='utf-8')
    source = (ROOT / 'scripts/linux/deploy_octobox.sh').read_text(encoding='utf-8')
    snapshot_start = source.index('\nprevious_commit_present=0\n')
    snapshot_end = source.index('\ncurrent_release=""', snapshot_start)
    assert source.index('flock -n 9') < snapshot_start < source.index('echo "== Activate =="')
    script = '\n'.join((
        'set -euo pipefail',
        'chmod() { :; }; chown() { :; }',
        'systemctl() { :; }; health_matches() { return 0; }',
        # Pointer replacement is stubbed; state files exercise real writes.
        'atomic_symlink() { printf "%s\\n" "$1" > "$CURRENT_LINK"; }',
        'OCTOBOX_APP_GROUP=test-group',
        'CURRENT_LINK="$REVIEW_ROOT/current"',
        'PREVIOUS_FILE="$REVIEW_ROOT/previous_commit"',
        'CURRENT_FILE="$REVIEW_ROOT/current_commit"',
        'DEPLOYED_SHA_FILE="$REVIEW_ROOT/deployed_sha"',
        'DEPLOY_RUN_FILE="$REVIEW_ROOT/deploy_run_id"',
        'current_release="$REVIEW_ROOT/release-a"',
        f'current_sha={active_sha}',
        'current_run_id=activation-a',
        source[snapshot_start:snapshot_end],
        shell_function('deploy_octobox.sh', 'write_atomic'),
        shell_function('deploy_octobox.sh', 'restore_previous_release'),
        # Failed B activation has already made A the recorded predecessor.
        'write_atomic "$PREVIOUS_FILE" "$current_sha"',
        'restore_previous_release',
    ))
    result = subprocess.run(
        [bash_path(), '--noprofile', '--norc', '-s'], input=script, text=True,
        capture_output=True, timeout=15,
        env={**os.environ, 'REVIEW_ROOT': tmp_path.as_posix()},
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / 'current_commit').read_text().strip() == active_sha
    assert (tmp_path / 'deployed_sha').read_text().strip() == active_sha
    assert (tmp_path / 'deploy_run_id').read_text().strip() == 'activation-a'
    if had_predecessor:
        assert (tmp_path / 'previous_commit').read_text().strip() == previous_sha
    else:
        assert not (tmp_path / 'previous_commit').exists()


@pytest.mark.parametrize('script_name,restore_function', (
    ('deploy_octobox.sh', 'restore_previous_release'),
    ('rollback_octobox.sh', 'restore_current_release'),
))
@pytest.mark.parametrize('installed', (True, False))
def test_restoring_release_restarts_installed_worker_on_restored_pointer(script_name, restore_function, installed, tmp_path):
    (tmp_path / 'active-release').mkdir()
    (tmp_path / 'shared/deploy-state').mkdir(parents=True)
    script = '\n'.join((
        'set -euo pipefail',
        'OCTOBOX_APP_HOME="$REVIEW_ROOT"',
        'OCTOBOX_APP_GROUP=test-group',
        'CURRENT_LINK="$REVIEW_ROOT/current"',
        'PREVIOUS_FILE="$REVIEW_ROOT/shared/deploy-state/previous_commit"',
        'CURRENT_FILE="$REVIEW_ROOT/shared/deploy-state/current_commit"',
        'DEPLOYED_SHA_FILE="$REVIEW_ROOT/shared/deploy-state/deployed_sha"',
        'DEPLOY_RUN_FILE="$REVIEW_ROOT/shared/deploy-state/deploy_run_id"',
        'current_release="$REVIEW_ROOT/active-release"',
        'current_sha=original-sha; current_run_id=original-run; target_sha=failed-target',
        'previous_commit_present=0; previous_commit=""',
        f'worker_installed={int(installed)}',
        'chmod() { :; }; chown() { :; }; health_matches() { return 0; }',
        'atomic_symlink() { printf "%s\\n" "$1" > "$CURRENT_LINK"; }',
        'systemctl() { if [[ "$1" == cat ]]; then [[ "$worker_installed" == 1 ]]; return; fi; printf "%s|%s\\n" "$*" "$(cat "$CURRENT_LINK")" >> "$REVIEW_ROOT/services.log"; }',
        shell_function(script_name, 'write_atomic'),
        shell_function(script_name, restore_function),
        restore_function,
    ))
    result = subprocess.run(
        [bash_path(), '--noprofile', '--norc', '-s'], input=script, text=True,
        capture_output=True, timeout=15, env={**os.environ, 'REVIEW_ROOT': tmp_path.as_posix()},
    )
    assert result.returncode == 0, result.stderr
    calls = (tmp_path / 'services.log').read_text().splitlines()
    expected_call = f'restart octobox-public-workout-rest-alerts|{(tmp_path / "active-release").as_posix()}'
    assert (expected_call in calls) == installed


def test_optional_worker_restart_failure_does_not_skip_release_health(tmp_path):
    source = (ROOT / 'scripts/linux/deploy_octobox.sh').read_text(encoding='utf-8')
    activation = source[source.index('echo "== Activate =="'):]
    script = '\n'.join((
        'set -euo pipefail',
        'current_sha=old; TARGET_SHA=new; DEPLOY_RUN_ID=new-run; backup_path=synthetic-backup',
        'RELEASE_DIR=synthetic-release; PREVIOUS_FILE=previous; DEPLOYED_SHA_FILE=deployed',
        'DEPLOY_RUN_FILE=run; CURRENT_FILE=current',
        'write_atomic() { :; }; atomic_symlink() { :; }',
        'restore_previous_release() { echo RESTORED; }',
        'health_matches() { echo HEALTH_CHECKED; return 1; }',
        'systemctl() { if [[ "$1" == restart && "$2" == octobox-public-workout-rest-alerts ]]; then return 1; fi; return 0; }',
        activation,
    ))
    result = subprocess.run(
        [bash_path(), '--noprofile', '--norc', '-s'], input=script,
        text=True, capture_output=True, timeout=15,
    )
    assert result.returncode == 1
    assert 'HEALTH_CHECKED' in result.stdout
    assert 'RESTORED' in result.stdout


def test_failed_first_activation_stops_worker_and_removes_live_state(tmp_path):
    for name in ('current', 'deployed_sha', 'deploy_run_id', 'current_commit'):
        (tmp_path / name).write_text('failed-release\n', encoding='utf-8')
    script = '\n'.join((
        'set -euo pipefail',
        'CURRENT_LINK="$REVIEW_ROOT/current"',
        'PREVIOUS_FILE="$REVIEW_ROOT/previous_commit"',
        'CURRENT_FILE="$REVIEW_ROOT/current_commit"',
        'DEPLOYED_SHA_FILE="$REVIEW_ROOT/deployed_sha"',
        'DEPLOY_RUN_FILE="$REVIEW_ROOT/deploy_run_id"',
        'current_release=""; previous_commit_present=0; previous_commit=""',
        'systemctl() { printf "%s\\n" "$*" >> "$REVIEW_ROOT/services.log"; }',
        shell_function('deploy_octobox.sh', 'restore_previous_release'),
        'restore_previous_release',
    ))
    result = subprocess.run(
        [bash_path(), '--noprofile', '--norc', '-s'], input=script, text=True,
        capture_output=True, timeout=15, env={**os.environ, 'REVIEW_ROOT': tmp_path.as_posix()},
    )
    assert result.returncode == 0, result.stderr
    assert 'stop octobox-public-workout-rest-alerts' in (tmp_path / 'services.log').read_text().splitlines()
    assert sorted(path.name for path in tmp_path.iterdir()) == ['services.log']
