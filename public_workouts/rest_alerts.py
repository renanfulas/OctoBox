"""Push do fim do descanso do modo foco, enviado pelo servidor no horário.

O iOS congela o PWA poucos segundos depois que ele sai da tela: o bipe e a
vibração do próprio app param ali. Com o app fechado ou a tela bloqueada, o
único jeito de o aluno sentir o fim do descanso é um push que sai do servidor
na hora certa. O app agenda ao começar o descanso, reagenda no "+30 s" e
cancela ao pular, ao encerrar e quando o descanso termina com a tela à vista
(o iOS exige mostrar notificação para cada push, então é o cancelamento que
evita o alerta duplo).

A fila da outbox roda a cada minuto e não serve aqui. `RestAlertWorker` é um
processo único (advisory lock no Postgres) que dorme até o próximo horário
pendente e acorda antes com LISTEN/NOTIFY quando um aviso é agendado. Ver
docs/decisions/0003-curva-rest-alert-worker.md.
"""

from __future__ import annotations

import logging
import re
import select
import time
import uuid
from datetime import timedelta

from django.db import IntegrityError, connection, transaction
from django.db.models import F
from django.utils import timezone

from .models import (
    PublicWorkoutPushSubscription, PublicWorkoutRestAlert, PublicWorkoutRestAlertStatus,
    PublicWorkoutTrainingSession,
)


logger = logging.getLogger(__name__)

NOTIFY_CHANNEL = 'curva_rest_alert'
# Chave do pg_advisory_lock: só um worker envia por banco ('CRVAREST').
WORKER_LOCK_KEY = 0x4352564152455354
MIN_DELAY_MS = 1_000
MAX_DELAY_MS = 30 * 60 * 1000
# Aviso atrasado além disso (worker fora do ar) não vale mais: vence sem enviar.
MAX_LATENESS = timedelta(seconds=30)
# Envio que travou no meio (worker morreu) não é repetido depois disso.
SENDING_LEASE = timedelta(seconds=60)
RETENTION = timedelta(days=7)
PUSH_TTL_SECONDS = 30
PUSH_TIMEOUT_SECONDS = 5
TITLE = 'Descanso acabou'
_CONTROL = re.compile(r'[\x00-\x1f\x7f]+')


