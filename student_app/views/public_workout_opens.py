"""POST /renan/<slug>/abertura — o app avisa que o aluno abriu o treino.

A página viva já registra a abertura ao renderizar (PublicWorkoutDetailView).
Este endpoint cobre o que o servidor não vê: o app aberto da cópia salva sem
internet (enviado pela fila offline quando a conexão volta) e a volta ao app
que estava em segundo plano. `opened_at` é o horário do aparelho: a abertura
offline das 19h conta como 19h, não como a hora em que sincronizou.
Duplicatas (reenvio, página viva + evento) caem na janela de
record_program_open.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views import View

from student_identity.public_workout_session import get_public_workout_account_id_from_request

from .public_workout_access import _confirm_login_session_owns_slug_or_404, _get_public_workout_entry
from .public_workout_offline_telemetry import log_offline_sync_lag
from .public_workout_request import json_payload

# Relógio do aparelho adiantado é comum; mais que isso não é abertura real.
MAX_CLOCK_AHEAD = timedelta(minutes=5)
# Mesma validade da cópia offline e das leituras salvas (30 dias).
MAX_AGE = timedelta(days=30)


def _opened_at(value) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=dt_timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


class PublicWorkoutProgramOpenView(View):
    http_method_names = ['post']

    def post(self, request, plan_slug, *args, **kwargs):
        from public_workouts.coach_analytics import record_program_open
        from public_workouts.models import PublicWorkoutAccount

        plan = _get_public_workout_entry(plan_slug)
        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'login necessario'}, status=401)
        _confirm_login_session_owns_slug_or_404(request, plan.slug)
        log_offline_sync_lag(request, 'open')
        data = json_payload(request)
        if data is None:
            return HttpResponse(status=400)
        opened_at = _opened_at(data.get('opened_at'))
        now = timezone.now()
        if opened_at is None or opened_at < now - MAX_AGE:
            return JsonResponse({'error': 'opened_at invalido'}, status=400)
        opened_at = min(opened_at, now) if opened_at <= now + MAX_CLOCK_AHEAD else None
        if opened_at is None:
            return JsonResponse({'error': 'opened_at no futuro'}, status=400)
        account = PublicWorkoutAccount.objects.filter(pk=account_id).first()
        if account is None:
            return JsonResponse({'error': 'login necessario'}, status=401)
        opened = record_program_open(
            account=account, plan_slug=plan.slug, user_agent=request.META.get('HTTP_USER_AGENT', ''), at=opened_at,
        )
        return JsonResponse({'ok': True, 'recorded': opened is not None})
