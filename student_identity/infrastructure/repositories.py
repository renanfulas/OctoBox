from __future__ import annotations

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from student_identity.box_scope import (
    get_student_identity_box_scope,
    get_student_identity_box_scope_for_box_id,
    get_student_identity_box_scope_for_root,
    student_identity_box_references_match,
)

from student_identity.application.results import (
    IdentitySaveConflictError,
    StudentBoxInviteLinkRecord,
    StudentIdentityRecord,
    StudentInvitationRecord,
)
from student_identity.models import (
    StudentAppInvitation,
    StudentBoxInviteLink,
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentIdentity,
    StudentIdentityStatus,
    StudentInvitationType,
    StudentOnboardingJourney,
    StudentTransfer,
    StudentTransferStatus,
)

# Sprint 2: Student NAO e mais importado aqui diretamente.
# student_identity e SHARED_APPS (public schema). Student e TENANT_APPS (box_xxx schema).
# Acesso ao Student deve usar schema_context(box.schema_name) nos call sites que precisam.
# A funcao find_student_by_id abaixo ainda funciona quando chamada com tenant ativo no request.


def _identity_record(identity: StudentIdentity) -> StudentIdentityRecord:
    return StudentIdentityRecord(
        id=identity.id,
        student_id=identity.student_id,
        student_name=identity.student_name,  # Sprint 2: era identity.student.full_name (cross-schema)
        email=identity.email,
        provider=identity.provider,
        box_root_slug=identity.box_root_slug,
        primary_box_root_slug=identity.primary_box_root_slug,
        status=identity.status,
    )


def _invitation_record(invitation: StudentAppInvitation) -> StudentInvitationRecord:
    return StudentInvitationRecord(
        id=invitation.id,
        token=str(invitation.token),
        student_id=invitation.student_id,
        student_name=invitation.student_name,  # Sprint 2: era invitation.student.full_name (cross-schema)
        invite_type=invitation.invite_type,
        onboarding_journey=invitation.onboarding_journey,
        invited_email=invitation.invited_email,
        box_root_slug=invitation.box_root_slug,
        expires_at_iso=invitation.expires_at.isoformat(),
        accepted_at_iso=invitation.accepted_at.isoformat() if invitation.accepted_at else '',
    )


def _box_invite_link_record(link: StudentBoxInviteLink) -> StudentBoxInviteLinkRecord:
    return StudentBoxInviteLinkRecord(
        id=link.id,
        token=str(link.token),
        box_root_slug=link.box_root_slug,
        expires_at_iso=link.expires_at.isoformat(),
        max_uses=link.max_uses,
        use_count=link.use_count,
        paused_at_iso=link.paused_at.isoformat() if link.paused_at else '',
        revoked_at_iso=link.revoked_at.isoformat() if link.revoked_at else '',
    )


