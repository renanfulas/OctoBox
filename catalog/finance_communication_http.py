"""
ARQUIVO: corredor HTTP da comunicacao financeira.

POR QUE ELE EXISTE:
- tira de `catalog/views/finance_views.py` a orquestracao de form, auditoria e streams.
"""

from datetime import timedelta

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone

from access.roles import ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from auditing import log_audit_event
from auditing.models import AuditEvent
from catalog.forms import FinanceCommunicationActionForm
from catalog.services.finance_communication_actions import handle_finance_communication_action
from finance.models import Payment
from shared_support.cascade.contracts import build_cascade_intent, merge_cascade_metadata
from shared_support.cascade.ownership import resolve_actor_box_id, resolve_box_owner_user_id
from shared_support.manager_event_stream import publish_manager_stream_event
from shared_support.operational_contact_memory import (
    CONTACT_COOLDOWN_DAYS,
    CONTACT_OWNERSHIP_MANAGER_OWNER,
    CONTACT_STAGE_FIRST_TOUCH_OPENED,
    CONTACT_STAGE_FOLLOW_UP_ACTIVE,
    CONTACT_STAGE_UNREACHED,
    FINANCE_CONTACT_ACTIONS,
    MANAGER_FINANCE_WHATSAPP_ACTION,
    OWNER_FINANCE_WHATSAPP_ACTION,
    RECEPTION_FINANCE_WHATSAPP_ACTION,
    build_contact_memory_metadata,
)
from shared_support.operational_settings import get_operational_whatsapp_repeat_block_hours
from shared_support.student_event_stream import publish_student_stream_event


def handle_finance_communication_view_post(*, request):
    open_in_whatsapp = request.POST.get('open_in_whatsapp') == '1'
    form = FinanceCommunicationActionForm(request.POST)
    if not form.is_valid():
        messages.error(
            request,
            'A acao de comunicacao nao foi registrada. Revise os dados do contato operacional.',
        )
        return redirect('finance-center')

    result = handle_finance_communication_action(
        actor=request.user,
        action_kind=form.cleaned_data['action_kind'],
        student_id=form.cleaned_data['student_id'],
        payment_id=form.cleaned_data.get('payment_id'),
        enrollment_id=form.cleaned_data.get('enrollment_id'),
    )
    if result['blocked']:
        repeat_block_hours = get_operational_whatsapp_repeat_block_hours()
        if repeat_block_hours:
            messages.warning(
                request,
                (
                    f'Contato de WhatsApp ja registrado nas ultimas {repeat_block_hours}h para '
                    f'{result["student"].full_name}. Aguarde a proxima janela antes de repetir a mesma acao.'
                ),
            )
        else:
            messages.warning(
                request,
                f'Contato de WhatsApp repetido bloqueado para {result["student"].full_name}.',
            )
        return redirect('finance-center')

    payment_id = form.cleaned_data.get('payment_id')
    prior_touch_exists = False
    if payment_id:
        prior_touch_exists = AuditEvent.objects.filter(
            action__in=FINANCE_CONTACT_ACTIONS,
            target_model='payment',
            target_id=str(payment_id),
        ).exists()

    role_action_map = {
        ROLE_MANAGER: MANAGER_FINANCE_WHATSAPP_ACTION,
        ROLE_RECEPTION: RECEPTION_FINANCE_WHATSAPP_ACTION,
        ROLE_OWNER: OWNER_FINANCE_WHATSAPP_ACTION,
    }
    current_role = get_user_role(request.user)
    current_role_slug = getattr(current_role, 'slug', '')
    action_name = role_action_map.get(current_role_slug, MANAGER_FINANCE_WHATSAPP_ACTION)
    stage_before = CONTACT_STAGE_UNREACHED if not prior_touch_exists else CONTACT_STAGE_FOLLOW_UP_ACTIVE
    stage_after = CONTACT_STAGE_FIRST_TOUCH_OPENED if not prior_touch_exists else CONTACT_STAGE_FOLLOW_UP_ACTIVE
    cooldown_until = (timezone.now() + timedelta(days=CONTACT_COOLDOWN_DAYS)).isoformat()
    payment = Payment.objects.filter(pk=payment_id).first() if payment_id else None
    enrollment_id = form.cleaned_data.get('enrollment_id')
    audit_target = payment or result['student']
    box_id = resolve_actor_box_id(request.user)
    cascade_intent = build_cascade_intent(
        box_id=box_id,
        owner_user_id=resolve_box_owner_user_id(box_id),
        requested_by_user_id=request.user.id,
        requested_by_role=current_role_slug or ROLE_MANAGER,
        subject_type='payment' if payment_id else 'student',
        subject_id=payment_id or result['student'].id,
        action_kind=f'finance_{form.cleaned_data["action_kind"]}_whatsapp',
        channel='whatsapp',
        surface=current_role_slug or 'finance',
    )

    log_audit_event(
        actor=request.user,
        action=action_name,
        target=audit_target,
        description=f'Contato de cobranca aberto por WhatsApp para {result["student"].full_name}.',
        metadata=merge_cascade_metadata(
            build_contact_memory_metadata(
                board_key='finance',
                channel='whatsapp',
                subject_type='payment' if payment_id else 'student',
                subject_id=payment_id or result['student'].id,
                subject_label=result['student'].full_name,
                student_id=result['student'].id,
                payment_id=payment_id,
                intake_id=None,
                stage_before=stage_before,
                stage_after=stage_after,
                ownership_scope=CONTACT_OWNERSHIP_MANAGER_OWNER,
                cooldown_until=cooldown_until,
                is_first_touch=not prior_touch_exists,
            ),
            intent=cascade_intent,
        ),
    )
    publish_manager_stream_event(
        event_type='student.payment.updated',
        meta={
            'student_id': result['student'].id,
            'payment_id': payment_id,
            'enrollment_id': enrollment_id,
            'action': action_name,
        },
    )
    publish_student_stream_event(
        student_id=result['student'].id,
        event_type='student.payment.updated',
        meta={
            'payment_id': payment_id,
            'action': action_name,
        },
    )

    if open_in_whatsapp and result['whatsapp_href']:
        return redirect(result['whatsapp_href'])

    messages.success(request, f'Contato operacional registrado para {result["student"].full_name}.')
    return redirect('finance-center')
