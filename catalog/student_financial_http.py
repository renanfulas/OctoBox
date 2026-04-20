"""
ARQUIVO: corredor HTTP financeiro da ficha do aluno.

POR QUE ELE EXISTE:
- tira de student_views.py a orquestracao de pagamento e matricula sem tocar ainda no restante da ficha.

O QUE ESTE ARQUIVO FAZ:
1. centraliza o contrato JSON do overview financeiro.
2. executa actions de pagamento com locking e mensagens consistentes.
3. executa actions de matricula com locking e mensagens consistentes.
4. oferece redirects padrao para o fragmento financeiro da ficha.

PONTOS CRITICOS:
- qualquer mudanca aqui altera cobranca, recebimento, matricula e a experiencia AJAX do painel financeiro.
- os codigos HTTP e mensagens precisam continuar identicos ao corredor anterior.
"""

from django.contrib import messages
from django.db import DatabaseError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from access.roles import ROLE_RECEPTION, get_user_role
from catalog.forms import EnrollmentManagementForm, PaymentManagementForm, StudentPaymentActionForm
from catalog.presentation.student_financial_fragments import render_student_financial_fragments
from catalog.services.student_enrollment_actions import handle_student_enrollment_action
from catalog.services.student_payment_actions import handle_student_payment_action, handle_student_payment_creation
from finance.models import Enrollment, Payment


STUDENT_FINANCIAL_FRAGMENT = 'student-financial-overview'