class DjangoStudentIdentityRepository:
    def _ensure_membership_status(
        self,
        *,
        identity: StudentIdentity,
        student_id: int | None = None,
        box_root_slug: str,
        invitation=None,
        actor_id: int | None = None,
        status: str = StudentBoxMembershipStatus.ACTIVE,
    ) -> StudentBoxMembership:
        # Sprint 2: 'student' FK removido de StudentBoxMembership.
        # student_id e passado como IntegerField (referencia fraca, sem constraint DB).
        effective_student_id = student_id or (identity.student_id)
        scope = get_student_identity_box_scope_for_root(box_root_slug)
        target_root = scope.box_root_slug
        membership = (
            StudentBoxMembership.objects.filter(
                identity=identity,
                box_id=scope.box.pk,
            ).first()
            if scope.box else None
        )
        if membership is None:
            membership = StudentBoxMembership.objects.filter(
                identity=identity,
                box__isnull=True,
                box_root_slug__in=(
                    {scope.box_root_slug, scope.box.slug}
                    if scope.box else {scope.box_root_slug}
                ),
            ).first()
        if membership is None:
            membership = StudentBoxMembership(
                identity=identity,
                box=scope.box,
                box_root_slug=target_root,
                student_id=effective_student_id,
                status=status,
                created_from_invite=invitation,
                approved_by_id=actor_id,
            )
        elif scope.box and membership.box_id is None:
            membership.box = scope.box
        # Atualiza student_id caso membership existente nao tenha (migracao gradual)
        if effective_student_id and not membership.student_id:
            membership.student_id = effective_student_id
        if invitation is not None and membership.created_from_invite_id is None:
            membership.created_from_invite = invitation
        if status == StudentBoxMembershipStatus.ACTIVE:
            membership.mark_active()
            if actor_id is not None and membership.approved_by_id is None:
                membership.approved_by_id = actor_id
        else:
            membership.status = status
        membership.save()
        return membership

    def find_student_by_id(self, student_id: int):
        # AVISO: requer tenant ativo em connection.schema_name.
        # Se chamado sem tenant, falha com "relation boxcore_student does not exist".
        from students.models import Student
        return Student.objects.filter(pk=student_id).first()

    def find_identity_by_id(self, identity_id: int):
        # Sprint 2: removido select_related('student') — cross-schema
        return StudentIdentity.objects.filter(pk=identity_id).first()

    def find_membership_for_identity_box(self, identity):
        box_scope = get_student_identity_box_scope_for_box_id(
            getattr(identity, 'box_id', None)
        ) or get_student_identity_box_scope_for_root(identity.box_root_slug)
        identity_id = getattr(identity, 'id', None) or getattr(identity, 'pk', None)
        if box_scope.box is not None:
            membership = StudentBoxMembership.objects.filter(
                identity_id=identity_id,
                box_id=box_scope.box.pk,
            ).first()
            if membership is not None:
                return membership
            return StudentBoxMembership.objects.filter(
                identity_id=identity_id,
                box__isnull=True,
                box_root_slug__in={box_scope.box.schema_name, box_scope.box.slug},
            ).first()
        return StudentBoxMembership.objects.filter(
            box_scope.predicate,
            identity_id=identity_id,
        ).first()

    def is_same_box(self, *, identity, box_root_slug: str) -> bool:
        return self.is_same_box_reference(
            box_id=getattr(identity, 'box_id', None) or getattr(identity, 'primary_box_id', None),
            box_root_slug=identity.box_root_slug,
            target_box_root_slug=box_root_slug,
        )

    def is_same_box_reference(
        self,
        *,
        box_id: int | None,
        box_root_slug: str,
        target_box_root_slug: str,
    ) -> bool:
        return student_identity_box_references_match(
            box_id=box_id,
            box_root_slug=box_root_slug,
            target_box_root_slug=target_box_root_slug,
        )

    def find_live_by_student_id(self, student_id: int):
        # Sprint 2: removido select_related('student') — cross-schema
        return (
            StudentIdentity.objects
            .filter(
                get_student_identity_box_scope().predicate,
                student_id=student_id,
                status__in=[StudentIdentityStatus.PENDING, StudentIdentityStatus.ACTIVE],
            )
            .first()
        )

    def find_live_by_email_and_box(self, *, email: str, box_root_slug: str):
        from student_identity.queries.email_lookup import identities_for_email

        queryset = StudentIdentity.objects.filter(
            get_student_identity_box_scope_for_root(box_root_slug).predicate,
            status__in=[StudentIdentityStatus.PENDING, StudentIdentityStatus.ACTIVE],
        )
        return next(iter(identities_for_email(email, queryset=queryset)), None)

    def find_by_provider_subject(self, *, provider_subject: str):
        # Sprint 2: removido select_related('student') — cross-schema
        return (
            StudentIdentity.objects
            .filter(provider_subject=provider_subject)
            .first()
        )

    def find_invitation_by_token(self, token: str):
        # Sprint 2: removido select_related('student') — cross-schema
        return (
            StudentAppInvitation.objects
            .filter(token=token)
            .first()
        )

    def find_box_invite_link_by_token(self, token: str):
        return StudentBoxInviteLink.objects.filter(token=token).first()

    def find_student_candidates_by_email(self, *, email: str):
        # AVISO: requer tenant ativo em connection.schema_name.
        # Sprint 4 / fix OAuth-500: Student e TENANT_APP — a tabela students_student
        # nao existe em public/control schema. Se o tenant nao foi ativado (ex.:
        # control_box vazio, nenhum Box ATIVO), a query explode com ProgrammingError
        # e devolve HTTP 500. Retornar [] forca failure_reason='student-email-ambiguous'
        # e redireciona para login com mensagem clara em vez de tela de erro.
        from django.db import connection
        if connection.schema_name in ('public', 'control'):
            return []
        from students.models import Student
        return list(Student.objects.filter(email__iexact=(email or '').strip()).order_by('id'))

    def count_open_box_invites_since(self, *, box_root_slug: str, since):
        box_scope = get_student_identity_box_scope_for_root(box_root_slug)
        return StudentAppInvitation.objects.filter(
            box_scope.predicate,
            invite_type=StudentInvitationType.OPEN_BOX,
            created_at__gte=since,
        ).count()

    @transaction.atomic
    def create_invitation(
        self,
        *,
        student,
        invited_email: str,
        box_root_slug: str,
        invite_type: str,
        onboarding_journey: str,
        expires_in_days: int,
        actor_id: int | None,
    ) -> StudentInvitationRecord:
        now = timezone.now()
        box_scope = get_student_identity_box_scope_for_root(box_root_slug)
        effective_box_root_slug = box_scope.box_root_slug
        # Sprint 2: filtra por student_id (IntegerField) em vez de student FK
        (
            StudentAppInvitation.objects
            .filter(
                box_scope.predicate,
                student_id=student.id,
                accepted_at__isnull=True,
                expires_at__gt=now,
            )
            .update(expires_at=now)
        )
        invitation = StudentAppInvitation.objects.create(
            student_id=student.id,
            student_name=student.full_name,  # Sprint 2: denormalizado
            box=box_scope.box,
            box_root_slug=effective_box_root_slug,
            invite_type=invite_type,
            onboarding_journey=onboarding_journey or StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
            invited_email=(invited_email or '').strip().lower(),
            expires_at=now + timedelta(days=max(1, expires_in_days)),
            created_by_id=actor_id,
        )
        return _invitation_record(invitation)

    @transaction.atomic
    def create_or_replace_box_invite_link(
        self,
        *,
        box_root_slug: str,
        expires_in_days: int,
        max_uses: int,
        actor_id: int | None,
    ) -> StudentBoxInviteLinkRecord:
        now = timezone.now()
        box_scope = get_student_identity_box_scope_for_root(box_root_slug)
        effective_box_root_slug = box_scope.box_root_slug
        (
            StudentBoxInviteLink.objects
            # Inclui links pausados: "Gerar novo link" substitui TODOS os do box. Antes o pausado
            # sobrevivia e, ao ser retomado, voltava a funcionar ao lado do link novo.
            .filter(
                box_scope.predicate,
                revoked_at__isnull=True,
                expires_at__gt=now,
            )
            .update(revoked_at=now)
        )
        link = StudentBoxInviteLink.objects.create(
            box=box_scope.box,
            box_root_slug=effective_box_root_slug,
            expires_at=now + timedelta(days=max(1, expires_in_days)),
            max_uses=max(1, max_uses),
            created_by_id=actor_id,
        )
        return _box_invite_link_record(link)

    @transaction.atomic
    def consume_box_invite_slot(
        self,
        link_id: int,
        *,
        box_id: int | None = None,
        box_root_slug: str = '',
    ) -> bool:
        """Consome 1 vaga do link do grupo, atomicamente (um UPDATE condicional no banco).

        Duas requests simultaneas nunca passam de max_uses: o WHERE reavalia use_count < max_uses
        no momento do UPDATE. Devolve False se o link acabou/pausou/revogou/expirou.
        """
        now = timezone.now()
        if box_id:
            box_scope = get_student_identity_box_scope_for_box_id(box_id)
            if box_scope is None:
                return False
            if box_root_slug and not student_identity_box_references_match(
                box_id=box_id,
                box_root_slug=box_scope.box_root_slug,
                target_box_root_slug=box_root_slug,
            ):
                return False
        elif box_root_slug:
            box_scope = get_student_identity_box_scope_for_root(box_root_slug)
        else:
            box_scope = get_student_identity_box_scope()
        updated = StudentBoxInviteLink.objects.filter(
            box_scope.predicate,
            pk=link_id,
            paused_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=now,
            use_count__lt=F('max_uses'),
        ).update(use_count=F('use_count') + 1, updated_at=now)
        return updated == 1

    @transaction.atomic
    def record_box_invite_acceptance(self, link: StudentBoxInviteLink) -> StudentBoxInviteLink:
        # Mantido por compatibilidade; sem leitura-modificacao-escrita em Python.
        self.consume_box_invite_slot(
            link.pk,
            box_id=link.box_id,
            box_root_slug=link.box_root_slug,
        )
        return StudentBoxInviteLink.objects.get(pk=link.pk)

    @transaction.atomic
    def save_identity(
        self,
        *,
        student,
        box_root_slug: str,
        provider: str,
        provider_subject: str,
        email: str,
        invitation=None,
        photo_url: str = '',
    ) -> StudentIdentityRecord:
        box_scope = get_student_identity_box_scope_for_root(box_root_slug)
        effective_box_root_slug = box_scope.box_root_slug
        normalized_photo_url = (photo_url or '').strip()
        identity = self.find_live_by_student_id(student.id)
        if identity is None:
            # Onda 1 (docs/plans/student-login-magic-link-bugs-corda.md): find_live_by_student_id
            # so enxerga StudentIdentity do MESMO Student — uma chave LOCAL ao schema do tenant
            # atual. Quando esse provider_subject ja pertence a uma identidade de OUTRO box
            # (Student diferente, mas StudentIdentity e schema publico/compartilhado), essa busca
            # nunca acha, e o create() abaixo estouraria IntegrityError (provider_subject e
            # unique=True). Cinto de seguranca: procurar tambem pela chave global antes de criar.
            if self.find_by_provider_subject(provider_subject=provider_subject) is not None:
                raise IdentitySaveConflictError('provider-subject-conflict')
            identity = StudentIdentity(
                student_id=student.id,          # Sprint 2: IntegerField (sem FK)
                student_name=student.full_name,  # Sprint 2: denormalizado
                box=box_scope.box,
                box_root_slug=effective_box_root_slug,
                primary_box=box_scope.box,
                primary_box_root_slug=effective_box_root_slug,
                provider=provider,
                provider_subject=provider_subject,
                email=(email or '').strip().lower(),
                invited_at=timezone.now() if invitation is not None else None,
                photo_url=normalized_photo_url,
            )
        else:
            identity.student_id = student.id
            identity.student_name = student.full_name  # Sprint 2: mantém denorm sincronizado
            if box_scope.box is not None:
                identity.box = box_scope.box
            identity.box_root_slug = effective_box_root_slug
            identity.provider = provider
            identity.provider_subject = provider_subject
            identity.email = (email or '').strip().lower()
            if not identity.primary_box_root_slug:
                identity.primary_box = box_scope.box
                identity.primary_box_root_slug = effective_box_root_slug
            elif not identity.primary_box_id:
                primary_scope = get_student_identity_box_scope_for_root(
                    identity.primary_box_root_slug
                )
                if primary_scope.box is not None:
                    identity.primary_box = primary_scope.box
            if invitation is not None and identity.invited_at is None:
                identity.invited_at = timezone.now()
            # So sobrescreve com um valor novo — nunca apaga uma foto ja salva
            # com um payload sem foto (ex.: Apple normalmente nao manda picture).
            if normalized_photo_url:
                identity.photo_url = normalized_photo_url

        # Onda 3 (docs/plans/student-login-magic-link-bugs-corda.md): o commit bd01222e
        # removeu a validacao de duplicidade de e-mail do onboarding sem substitui-la — so
        # a UniqueConstraint condicional do banco (models.py, status in [PENDING, ACTIVE])
        # pegava isso, como IntegrityError cru. find_live_by_email_and_box ja usa o mesmo
        # criterio de "vivo" da constraint; exclui a propria identity (update sem mudar
        # e-mail, ou re-save do mesmo registro) comparando pk.
        conflicting_identity = self.find_live_by_email_and_box(
            email=identity.email,
            box_root_slug=effective_box_root_slug,
        )
        if conflicting_identity is not None and conflicting_identity.id != identity.pk:
            raise IdentitySaveConflictError('email-conflict', provider=conflicting_identity.provider)

        identity.mark_authenticated()
        try:
            # savepoint interno: save_identity ja e @transaction.atomic — sem este
            # `with transaction.atomic()`, um IntegrityError aqui deixaria a transacao
            # externa marcada "precisa de rollback" e qualquer query seguinte nesta
            # mesma funcao (ex.: _ensure_membership_status, logo abaixo) estouraria
            # TransactionManagementError em vez do conflito limpo que queremos devolver.
            with transaction.atomic():
                identity.save()
        except IntegrityError as exc:
            # So alcancavel por uma corrida real (duas requests simultaneas passando pelas
            # checagens acima — provider_subject ou e-mail — antes de qualquer uma
            # commitar). As checagens acima ja cobrem o caso comum e deterministico.
            raise IdentitySaveConflictError('unique-constraint-conflict') from exc
        membership_status = StudentBoxMembershipStatus.ACTIVE
        if invitation is not None and invitation.invite_type == StudentInvitationType.OPEN_BOX:
            membership_status = StudentBoxMembershipStatus.PENDING_APPROVAL

        self._ensure_membership_status(
            identity=identity,
            student_id=student.id,
            box_root_slug=effective_box_root_slug,
            invitation=invitation,
            status=membership_status,
        )

        if invitation is not None and invitation.accepted_at is None:
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=['accepted_at'])

        if not student.email:
            student.email = identity.email
            student.save(update_fields=['email'])

        return _identity_record(identity)

    @transaction.atomic
    def mark_authenticated(self, identity) -> StudentIdentityRecord:
        identity.mark_authenticated()
        identity.save(update_fields=['status', 'activated_at', 'last_authenticated_at'])
        membership = self.find_membership_for_identity_box(identity)
        if membership is None:
            self._ensure_membership_status(
                identity=identity,
                student_id=identity.student_id,  # Sprint 2: IntegerField
                box_root_slug=identity.box_root_slug,
                status=StudentBoxMembershipStatus.ACTIVE,
            )
        elif membership.status == StudentBoxMembershipStatus.ACTIVE:
            membership.last_access_at = timezone.now()
            membership.save(update_fields=['last_access_at', 'updated_at'])
        return _identity_record(identity)

    @transaction.atomic
    def transfer_identity(
        self,
        *,
        identity,
        to_box_root_slug: str,
        actor_id: int | None,
        reason: str,
    ) -> tuple[StudentIdentityRecord, int]:
        target_scope = get_student_identity_box_scope_for_root(to_box_root_slug)
        source_scope = get_student_identity_box_scope_for_box_id(
            getattr(identity, 'box_id', None) or getattr(identity, 'primary_box_id', None)
        ) or get_student_identity_box_scope_for_root(identity.box_root_slug)
        source_root = source_scope.box_root_slug
        target_root = target_scope.box_root_slug
        transfer = StudentTransfer.objects.create(
            identity=identity,
            student_id=identity.student_id,  # Sprint 2: IntegerField (sem FK)
            from_box_root_slug=source_root,
            to_box_root_slug=target_root,
            from_box=source_scope.box,
            to_box=target_scope.box,
            status=StudentTransferStatus.COMPLETED,
            requested_by_id=actor_id,
            completed_at=timezone.now(),
            reason=reason,
            audit_summary=f'Transferência concluída de {source_root} para {target_root}.',
        )
        previous_box_root_slug = identity.box_root_slug
        previous_membership = None
        if source_scope.box is not None:
            previous_membership = StudentBoxMembership.objects.filter(
                identity=identity, box_id=source_scope.box.pk
            ).first()
            if previous_membership is None:
                previous_membership = StudentBoxMembership.objects.filter(
                    identity=identity,
                    box__isnull=True,
                    box_root_slug__in={source_scope.box.schema_name, source_scope.box.slug},
                ).first()
        else:
            previous_membership = StudentBoxMembership.objects.filter(
                identity=identity, box_root_slug=previous_box_root_slug
            ).first()
        if previous_membership is None:
            previous_membership = StudentBoxMembership.objects.create(
                identity=identity,
                student_id=identity.student_id,  # Sprint 2: IntegerField
                box=source_scope.box,
                box_root_slug=previous_box_root_slug,
                status=StudentBoxMembershipStatus.INACTIVE,
                revoked_reason=reason,
                revoked_at=timezone.now(),
            )
        else:
            if source_scope.box is not None and previous_membership.box_id is None:
                previous_membership.box = source_scope.box
            previous_membership.status = StudentBoxMembershipStatus.INACTIVE
            previous_membership.revoked_reason = reason
            previous_membership.revoked_at = timezone.now()
            previous_membership.save(update_fields=['box', 'status', 'revoked_reason', 'revoked_at', 'updated_at'])
        identity.box = target_scope.box
        identity.primary_box = target_scope.box
        identity.box_root_slug = target_root
        identity.primary_box_root_slug = target_root
        identity.last_authenticated_at = timezone.now()
        identity.save(update_fields=[
            'box', 'primary_box', 'box_root_slug', 'primary_box_root_slug', 'last_authenticated_at'
        ])
        self._ensure_membership_status(
            identity=identity,
            student_id=identity.student_id,  # Sprint 2: IntegerField
            box_root_slug=target_root,
            actor_id=actor_id,
            status=StudentBoxMembershipStatus.ACTIVE,
        )
        return _identity_record(identity), transfer.id
