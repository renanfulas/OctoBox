"""Persistência tenant-local de texto WOD, independente do treino efetivo."""

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import Http404
from django.utils import timezone

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, get_user_role
from operations.models import WorkoutProgram
from operations.workout_editor_loader import load_coach_workout_editor_session
from student_app.models import WeeklyWodPlan, WodInputDraft


MAX_SOURCE_LENGTH = 20_000
MAX_ACTIVE_DRAFTS = 20
DRAFT_TTL = timedelta(days=30)


class DraftConflict(Exception):
    def __init__(self, code, version=None):
        self.code = code
        self.version = version
        super().__init__(code)


class DraftQuota(Exception):
    pass


class DraftTooLarge(Exception):
    pass


@dataclass(frozen=True)
class DraftScope:
    kind: str
    key: str
    session: object = None
    week_start: date | None = None
    program: object = None
    weekly_plan: object = None


def _positive_int(value, field):
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f'{field} inválido.') from exc
    if number < 1:
        raise ValidationError(f'{field} inválido.')
    return number


def _uuid(value, field):
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValidationError(f'{field} inválido.') from exc


def resolve_draft_scope(*, actor, scope_kind, session_id=None, week_start=None,
                        workout_program_id=None, plan_id=None):
    role = get_user_role(actor)
    if role is None or role.slug not in {ROLE_COACH, ROLE_MANAGER, ROLE_OWNER}:
        raise PermissionDenied('Sem permissão para editar rascunhos WOD.')
    if scope_kind == WodInputDraft.Scope.DAILY:
        if role.slug not in {ROLE_COACH, ROLE_OWNER}:
            raise PermissionDenied('O editor diário é exclusivo de Coach e Owner.')
        session = load_coach_workout_editor_session(
            session_id=_positive_int(session_id, 'session_id'), actor=actor,
        )
        return DraftScope(kind=scope_kind, key=f'session:{session.pk}', session=session)
    if scope_kind != WodInputDraft.Scope.WEEKLY:
        raise ValidationError('scope_kind inválido.')
    try:
        target_week = date.fromisoformat(str(week_start))
    except (TypeError, ValueError) as exc:
        raise ValidationError('week_start deve ser uma data ISO.') from exc
    if target_week.weekday() != 0:
        raise ValidationError('week_start deve ser uma segunda-feira.')
    program = WorkoutProgram.objects.filter(
        pk=_positive_int(workout_program_id, 'workout_program_id'), is_active=True,
    ).first()
    if program is None:
        raise Http404('Programa não encontrado.')
    plan = None
    if plan_id:
        plan = WeeklyWodPlan.objects.filter(
            pk=_positive_int(plan_id, 'plan_id'), created_by=actor,
            week_start=target_week, workout_program=program,
        ).first()
        if plan is None:
            raise Http404('Plano semanal não encontrado neste escopo.')
    return DraftScope(
        kind=scope_kind, key=f'week:{target_week.isoformat()}:program:{program.pk}',
        week_start=target_week, program=program, weekly_plan=plan,
    )


def draft_payload(draft):
    if draft is None:
        return {'ok': True, 'draft': None}
    return {'ok': True, 'draft': {
        'draft_id': str(draft.pk), 'scope_kind': draft.scope_kind,
        'source_text': draft.source_text, 'version': draft.version,
        'parser_version': draft.parser_version,
        'updated_at': draft.updated_at.isoformat(),
        'expires_at': draft.expires_at.isoformat(),
    }}


def load_draft(*, actor, scope):
    WodInputDraft.objects.filter(
        author=actor, scope_key=scope.key, state=WodInputDraft.State.ACTIVE,
        expires_at__lte=timezone.now(),
    ).update(state=WodInputDraft.State.EXPIRED)
    return WodInputDraft.objects.filter(
        author=actor, scope_key=scope.key, state=WodInputDraft.State.ACTIVE,
        expires_at__gt=timezone.now(),
    ).first()


