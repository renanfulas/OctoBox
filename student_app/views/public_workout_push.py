"""Inscrição Web Push do aluno Curva, isolada dos comandos de treino."""

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views import View

from student_identity.public_workout_session import (
    get_public_workout_account_id_from_request,
    get_verified_public_workout_account_id_from_request,
)
from student_app.views.public_workout_request import json_payload
from student_app.views.public_workout_access import (
    _confirm_login_session_owns_slug_or_404,
    _get_public_workout_entry,
)

from public_workouts.models import PublicWorkoutPushSubscription
from public_workouts.outbox import TOPIC_PUSH_WELCOME, enqueue_outbox
from public_workouts.push import configured, subscribe
from public_workouts import rest_alerts


def _verified_account(request, plan_slug):
    """(plano, conta, erro): o push exige identidade verificada, não a posse do link."""
    plan = _get_public_workout_entry(plan_slug)
    account_id = get_verified_public_workout_account_id_from_request(request)
    if account_id is None:
        return plan, None, JsonResponse({'error': 'login necessario'}, status=401)
    _confirm_login_session_owns_slug_or_404(request, plan.slug)
    return plan, account_id, None


class PublicWorkoutPushSubscriptionView(View):
    http_method_names = ['post', 'delete']

    def _account(self, request, plan_slug):
        _plan, account_id, error = _verified_account(request, plan_slug)
        return account_id, error

    def post(self, request, plan_slug, *args, **kwargs):
        account_id, error = self._account(request, plan_slug)
        if error:
            return error
        if not configured():
            return JsonResponse({'error': 'push-not-configured'}, status=503)
        data = json_payload(request)
        if data is None:
            return HttpResponse(status=400)
        try:
            with transaction.atomic():
                row = subscribe(
                    account_id=account_id, data=data.get('subscription'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )
                enqueue_outbox(
                    topic=TOPIC_PUSH_WELCOME, aggregate_type='push_subscription',
                    aggregate_id=row.pk, version=1, payload={'plan_slug': plan_slug},
                )
        except (ValueError, TypeError):
            return JsonResponse({'error': 'invalid-subscription'}, status=400)
        return JsonResponse({'ok': True, 'subscription_id': row.pk})

    def delete(self, request, plan_slug, *args, **kwargs):
        account_id, error = self._account(request, plan_slug)
        if error:
            return error
        data = json_payload(request)
        endpoint = str((data or {}).get('endpoint') or '').strip()
        if endpoint:
            PublicWorkoutPushSubscription.objects.filter(
                account_id=account_id, endpoint=endpoint, revoked_at__isnull=True,
            ).update(revoked_at=timezone.now())
        return JsonResponse({'ok': True})


class PublicWorkoutRestAlertView(View):
    """Agenda e cancela o push do fim do descanso do modo foco.

    Só para quem tem este aparelho inscrito: o app manda o próprio `endpoint`
    e o aviso vai só para ele, não para todos os aparelhos da conta. O worker
    `run_public_workout_rest_alerts` envia no horário (public_workouts/rest_alerts.py).
    """

    http_method_names = ['post', 'delete']

    def post(self, request, plan_slug, *args, **kwargs):
        plan, account_id, error = _verified_account(request, plan_slug)
        if error:
            return error
        if not configured():
            return JsonResponse({'error': 'push-not-configured'}, status=503)
        data = json_payload(request)
        if data is None:
            return HttpResponse(status=400)
        try:
            alert = rest_alerts.schedule(
                account_id=account_id, plan_slug=plan.slug,
                session_id=data.get('session_id'), endpoint=data.get('endpoint'),
                remaining_ms=data.get('remaining_ms'), exercise=data.get('exercise'),
                set_number=data.get('set_number'),
            )
        except rest_alerts.RestAlertRejected as exc:
            status = 409 if exc.code in ('session-not-active', 'push-not-subscribed') else 400
            return JsonResponse({'error': exc.code}, status=status)
        return JsonResponse({'ok': True, 'revision': alert.revision})

    def delete(self, request, plan_slug, *args, **kwargs):
        plan, account_id, error = _verified_account(request, plan_slug)
        if error:
            return error
        data = json_payload(request) or {}
        cancelled = rest_alerts.cancel(
            account_id=account_id, plan_slug=plan.slug,
            session_id=data.get('session_id'),
        )
        return JsonResponse({'ok': True, 'cancelled': cancelled})
