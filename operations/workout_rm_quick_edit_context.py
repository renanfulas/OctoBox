"""
ARQUIVO: contexto e payload da tela de RM rapido.

POR QUE ELE EXISTE:
- tira da view a montagem visual e o contexto da tela de RM rapido sem criar acoplamento extra.

O QUE ESTE ARQUIVO FAZ:
1. monta o payload visual da tela.
2. monta o contexto final com workout, aluno e RM atual.
3. injeta os kwargs do formulario.

PONTOS CRITICOS:
- manter contrato de template e copy identicos ao fluxo anterior.
- aqui mora apresentacao leve, nao mutacao.
"""

from django.urls import reverse

from shared_support.page_payloads import attach_page_payload, build_page_hero
from shared_support.page_payloads import build_page_assets, build_page_payload


def build_workout_student_rm_quick_edit_form_kwargs(view):
    form_kwargs = super(type(view), view).get_form_kwargs()
    form_kwargs['instance'] = view.rm_record
    form_kwargs['exercise_label'] = view.exercise_label
    return form_kwargs


def build_workout_student_rm_quick_edit_page_payload(view, context):
    payload = build_page_payload(
        context={
            'page_key': 'operations-workout-student-rm-quick-edit',
            'title': view.page_title,
            'subtitle': view.page_subtitle,
            'mode': 'workspace',
            'role_slug': context['current_role'].slug,
        },
        data={
            'hero': build_page_hero(
                eyebrow='RM operacional',
                title=f'{view.student.full_name} · {view.exercise_label}',
                copy='Aqui voce registra o RM real do aluno e devolve essa informacao para o corredor do WOD, como quem entrega a chave certa para a porta certa.',
                actions=[
                    {
                        'label': 'Voltar para a board',
                        'href': reverse('workout-approval-board') + '#rm-gap-queue',
                        'kind': 'secondary',
                    },
                ],
                aria_label='Cadastro rapido de RM do aluno',
                classes=['coach-hero'],
                data_panel='coach-hero',
                actions_slot='coach-hero-actions',
            ),
        },
        behavior={
            'surface_key': 'operations-workout-student-rm-quick-edit',
            'scope': 'operations-approval',
        },
        assets=build_page_assets(css=['css/design-system/operations.css']),
    )
    attach_page_payload(context, payload_key='operation_page', payload=payload)
    return payload


def build_workout_student_rm_quick_edit_context(view, **kwargs):
    context = super(type(view), view).get_context_data(**kwargs)
    context.update(view.get_base_context())
    build_workout_student_rm_quick_edit_page_payload(view, context)
    context['workout'] = view.workout
    context['student'] = view.student
    context['exercise_slug'] = view.exercise_slug
    context['exercise_label'] = view.exercise_label
    context['rm_record'] = view.rm_record
    return context


__all__ = [
    'build_workout_student_rm_quick_edit_context',
    'build_workout_student_rm_quick_edit_form_kwargs',
    'build_workout_student_rm_quick_edit_page_payload',
]
