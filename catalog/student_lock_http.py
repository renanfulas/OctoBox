"""
ARQUIVO: corredor HTTP de lock da ficha do aluno.

POR QUE ELE EXISTE:
- tira de student_views.py a orquestracao do heartbeat e da leitura de status do lock.

O QUE ESTE ARQUIVO FAZ:
1. resolve o heartbeat do lock com renovacao, furto ou reaquisição.
2. resolve a leitura simples do status do lock.
3. preserva o bypass de Dev e a degradacao segura do lock.

PONTOS CRITICOS:
- qualquer mudanca aqui altera concorrencia de edicao da ficha.
- os estados JSON precisam continuar estaveis para o frontend.
"""

from django.http import JsonResponse

from shared_support.editing_locks import acquire_student_lock, get_student_lock_status, refresh_student_lock


def handle_student_lock_heartbeat(*, student_id, user, role_slug: str | None):
    if not role_slug or role_slug == 'Dev':
        return JsonResponse({'status': 'dev_bypass'})

    refreshed = refresh_student_lock(student_id, user.id)
    if refreshed:
        return JsonResponse({'status': 'active', 'holder': 'self'})

    current = get_student_lock_status(student_id)
    if current:
        return JsonResponse(
            {
                'status': 'stolen',
                'holder': {
                    'user_display': current.get('user_display', ''),
                    'role_label': current.get('role_label', ''),
                },
            }
        )

    lock_result = acquire_student_lock(student_id, user, role_slug)
    if lock_result.acquired:
        return JsonResponse({'status': 'reacquired'})

    holder = lock_result.holder or {}
    return JsonResponse(
        {
            'status': 'blocked',
            'holder': {
                'user_display': holder.get('user_display', ''),
                'role_label': holder.get('role_label', ''),
            },
        }
    )


def build_student_lock_status_response(*, student_id, user_id: int):
    current = get_student_lock_status(student_id)
    if not current:
        return JsonResponse({'status': 'free'})
    if current.get('user_id') == user_id:
        return JsonResponse({'status': 'owner'})
    return JsonResponse(
        {
            'status': 'blocked',
            'holder': {
                'user_display': current.get('user_display', ''),
                'role_label': current.get('role_label', ''),
            },
        }
    )


__all__ = ['build_student_lock_status_response', 'handle_student_lock_heartbeat']