def expects_student_financial_json_response(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def build_student_financial_json_response(
    *,
    request,
    student,
    message,
    selected_payment=None,
    standalone_payment=False,
    status=200,
):
    return JsonResponse(
        {
            'status': 'success',
            'message': message,
            'selected_payment_id': getattr(selected_payment, 'id', None),
            'fragments': render_student_financial_fragments(
                student,
                request=request,
                selected_payment=selected_payment,
                standalone_payment=standalone_payment,
            ),
        },
        status=status,
    )


def build_student_financial_json_error(*, message, status=400):
    return JsonResponse(
        {
            'status': 'error',
            'message': message,
        },
        status=status,
    )


def redirect_to_student_financial_overview(*, student_id):
    return redirect(f"{reverse('student-quick-update', args=[student_id])}#{STUDENT_FINANCIAL_FRAGMENT}")


def handle_student_payment_action_request(*, request, student):
    expects_json = expects_student_financial_json_response(request)
    action_form = StudentPaymentActionForm(request.POST)
    if not action_form.is_valid():
        return _payment_error_response(
            request=request,
            student=student,
            expects_json=expects_json,
            message='A acao financeira enviada para o aluno nao e valida neste fluxo.',
            status=400,
        )

    action = action_form.cleaned_data['action']
    if action == 'create-payment':
        return _handle_student_payment_creation_request(
            request=request,
            student=student,
            expects_json=expects_json,
        )

    try:
        with transaction.atomic():
            payment = get_object_or_404(
                Payment.objects.select_for_update(nowait=True),
                pk=action_form.cleaned_data['payment_id'],
                student=student,
            )
    except DatabaseError:
        return _payment_error_response(
            request=request,
            student=student,
            expects_json=expects_json,
            message='Esta operacao financeira esta sendo processada em outra aba ou por outro administrador. Tente novamente em 15 segundos.',
            status=409,
        )

    restricted_actions = {'refund-payment', 'cancel-payment', 'regenerate-payment'}
    if action in restricted_actions and getattr(get_user_role(request.user), 'slug', '') == ROLE_RECEPTION:
        return _payment_error_response(
            request=request,
            student=student,
            expects_json=expects_json,
            message='A Recepcao so pode salvar cobranca ou confirmar pagamento neste fluxo.',
            status=403,
        )

    if action == 'update-payment':
        form = PaymentManagementForm(request.POST)
        if not form.is_valid():
            return _payment_error_response(
                request=request,
                student=student,
                expects_json=expects_json,
                message='A cobranca nao foi atualizada. Revise valor, vencimento e campos enviados.',
                status=400,
            )
        updated_payment = handle_student_payment_action(
            actor=request.user,
            student=student,
            payment=payment,
            action=action,
            payload=form.cleaned_data,
        )
        if updated_payment is not None:
            payment = updated_payment
        success_message = 'Cobranca atualizada com sucesso.'
    else:
        updated_payment = handle_student_payment_action(
            actor=request.user,
            student=student,
            payment=payment,
            action=action,
        )
        if updated_payment is not None:
            payment = updated_payment
        action_success_messages = {
            'mark-paid': 'Pagamento registrado com sucesso.',
            'refund-payment': 'Estorno registrado com sucesso.',
            'cancel-payment': 'Cobranca cancelada com sucesso.',
            'regenerate-payment': 'Cobranca regenerada com sucesso.',
        }
        success_message = action_success_messages.get(action, 'Acao financeira concluida com sucesso.')

    if expects_json:
        return build_student_financial_json_response(
            request=request,
            student=student,
            message=success_message,
            selected_payment=payment,
        )

    messages.success(request, success_message)
    return redirect_to_student_financial_overview(student_id=student.id)


def handle_student_enrollment_action_request(*, request, student):
    expects_json = expects_student_financial_json_response(request)
    form = EnrollmentManagementForm(request.POST)
    if not form.is_valid():
        return _enrollment_error_response(
            request=request,
            student=student,
            expects_json=expects_json,
            message='A acao de matricula nao foi aplicada. Revise os campos enviados.',
            status=400,
        )

    try:
        with transaction.atomic():
            enrollment = get_object_or_404(
                Enrollment.objects.select_for_update(nowait=True),
                pk=form.cleaned_data['enrollment_id'],
                student=student,
            )
    except DatabaseError:
        return _enrollment_error_response(
            request=request,
            student=student,
            expects_json=expects_json,
            message='Esta matricula está bloqueada para alteracao no momento (outra operacao em curso).',
            status=409,
        )

    if form.cleaned_data['action'] == 'cancel-enrollment' and enrollment.status != 'active':
        return _enrollment_error_response(
            request=request,
            student=student,
            expects_json=expects_json,
            message='Esta matricula já se encontra inativa ou cancelada.',
            status=400,
        )

    handle_student_enrollment_action(
        actor=request.user,
        student=student,
        enrollment=enrollment,
        action=form.cleaned_data['action'],
        action_date=form.cleaned_data['action_date'],
        reason=form.cleaned_data['reason'],
    )

    action_success_messages = {
        'cancel-enrollment': 'Matricula cancelada com sucesso.',
        'reactivate-enrollment': 'Matricula reativada com sucesso.',
    }
    success_message = action_success_messages.get(form.cleaned_data['action'], 'Acao de matricula concluida com sucesso.')

    if expects_json:
        return build_student_financial_json_response(
            request=request,
            student=student,
            message=success_message,
        )

    messages.success(request, success_message)
    return redirect_to_student_financial_overview(student_id=student.id)


def _handle_student_payment_creation_request(*, request, student, expects_json: bool):
    form = PaymentManagementForm(request.POST)
    if not form.is_valid():
        return _payment_error_response(
            request=request,
            student=student,
            expects_json=expects_json,
            message='A cobranca avulsa nao foi registrada. Revise valor, vencimento e campos enviados.',
            status=400,
        )

    new_payment = handle_student_payment_creation(
        actor=request.user,
        student=student,
        payload=form.cleaned_data,
    )
    if new_payment:
        success_message = 'Cobranca avulsa criada e recebimento confirmado via Balcao.'
        if expects_json:
            return build_student_financial_json_response(
                request=request,
                student=student,
                message=success_message,
                selected_payment=new_payment,
            )
        messages.success(request, success_message)
        return redirect_to_student_financial_overview(student_id=student.id)

    return _payment_error_response(
        request=request,
        student=student,
        expects_json=expects_json,
        message='Erro ao criar cobranca avulsa.',
        status=400,
    )


def _payment_error_response(*, request, student, expects_json: bool, message: str, status: int):
    if expects_json:
        return build_student_financial_json_error(message=message, status=status)
    messages.error(request, message)
    return redirect_to_student_financial_overview(student_id=student.id)


def _enrollment_error_response(*, request, student, expects_json: bool, message: str, status: int):
    if expects_json:
        return build_student_financial_json_error(message=message, status=status)
    messages.error(request, message)
    return redirect_to_student_financial_overview(student_id=student.id)


__all__ = [
    'STUDENT_FINANCIAL_FRAGMENT',
    'build_student_financial_json_error',
    'build_student_financial_json_response',
    'expects_student_financial_json_response',
    'handle_student_enrollment_action_request',
    'handle_student_payment_action_request',
    'redirect_to_student_financial_overview',
]
