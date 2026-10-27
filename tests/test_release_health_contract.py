import json
from unittest.mock import patch

import pytest
from django.test import RequestFactory


@pytest.mark.django_db
def test_release_health_is_healthy_without_release_metadata():
    from api.v1.views import ApiV1HealthView

    request = RequestFactory().get('/api/v1/health/')
    with (
        patch('api.v1.views.get_deployed_commit_sha', return_value=None),
        patch('api.v1.views.get_loaded_release_sha', return_value=None),
        patch('control.models.Box.objects.filter') as boxes,
    ):
        boxes.return_value.count.return_value = 0
        response = ApiV1HealthView.as_view()(request)

    body = json.loads(response.content)
    assert body['healthy'] is True
    assert body['release_consistent'] is True
    assert body['status'] == 'ok'


@pytest.mark.django_db
def test_release_health_compares_pointer_and_loaded_worker_sha():
    from api.v1.views import ApiV1HealthView

    request = RequestFactory().get('/api/v1/health/')
    with (
        patch('api.v1.views.get_deployed_commit_sha', return_value='a' * 40),
        patch('api.v1.views.get_loaded_release_sha', return_value='a' * 40),
        patch('control.models.Box.objects.filter') as boxes,
    ):
        boxes.return_value.count.return_value = 0
        response = ApiV1HealthView.as_view()(request)

    body = json.loads(response.content)
    assert body['deployed_sha'] == body['loaded_sha'] == 'a' * 40
    assert body['healthy'] is True
    assert body['release_consistent'] is True


@pytest.mark.django_db
def test_release_health_flags_worker_that_loaded_the_previous_release():
    from api.v1.views import ApiV1HealthView

    request = RequestFactory().get('/api/v1/health/')
    with (
        patch('api.v1.views.get_deployed_commit_sha', return_value='b' * 40),
        patch('api.v1.views.get_loaded_release_sha', return_value='a' * 40),
        patch('control.models.Box.objects.filter') as boxes,
    ):
        boxes.return_value.count.return_value = 0
        response = ApiV1HealthView.as_view()(request)

    body = json.loads(response.content)
    assert body['healthy'] is False
    assert body['release_consistent'] is False
    assert body['status'] == 'degraded'
