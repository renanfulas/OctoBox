"""
ARQUIVO: fachada/orquestrador dos builders da board de aprovacao do WOD.

POR QUE ELE EXISTE:
- expoe um ponto unico de import para os corredores internos da board sem manter toda a logica no mesmo arquivo.
"""

from .workout_board_management_builders import (
    build_management_alert_priority,
    build_management_recommendations,
    build_operational_leverage_summary,
    build_operational_leverage_trends,
    build_operational_management_alerts,
    build_operational_memory_patterns,
    build_rm_gap_queue,
    build_rm_readiness_management_alerts,
)
from .workout_board_review_builders import (
    build_snapshot_blocks,
    build_snapshot_presentation,
    build_student_preview_diff,
    build_student_preview_payload,
    build_workout_decision_assist,
    build_workout_diff_snapshot,
    normalize_load_type_label,
)
from .workout_board_weekly_builders import (
    build_weekly_checkpoint_maturity,
    build_weekly_checkpoint_rhythm,
    build_weekly_executive_summary,
    build_weekly_governance_action,
)
from .workout_history_tab_builders import (
    build_alerts_context,
    build_checkpoint_context,
    build_published_wods_context,
)
