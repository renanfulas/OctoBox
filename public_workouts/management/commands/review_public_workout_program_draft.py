"""
ARQUIVO: revisão e publicação controlada de rascunhos de treino Curva.

POR QUE ELE EXISTE:
- substitui consultas e mutações ad hoc no Django shell por uma operação
  reproduzível para revisão remota via SSH.

O QUE ESTE ARQUIVO FAZ:
1. mostra estado, versão-base, versão ativa, schema, plano e diff.
2. mantém a execução somente leitura por padrão.
3. exige versão ativa esperada e revisor de equipe para publicar.
4. chama o serviço oficial e confirma versão e outbox.

PONTOS CRITICOS:
- a publicação sempre passa por approve_and_publish_draft.
- nunca use publish_program em shell para contornar a revisão humana.
"""

from __future__ import annotations

import difflib
import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from public_workouts.models import (
    PublicWorkoutOutboxMessage,
    PublicWorkoutProgram,
    PublicWorkoutProgramDraft,
    PublicWorkoutProgramDraftStatus,
    PublicWorkoutSubscription,
    PublicWorkoutWorkItem,
    PublicWorkoutWorkItemStatus,
    PublicWorkoutWorkItemType,
)
from public_workouts.schema import validate_payload
from public_workouts.services import ProgramDraftReviewError, approve_and_publish_draft


def _json_lines(payload):
    if isinstance(payload, dict):
        payload = {key: value for key, value in payload.items() if key != 'program_id'}
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).splitlines()