@transaction.atomic
def save_draft(*, actor, scope, source_text, request_id, expected_version=None, draft_id=None):
    if not isinstance(source_text, str):
        raise ValidationError('source_text deve ser texto.')
    if len(source_text) > MAX_SOURCE_LENGTH:
        raise DraftTooLarge(f'O texto excede {MAX_SOURCE_LENGTH} caracteres.')
    request_uuid = _uuid(request_id, 'request_id')
    now = timezone.now()
    expires = now + DRAFT_TTL
    if expected_version is None:
        # A linha compartilhada do autor serializa criação/quota entre abas.
        get_user_model().objects.select_for_update().get(pk=actor.pk)
        replay = WodInputDraft.objects.filter(author=actor, create_request_id=request_uuid).first()
        if replay is not None:
            if (
                replay.scope_key != scope.key or replay.source_text != source_text
                or replay.state != WodInputDraft.State.ACTIVE or replay.expires_at <= now
            ):
                raise DraftConflict('request_id_reused', replay.version)
            return replay
        current = load_draft(actor=actor, scope=scope)
        if current is not None:
            raise DraftConflict('draft_exists', current.version)
        WodInputDraft.objects.filter(
            author=actor, state=WodInputDraft.State.ACTIVE, expires_at__lte=now,
        ).update(state=WodInputDraft.State.EXPIRED)
        if WodInputDraft.objects.filter(author=actor, state=WodInputDraft.State.ACTIVE).count() >= MAX_ACTIVE_DRAFTS:
            raise DraftQuota('Limite de rascunhos ativos atingido.')
        try:
            return WodInputDraft.objects.create(
                author=actor, scope_kind=scope.kind, scope_key=scope.key,
                session=scope.session, weekly_plan=scope.weekly_plan,
                week_start=scope.week_start, workout_program=scope.program,
                source_text=source_text, create_request_id=request_uuid,
                last_request_id=request_uuid, expires_at=expires,
            )
        except IntegrityError as exc:
            raise DraftConflict('draft_exists') from exc

    version = _positive_int(expected_version, 'expected_version')
    draft_uuid = _uuid(draft_id, 'draft_id')
    current = load_draft(actor=actor, scope=scope)
    if current is None or current.pk != draft_uuid:
        raise DraftConflict('draft_missing')
    if current.last_request_id == request_uuid:
        if current.source_text != source_text:
            raise DraftConflict('request_id_reused', current.version)
        return current
    changed = WodInputDraft.objects.filter(
        pk=draft_uuid, author=actor, scope_key=scope.key,
        state=WodInputDraft.State.ACTIVE, expires_at__gt=now,
        version=version,
    ).update(
        source_text=source_text, version=F('version') + 1,
        last_request_id=request_uuid, updated_at=now, expires_at=expires,
        weekly_plan=scope.weekly_plan or current.weekly_plan,
    )
    if not changed:
        fresh = WodInputDraft.objects.filter(pk=draft_uuid, author=actor).first()
        raise DraftConflict('stale_version', fresh.version if fresh else None)
    return WodInputDraft.objects.get(pk=draft_uuid)


@transaction.atomic
def discard_draft(*, actor, scope, draft_id, expected_version):
    draft_uuid = _uuid(draft_id, 'draft_id')
    version = _positive_int(expected_version, 'expected_version')
    changed = WodInputDraft.objects.filter(
        pk=draft_uuid, author=actor, scope_key=scope.key,
        state=WodInputDraft.State.ACTIVE, version=version,
    ).update(state=WodInputDraft.State.DISCARDED, version=F('version') + 1, updated_at=timezone.now())
    if not changed:
        raise DraftConflict('stale_version')


def link_weekly_draft(*, actor, plan):
    if not plan.workout_program_id:
        return
    key = f'week:{plan.week_start.isoformat()}:program:{plan.workout_program_id}'
    WodInputDraft.objects.filter(
        author=actor, scope_key=key, state=WodInputDraft.State.ACTIVE,
    ).update(weekly_plan=plan)
