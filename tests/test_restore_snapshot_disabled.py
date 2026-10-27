import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


def test_retired_snapshot_command_fails_closed():
    with pytest.raises(CommandError, match='está desativado'):
        call_command('restore_snapshot', 'legacy-snapshot.zip')
