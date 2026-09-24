"""Regression corpus built from the ten daily WOD examples supplied by the coach."""

import json
import os
import pytest
from unittest.mock import patch

from operations.services.wod_paste_freeform_parser import _freeform_should_take_over, parse_weekly_wod_freeform
from operations.services.wod_paste_parser import load_wod_movement_dictionary, parse_weekly_wod_text
from operations.services.wod_slug_resolver import apply_llm_slug_resolution


SUPPLIED_WODS = [
    (
        "example_1_monday",
        """Segunda
Mobilidade
Aquecimento
3x
100 run
5 front squat
6 front lunges
20 v up
Skill
5 rounds
8 back squat 65%
5 rounds
3 thruster saída do rack pesado
4 rounds
1 snatch + 1 ohs
Wod
Amrap 10m
8 Hang snatch
8 t2b
8 ohs""",
    ),
    (
        "example_1_tuesday",
        """Terça
Mobilidade
Aquecimento
3x
30 du
3 shouttle run
8 shoulder press
15 sit up
Skill
6 rounds
2 clean jerk
Até 75%
Wod
Emom 14m
A cada minuto
A 7 clean jerk 60/45
Max bbjo
B Rest""",
    ),
    (
        "example_1_wednesday",
        """Quarta
Mobilidade
Aquecimento
Core
3x
30 russian twist
15 abs anilha
1m prancha
Skill
Emom 12m
A 8 strict hspu
B 12 rosca direta
C 15 v up plate
Wod
Amrap 15m duplas
200 run juntos
40 kbs A
100 run juntos
10 push up sincro
5 burpees sincro""",
    ),
    (
        "example_1_thursday",
        """Quinta
Mobilidade
Aquecimento
3x
8 bom dia
10 Back lunges
10 Hollow rock
Skill
5 rounds
5 deadlift 70%
Emom 6m
1 Hang squat clean + 1 front
Wod 14m
4 rounds
5 bmu / 10 pull up
5 clean 80/65 kg
5 devil press
50 du""",
    ),
    (
        "example_1_friday_hyrox",
        """Sexta
Mobilidade
Hyrox
800 run
60m lunges bg
800 run
60m BBJ
800 run
80 wall ball
800 run
50m sled push
800 run
60 step box""",
    ),
    (
        "example_2_monday",
        """Segunda
Alongar bem
Aquecimento
3x
8 Back squat
8 Back lunges
100 run
Skill
Força
6 rounds
4 front squat 75%
4 rounds
6 Deadlift
Cap 16m
4 rounds
10-8-6-4 hang snatch
8 ohs
300 run""",
    ),
    (
        "example_2_tuesday",
        """Terça
Alongar bem
3x
10 v up
8 clean
8 shoulder press
8 push up
Skill
5 rounds
2 Hang clean
3 jerk
Emom 5m
1 clean jerk 100%
Amrap 12m
50 DU
10 Hang squat clean
15 hspu""",
    ),
    (
        "example_2_wednesday",
        """Quarta
Alongar bem
3x
6/6 militar press
8/8 remada kb
20 kbs
Skill
Técnica
SC- rope climb
Rx
9 rounds
Cada 1’30
A) 1 Leg Less
1 rope climb
B) 12 pistol
C) 20 v up plate
Cap 18m
4 rounds
40 du
8 Pull Up
15 Push up
15m oh lunges db
Rest 1’""",
    ),
    (
        "example_2_thursday",
        """Quinta
Alongar bem
3x
8 muscle snatch
8 ohs
15 sit up
40 su
Skill
6 rounds
2 squat snatch
4 rounds
Emom
A) 40 du
B) 8 Power snatch
C) 10 BBJO
D) 7 C2b + 7 t2b
E) rest""",
    ),
    (
        "example_2_friday_hyrox",
        """Sexta
Mobilidade
Hyrox
1 km run
50 kbs A
1km
200m farmers carry
1km
80m lunges bg
1 km
80m burpees b jump
1 km
Sled pull""",
    ),
]


@pytest.mark.parametrize(("case_name", "source_text"), SUPPLIED_WODS, ids=[case[0] for case in SUPPLIED_WODS])
def test_coach_supplied_wod_is_parsed_without_losing_the_day_or_all_movements(case_name, source_text):
    """Each real-world paste produces a usable day for dictionary/Haiku/review processing."""
    parsed = parse_weekly_wod_text(source_text)
    if _freeform_should_take_over(parsed):
        parsed = parse_weekly_wod_freeform(source_text)

    assert len(parsed["days"]) == 1, case_name
    blocks = parsed["days"][0]["blocks"]
    assert blocks, case_name
    movements = [movement for block in blocks for movement in block.get("movements", [])]
    assert movements, f"{case_name} produced no movement records"
    assert all("movement_slug" in movement for movement in movements), case_name

    unknown_names = sorted({movement["movement_label_raw"] for movement in movements if not movement.get("movement_slug")})
    model_no_match = json.dumps({name: {"slug": "", "note": "Sem correspondência segura."} for name in unknown_names})
    with (
        patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only"}, clear=False),
        patch("operations.services.wod_slug_resolver._lookup_learned_aliases", return_value={}),
        patch("operations.services.wod_slug_resolver._call_anthropic", return_value=model_no_match) as haiku_call,
        patch("operations.services.wod_slug_resolver._remember_resolved_aliases"),
    ):
        apply_llm_slug_resolution(parsed, load_wod_movement_dictionary())

    if unknown_names:
        haiku_call.assert_called_once()
        assert parsed["movement_resolution"]["state"] == "haiku_no_match", case_name
        assert parsed["movement_resolution"]["candidate_count"] == len(unknown_names), case_name
    else:
        haiku_call.assert_not_called()