class RestAlertRejected(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _clean_label(value) -> str:
    text = _CONTROL.sub(' ', str(value or ''))
    return ' '.join(text.split())[:80]


def _clean_set_number(value):
    if value in (None, ''):
        return None
    if isinstance(value, bool):
        raise RestAlertRejected('invalid-set-number')
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise RestAlertRejected('invalid-set-number') from exc
    if not 1 <= number <= 99:
        raise RestAlertRejected('invalid-set-number')
    return number


def _clean_delay(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RestAlertRejected('invalid-remaining')
    delay = int(value)
    if not MIN_DELAY_MS <= delay <= MAX_DELAY_MS:
        raise RestAlertRejected('invalid-remaining')
    return delay


def _session_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise RestAlertRejected('invalid-session') from exc


def _wake_worker():
    # Entregue no COMMIT: o worker nunca acorda antes de o aviso existir.
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_notify(%s, %s)', [NOTIFY_CHANNEL, ''])


def schedule(*, account_id, plan_slug, session_id, endpoint, remaining_ms, exercise='', set_number=None, now=None):
    """Agenda (ou reagenda) o aviso da sessão para daqui a `remaining_ms`.

    O prazo é relativo de propósito: o relógio do celular pode estar fora de
    hora, o do servidor é o que o worker usa.
    """
    delay = _clean_delay(remaining_ms)
    label = _clean_label(exercise)
    number = _clean_set_number(set_number)
    session = PublicWorkoutTrainingSession.objects.filter(
        pk=_session_uuid(session_id), account_id=account_id, plan_slug=plan_slug,
        ended_at__isnull=True, completed_at__isnull=True,
    ).first()
    if session is None:
        raise RestAlertRejected('session-not-active')
    subscription = PublicWorkoutPushSubscription.objects.filter(
        account_id=account_id, endpoint=str(endpoint or '').strip(), revoked_at__isnull=True,
    ).first()
    if subscription is None:
        raise RestAlertRejected('push-not-subscribed')
    due_at = (now or timezone.now()) + timedelta(milliseconds=delay)
    fields = {
        'subscription': subscription, 'due_at': due_at, 'status': PublicWorkoutRestAlertStatus.PENDING,
        'exercise_label': label, 'set_number': number, 'claimed_at': None, 'sent_at': None, 'last_error': '',
    }
    for attempt in range(2):
        try:
            with transaction.atomic():
                alert = PublicWorkoutRestAlert.objects.select_for_update().filter(session=session).first()
                if alert is None:
                    alert = PublicWorkoutRestAlert.objects.create(session=session, **fields)
                else:
                    for name, value in fields.items():
                        setattr(alert, name, value)
                    alert.revision += 1
                    alert.save()
                _wake_worker()
            return alert
        except IntegrityError:
            # Duas abas criando o primeiro aviso da sessão: a segunda atualiza.
            if attempt:
                raise
    raise AssertionError('unreachable')


def cancel(*, account_id, plan_slug, session_id) -> int:
    """Cancela o aviso pendente; um envio já em curso não volta atrás."""
    try:
        session_pk = _session_uuid(session_id)
    except RestAlertRejected:
        return 0
    return PublicWorkoutRestAlert.objects.filter(
        session_id=session_pk, session__account_id=account_id, session__plan_slug=plan_slug,
        status=PublicWorkoutRestAlertStatus.PENDING,
    ).update(
        status=PublicWorkoutRestAlertStatus.CANCELLED, revision=F('revision') + 1, updated_at=timezone.now(),
    )


def next_due_at():
    return PublicWorkoutRestAlert.objects.filter(
        status=PublicWorkoutRestAlertStatus.PENDING,
    ).order_by('due_at').values_list('due_at', flat=True).first()


def expire_overdue(now=None) -> int:
    now = now or timezone.now()
    expired = PublicWorkoutRestAlert.objects.filter(
        status=PublicWorkoutRestAlertStatus.PENDING, due_at__lt=now - MAX_LATENESS,
    ).update(
        status=PublicWorkoutRestAlertStatus.EXPIRED, last_error='worker-late',
        revision=F('revision') + 1, updated_at=now,
    )
    stuck = PublicWorkoutRestAlert.objects.filter(
        status=PublicWorkoutRestAlertStatus.SENDING, claimed_at__lt=now - SENDING_LEASE,
    ).update(status=PublicWorkoutRestAlertStatus.FAILED, last_error='sending-lease-expired', updated_at=now)
    if expired or stuck:
        logger.warning('curva_rest_alert_overdue expired=%s stuck=%s', expired, stuck)
    return expired + stuck


def _body(alert) -> str:
    if alert.exercise_label and alert.set_number:
        return f'{alert.exercise_label}, série {alert.set_number}'
    if alert.exercise_label:
        return alert.exercise_label
    if alert.set_number:
        return f'Série {alert.set_number}'
    return 'Hora da próxima série.'


def _finish(alert_id, revision, status, *, error='', sent_at=None):
    # Só fecha o envio que este worker reivindicou: se o aluno reagendou
    # (+30 s) durante o envio, a revisão mudou e o novo aviso continua pendente.
    return PublicWorkoutRestAlert.objects.filter(
        pk=alert_id, revision=revision, status=PublicWorkoutRestAlertStatus.SENDING,
    ).update(status=status, last_error=error[:120], sent_at=sent_at, updated_at=timezone.now())


def _deliver(alert_id, revision) -> str:
    from . import push

    alert = PublicWorkoutRestAlert.objects.select_related('session', 'subscription').get(pk=alert_id)
    session = alert.session
    if session.ended_at or session.completed_at:
        _finish(alert_id, revision, PublicWorkoutRestAlertStatus.CANCELLED, error='session-ended')
        return 'cancelled'
    if alert.subscription.revoked_at is not None:
        _finish(alert_id, revision, PublicWorkoutRestAlertStatus.FAILED, error='subscription-revoked')
        return 'failed'
    delivered = push.send(
        subscription=alert.subscription, title=TITLE, body=_body(alert),
        url=f'/renan/{session.plan_slug}#treino-guiado', tag=f'curva-rest-{session.pk}',
        ttl=PUSH_TTL_SECONDS, urgency='high', timeout=PUSH_TIMEOUT_SECONDS,
        # Mesma tag em toda a sessão: substitui o aviso anterior em vez de empilhar,
        # e `renotify` faz a substituição vibrar de novo.
        extra={'kind': 'rest', 'renotify': True, 'vibrate': [180, 90, 180]},
    )
    sent_at = timezone.now()
    lateness_ms = int((sent_at - alert.due_at).total_seconds() * 1000)
    if delivered:
        _finish(alert_id, revision, PublicWorkoutRestAlertStatus.SENT, sent_at=sent_at)
        logger.info('curva_rest_alert_sent alert_id=%s lateness_ms=%s', alert_id, lateness_ms)
        return 'sent'
    alert.subscription.refresh_from_db(fields=['last_error'])
    _finish(alert_id, revision, PublicWorkoutRestAlertStatus.FAILED, error=alert.subscription.last_error or 'push-failed')
    logger.warning('curva_rest_alert_failed alert_id=%s lateness_ms=%s', alert_id, lateness_ms)
    return 'failed'


def dispatch_due(*, now=None, limit=50) -> dict[str, int]:
    """Reivindica os avisos vencidos e envia um a um."""
    now = now or timezone.now()
    counters = {'sent': 0, 'failed': 0, 'cancelled': 0}
    with transaction.atomic():
        claimed = list(PublicWorkoutRestAlert.objects.select_for_update(skip_locked=True).filter(
            status=PublicWorkoutRestAlertStatus.PENDING, due_at__lte=now,
        ).order_by('due_at').values_list('pk', 'revision')[:limit])
        if claimed:
            PublicWorkoutRestAlert.objects.filter(pk__in=[pk for pk, _ in claimed]).update(
                status=PublicWorkoutRestAlertStatus.SENDING, claimed_at=now, updated_at=now,
            )
    for alert_id, revision in claimed:
        try:
            counters[_deliver(alert_id, revision)] += 1
        except Exception as exc:
            _finish(alert_id, revision, PublicWorkoutRestAlertStatus.FAILED, error=f'error:{type(exc).__name__}')
            logger.exception('curva_rest_alert_error alert_id=%s', alert_id)
            counters['failed'] += 1
    return counters


def prune(now=None) -> int:
    now = now or timezone.now()
    deleted, _ = PublicWorkoutRestAlert.objects.exclude(
        status__in=(PublicWorkoutRestAlertStatus.PENDING, PublicWorkoutRestAlertStatus.SENDING),
    ).filter(updated_at__lt=now - RETENTION).delete()
    return deleted


class RestAlertWorker:
    """Laço do worker: segura o lock, envia o que venceu e dorme até o próximo.

    O sono acaba no horário do próximo aviso pendente ou num NOTIFY do
    agendamento, o que vier primeiro; `max_idle` limita o sono como rede de
    segurança caso um NOTIFY se perca numa reconexão.
    """

    def __init__(self, *, max_idle=15.0, standby_poll=5.0, prune_every=3600.0):
        self.max_idle = max_idle
        self.standby_poll = standby_poll
        self.prune_every = prune_every
        self._raw = None
        self._last_prune = None

    def run(self, *, should_stop=lambda: False):
        while not should_stop():
            try:
                self.tick(should_stop=should_stop)
            except Exception:
                # Banco caiu ou reiniciou: reconecta, refaz lock e LISTEN.
                logger.exception('curva_rest_alert_worker_error')
                self.reset()
                time.sleep(1)
        self.release()

    def release(self):
        """Solta lock e LISTEN sem fechar a conexão (o processo pode seguir)."""
        if self._raw is None:
            return
        self._raw = None
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'UNLISTEN {NOTIFY_CHANNEL}')
                cursor.execute('SELECT pg_advisory_unlock(%s)', [WORKER_LOCK_KEY])
        except Exception:
            # Conexão já caiu: o Postgres soltou lock e LISTEN junto com ela.
            logger.warning('curva_rest_alert_worker_release_failed', exc_info=True)

    def reset(self):
        # Fechar a conexão derruba lock e LISTEN junto; a próxima volta refaz.
        self._raw = None
        try:
            connection.close()
        except Exception:
            logger.warning('curva_rest_alert_worker_close_failed', exc_info=True)

    def _attach(self) -> bool:
        connection.ensure_connection()
        raw = connection.connection
        if raw is self._raw:
            return True
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_try_advisory_lock(%s)', [WORKER_LOCK_KEY])
            if not cursor.fetchone()[0]:
                return False
            cursor.execute(f'LISTEN {NOTIFY_CHANNEL}')
        self._raw = raw
        logger.info('curva_rest_alert_worker_active')
        return True

    def tick(self, *, should_stop=lambda: False):
        if not self._attach():
            # Outro worker está ativo; fica de reserva.
            time.sleep(self.standby_poll)
            return 'standby'
        now = timezone.now()
        expire_overdue(now)
        counters = dispatch_due(now=now)
        if self._last_prune is None or time.monotonic() - self._last_prune >= self.prune_every:
            self._last_prune = time.monotonic()
            prune(now)
        if should_stop():
            return counters
        upcoming = next_due_at()
        timeout = self.max_idle
        if upcoming is not None:
            timeout = min(self.max_idle, max(0.0, (upcoming - timezone.now()).total_seconds()))
        if timeout > 0:
            self._wait(timeout)
        return counters

    def _wait(self, timeout):
        raw = self._raw
        notifies = getattr(raw, 'notifies', None)
        if callable(notifies):
            # psycopg 3: devolve primeiro os NOTIFY que chegaram fora da espera.
            for _ in notifies(timeout=timeout, stop_after=1):
                break
            return
        # psycopg2: NOTIFY recebidos durante outras consultas ficam na lista.
        if raw.notifies:
            raw.notifies.clear()
            return
        if select.select([raw], [], [], timeout)[0]:
            raw.poll()
            raw.notifies.clear()


__all__ = ['RestAlertRejected', 'RestAlertWorker', 'cancel', 'dispatch_due', 'schedule']
