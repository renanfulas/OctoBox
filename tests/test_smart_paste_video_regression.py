"""Regressions from the coach's 24 September mobile SmartPaste recording."""

import json
from unittest.mock import patch

from operations.forms import WeeklyWodReviewMovementForm
from operations.services.wod_paste_freeform_parser import (
    _freeform_should_take_over,
    parse_weekly_wod_freeform,
)
from operations.services.wod_paste_parser import parse_weekly_wod_text
from operations.services.wod_slug_resolver import (
    _call_anthropic,
    _parse_and_validate,
    _resolve_unknown_slugs_with_status,
)


VIDEO_TUESDAY = """Terça
Mobilidade

3 rounds
8 kipping
5 push up
40 du

Emom 8m
A 5 a 8 strict hspu
B 10m shw ou 3 wall walks

Emom 8m
A 6 strict pull up
B 15 Box dips

Wod 12m
5 rounds
15 pull up
25 wall ball"""


def test_video_tuesday_preserves_blocks_and_only_truly_ambiguous_movement():
    canonical = parse_weekly_wod_text(VIDEO_TUESDAY)
    freeform = parse_weekly_wod_freeform(VIDEO_TUESDAY)
    assert _freeform_should_take_over(canonical, freeform)
    day = freeform['days'][0]
    assert len(day['blocks']) == 5
    assert sum(len(block['movements']) for block in day['blocks']) == 10
    unresolved = [
        movement['movement_label_raw']
        for block in day['blocks'] for movement in block['movements']
        if not movement['movement_slug']
    ]
    assert unresolved == ['10m shw']
    alternatives = day['blocks'][2]['movements']
    assert [movement['movement_slug'] for movement in alternatives[-2:]] == [None, 'wall_walk']
    assert alternatives[-1]['is_scaled_alternative']


def test_haiku_indexed_result_preserves_raw_line_and_rejects_unknown_slug():
    result = _parse_and_validate(
        raw_text=json.dumps({'items': [
            {'id': 0, 'slug': 'wall_walk'},
            {'id': 1, 'slug': 'invented_slug'},
            {'id': 99, 'slug': 'wall_walk'},
        ]}),
        valid_slugs={'wall_walk'},
        unrecognized_names=['3 wall walks', '10m shw'],
    )
    assert list(result) == ['3 wall walks']
    assert result['3 wall walks']['slug'] == 'wall_walk'


def test_haiku_handles_long_week_in_a_single_indexed_response():
    names = [f'unknown movement {number}' for number in range(30)]
    calls = []

    def fake_haiku(*, static_block, dynamic_block, api_key):
        items = json.loads(dynamic_block.split('\n', 1)[1])
        calls.append(items)
        return json.dumps({'items': [{'id': item['id'], 'slug': 'run'} for item in items]})

    with (
        patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-only'}, clear=False),
        patch('operations.services.wod_slug_resolver._lookup_learned_aliases', return_value={}),
        patch('operations.services.wod_slug_resolver._remember_resolved_aliases'),
        patch('operations.services.wod_slug_resolver._call_anthropic', side_effect=fake_haiku),
    ):
        resolved, status = _resolve_unknown_slugs_with_status(
            unrecognized_names=names,
            slug_dictionary=[('run', ('run', 'corrida'))],
        )

    assert [len(batch) for batch in calls] == [30]
    assert len(resolved) == 30
    assert status['state'] == 'haiku_resolved'
    assert status['haiku_batch_count'] == 1


def test_truncated_haiku_response_cannot_be_treated_as_a_valid_mapping():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {'stop_reason': 'max_tokens', 'content': [{'type': 'text', 'text': '{"items": ['}]}

    with (
        patch.dict('os.environ', {'ANTHROPIC_WORKSPACE_ID': 'wrkspc_test'}, clear=False),
        patch('operations.services.wod_slug_resolver.requests.post', return_value=Response()) as request,
    ):
        assert _call_anthropic(static_block='dictionary', dynamic_block='items', api_key='test-only') is None
    assert request.call_args.kwargs['headers']['anthropic-workspace-id'] == 'wrkspc_test'
    body = request.call_args.kwargs['json']
    assert body['max_tokens'] >= 1024
    assert body['output_config']['format']['type'] == 'json_schema'


def test_manual_review_rejects_a_partial_slug_and_accepts_custom():
    data = {
        'plan_id': 1, 'day_index': 0, 'block_index': 0, 'movement_index': 0,
        'movement_label_raw': '10m shw', 'movement_slug': 'Kippi',
    }
    choices = [('kipping_swing', ('kipping',))]
    form = WeeklyWodReviewMovementForm(data, slug_choices=choices)
    assert not form.is_valid()
    assert 'movement_slug' in form.errors

    data['movement_slug'] = 'custom'
    form = WeeklyWodReviewMovementForm(data, slug_choices=choices)
    assert form.is_valid(), form.errors