class Command(BaseCommand):
    help = 'Mostra e, com aprovação explícita, publica um rascunho de treino Curva.'

    def add_arguments(self, parser):
        parser.add_argument('--draft-id', type=int, required=True)
        parser.add_argument(
            '--publish', action='store_true',
            help='Publica após as verificações; sem esta opção o comando é somente leitura.',
        )
        parser.add_argument(
            '--expected-active-version', type=int,
            help='Versão ativa revisada; use 0 se não há programa atualmente ativo.',
        )
        parser.add_argument(
            '--reviewed-by',
            help='Username Django da pessoa que aprovou (obrigatório com --publish).',
        )
        parser.add_argument(
            '--show-json', action='store_true',
            help='Imprime o payload JSON completo para revisão detalhada.',
        )

    def handle(self, *args, **options):
        draft_id = options['draft_id']
        try:
            draft = PublicWorkoutProgramDraft.objects.select_related(
                'base_program'
            ).get(pk=draft_id)
        except PublicWorkoutProgramDraft.DoesNotExist as exc:
            raise CommandError(f'Rascunho #{draft_id} não encontrado.') from exc

        active = PublicWorkoutProgram.objects.filter(
            slug=draft.slug, is_active=True
        ).first()
        subscription, onboarding_item = self._find_onboarding_item(draft.slug)
        errors = validate_payload(draft.payload)
        self._print_review(
            draft=draft,
            active=active,
            errors=errors,
            subscription=subscription,
            onboarding_item=onboarding_item,
            show_json=options['show_json'],
        )

        if errors:
            raise CommandError('Payload inválido; o rascunho não pode ser publicado.')
        if not options['publish']:
            self.stdout.write(self.style.SUCCESS('Revisão somente leitura concluída.'))
            return

        reviewer = self._resolve_reviewer(options.get('reviewed_by'))
        self._check_publish_guard(
            draft=draft,
            active=active,
            expected_version=options.get('expected_active_version'),
        )
        try:
            program = approve_and_publish_draft(draft_id=draft.pk, reviewed_by=reviewer)
        except ProgramDraftReviewError as exc:
            raise CommandError(str(exc)) from exc

        draft.refresh_from_db()
        active_after = PublicWorkoutProgram.objects.filter(
            slug=draft.slug, is_active=True
        ).first()
        if (
            active_after is None
            or active_after.pk != program.pk
            or draft.status != PublicWorkoutProgramDraftStatus.APPROVED
        ):
            raise CommandError(
                'A conferência pós-publicação falhou. Consulte as versões e o rascunho '
                'antes de tentar novamente.'
            )

        self.stdout.write(self.style.SUCCESS(
            f'Publicado: {draft.slug} v{program.version} (id={program.pk}); '
            f'rascunho #{draft.pk} aprovado por {reviewer.get_username()}.'
        ))
        if active is not None:
            active.refresh_from_db()
            self.stdout.write(f'Versão anterior: v{active.version}, ativa={active.is_active}.')
        self._print_onboarding_result(subscription=subscription, item=onboarding_item)
        self._print_outbox_state(program)

    def _resolve_reviewer(self, username):
        if not username:
            raise CommandError('--reviewed-by é obrigatório com --publish.')
        user_model = get_user_model()
        try:
            reviewer = user_model._default_manager.get(username=username)
        except user_model.DoesNotExist as exc:
            raise CommandError(f'Usuário revisor {username!r} não encontrado.') from exc
        if not reviewer.is_active or not reviewer.is_staff:
            raise CommandError('O revisor precisa estar ativo e ter acesso de equipe ao admin.')
        return reviewer

    def _check_publish_guard(self, *, draft, active, expected_version):
        if draft.status != PublicWorkoutProgramDraftStatus.PENDING_REVIEW:
            raise CommandError(f'Rascunho #{draft.pk} não está pendente: {draft.status}.')
        if expected_version is None or expected_version < 0:
            raise CommandError('--expected-active-version é obrigatório e não pode ser negativo.')
        if expected_version == 0:
            if active is not None or draft.base_program_id is not None:
                raise CommandError('Esperava nenhum programa ativo e um rascunho sem versão-base.')
            return
        if active is None or active.version != expected_version:
            current = 'nenhuma' if active is None else f'v{active.version}'
            raise CommandError(
                f'Versão ativa mudou: esperada v{expected_version}, atual {current}. '
                'Recrie o rascunho a partir da versão vigente.'
            )
        if draft.base_program_id != active.pk:
            raise CommandError(
                f'Rascunho baseado em #{draft.base_program_id}, mas a versão ativa é '
                f'#{active.pk}. Recrie o rascunho a partir da versão vigente.'
            )

    def _find_onboarding_item(self, slug):
        subscription = PublicWorkoutSubscription.objects.filter(plan_slug=slug).first()
        if subscription is None:
            return None, None
        item = PublicWorkoutWorkItem.objects.filter(
            subscription=subscription,
            item_type=PublicWorkoutWorkItemType.TRAINING_PROGRAM,
            cycle_key='onboarding',
            status__in=(
                PublicWorkoutWorkItemStatus.OPEN,
                PublicWorkoutWorkItemStatus.IN_PROGRESS,
                PublicWorkoutWorkItemStatus.BLOCKED,
            ),
        ).order_by('created_at').first()
        return subscription, item

    def _print_review(self, *, draft, active, errors, subscription, onboarding_item, show_json):
        base = draft.base_program
        self.stdout.write(f'Rascunho #{draft.pk} | {draft.slug} | {draft.status} | origem={draft.source}')
        if base is None:
            self.stdout.write('Base: nenhuma (primeira publicação).')
        else:
            self.stdout.write(f'Base: #{base.pk} v{base.version} | ativa={base.is_active}.')
        if active is None:
            self.stdout.write('Programa ativo: nenhum.')
        else:
            self.stdout.write(f'Programa ativo: #{active.pk} v{active.version}.')

        if subscription is None:
            self.stdout.write(self.style.WARNING('Nenhuma assinatura vinculada ao slug.'))
        elif onboarding_item is None:
            self.stdout.write(self.style.WARNING('Nenhum item de onboarding de treino ativo.'))
        else:
            self.stdout.write(f'Item de onboarding: #{onboarding_item.pk} {onboarding_item.status}.')

        if errors:
            self.stdout.write(self.style.ERROR('Schema: inválido'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
        else:
            self.stdout.write(self.style.SUCCESS('Schema: válido'))

        payload = draft.payload if isinstance(draft.payload, dict) else {}
        self.stdout.write(
            f"Plano: {payload.get('program_label')} | início={payload.get('started_on')} | "
            f"duração={payload.get('weeks')} semanas"
        )
        days = payload.get('days') if isinstance(payload.get('days'), list) else []
        for day in days:
            if not isinstance(day, dict):
                self.stdout.write(f'  [inválido] {_json_lines(day)[0]}')
                continue
            self.stdout.write(f"  [{day.get('day_id')}] {day.get('label')}")
            blocks = day.get('blocks') if isinstance(day.get('blocks'), list) else []
            for block in blocks:
                if not isinstance(block, dict) or not isinstance(block.get('movements'), list):
                    continue
                for movement in block['movements']:
                    if not isinstance(movement, dict):
                        continue
                    self.stdout.write(
                        f"    - {movement.get('name')} [{movement.get('movement_slug')}] | "
                        f"{movement.get('reps_spec')} | {movement.get('rir_spec', '')}"
                    )
        if show_json:
            self.stdout.write('Payload JSON:')
            self.stdout.write(json.dumps(draft.payload, ensure_ascii=False, indent=2, sort_keys=True))

        self.stdout.write('Diff versus base:')
        if base is None:
            self.stdout.write('  Primeira publicação; sem versão anterior para comparar.')
            return
        diff = list(difflib.unified_diff(
            _json_lines(base.payload),
            _json_lines(draft.payload),
            fromfile=f'base-v{base.version}',
            tofile='draft',
            lineterm='',
        ))
        if not diff:
            self.stdout.write('  Nenhuma diferença encontrada.')
        else:
            for line in diff:
                self.stdout.write(line)

    def _print_onboarding_result(self, *, subscription, item):
        if subscription is None:
            self.stdout.write(self.style.WARNING(
                'Sem assinatura vinculada; a versão foi publicada, sem aviso ao aluno.'
            ))
        elif item is None:
            self.stdout.write(self.style.WARNING(
                'Nenhum item de onboarding foi concluído; a versão continua ativa.'
            ))
        else:
            item.refresh_from_db()
            self.stdout.write(f'Item de onboarding após publicar: #{item.pk} {item.status}.')

    def _print_outbox_state(self, program):
        from public_workouts.outbox import TOPIC_PROGRAM_READY

        message = PublicWorkoutOutboxMessage.objects.filter(
            topic=TOPIC_PROGRAM_READY,
            aggregate_type='program',
            aggregate_id=program.pk,
            version=program.version,
        ).first()
        if message is None:
            self.stdout.write(self.style.WARNING('Evento program_ready não encontrado na outbox.'))
            return
        self.stdout.write(
            f'Outbox program_ready: {message.status} '
            f'(tentativas={message.attempt_count}; processado={message.processed_at or "—"}).'
        )
