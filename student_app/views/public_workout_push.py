"""Inscrição Web Push do aluno Curva, isolada dos comandos de treino."""

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views import View

from student_identity.public_workout_session import get_verified_public_workout_account_id_from_request
from student_app.views.public_workout_request import json_payload
from student_app.views.public_workout_access import (
    _confirm_login_session_owns_slug_or_404,
    _get_public_workout_entry,
)

from public_workouts.models import PublicWorkoutPushSubscription
from public_workouts.outbox import TOPIC_PUSH_WELCOME, enqueue_outbox
from public_workouts.push import configured, subscribe


class PublicWorkoutPushSubscriptionView(View):
    http_method_names = ['post', 'delete']

    def _account(self, request, plan_slug):
        plan = _get_public_workout_entry(plan_slug)
        account_id = get_verified_public_workout_account_id_from_request(request)
        if account_id is None:
            return None, JsonResponse({'error': 'login necessario'}, status=401)
        _confirm_login_session_owns_slug_or_404(request, plan.slug)
        return account_id, None

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
