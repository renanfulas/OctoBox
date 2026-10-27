import logging
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from shared_support.bulk_executor import execute_bulk_action
from shared_support.decorators import idempotent_action


def test_bulk_action_failure_does_not_log_or_return_exception_text(caplog):
    marker = 'PII-SENTINEL-bulk-error'
    item = SimpleNamespace(pk=17)

    def fail(_item):
        raise RuntimeError(marker)

    with caplog.at_level(logging.WARNING, logger='shared_support.bulk_executor'):
        results = execute_bulk_action([item], fail)

    assert results['failed'][0]['item'] is item
    assert results['failed'][0]['error'] == 'Não foi possível processar este item.'
    assert marker not in caplog.text
    assert 'bulk_action_item_failed error_type=RuntimeError' in caplog.text


def test_idempotency_failure_does_not_log_exception_text(capsys):
    marker = 'PII-SENTINEL-idempotency-error'
    request = SimpleNamespace(
        method='POST',
        headers={'X-Idempotency-Key': 'opaque-test-key'},
        user=SimpleNamespace(is_authenticated=False),
    )

    @idempotent_action
    def fail(_request):
        raise RuntimeError(marker)

    manager = Mock()
    manager.get_or_create.return_value = (SimpleNamespace(), True)
    manager.filter.return_value = manager

    with (
        patch('shared_support.decorators.transaction.atomic', return_value=nullcontext()),
        patch('shared_support.decorators.IdempotencyKey.objects', manager),
        patch('shared_support.decorators.logger.error') as error_log,
        pytest.raises(RuntimeError, match=marker),
    ):
        fail(request)

    error_log.assert_called_once_with('idempotent_action_failed error_type=%s', 'RuntimeError')
    assert marker not in capsys.readouterr().err
    manager.filter.assert_called_once_with(key='opaque-test-key')
    manager.update.assert_called_once_with(locked_at=None)
