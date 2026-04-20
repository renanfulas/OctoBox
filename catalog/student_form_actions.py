"""
Corredor de ações e validações operacionais das views de ficha do aluno.
"""

from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponseForbidden

from access.roles import ROLE_DEV, get_user_role
from catalog.services.student_workflows import (
    run_student_express_create_workflow,
    run_student_quick_create_workflow,
    run_student_quick_update_workflow,
)
from monitoring.student_realtime_metrics import record_student_save_conflict
from shared_support.editing_locks import acquire_student_lock, get_student_lock_status, release_student_lock
from shared_support.student_event_stream import publish_student_stream_event
from shared_support.student_snapshot_versions import build_profile_version


def enforce_student_creation_throttle(*, request, view):
    from shared_support.security.anti_cheat_throttles import StudentCreationSpamThrottle

    throttle = StudentCreationSpamThrottle()
    if throttle.allow_request(request, view):
        return None

    throttle.on_throttle_exceeded(request, view)
    return HttpResponseForbidden("Limite de criacao atingido. Tente novamente em 1 hora.")


def execute_student_quick_create(*, request, form, selected_intake):
    try:
        workflow = run_student_quick_create_workflow(
            actor=request.user,
            form=form,
            selected_intake=selected_intake,
        )
    except IntegrityError as exc:
        if "phone_lookup_index" not in str(exc):
            raise
        form.add_error("phone", "Ja existe um aluno cadastrado com este WhatsApp.")
        return None

    student = workflow["student"]
    messages.success(request, f"Aluno {student.full_name} cadastrado com sucesso.")
    return student


def execute_student_express_create(*, request, form, append_fragment, financial_fragment, reverse):
    workflow = run_student_express_create_workflow(
        actor=request.user,
        form=form,
    )
    student = workflow["student"]
    messages.success(request, f"Cadastro Expresso: {student.full_name} pronto para vinculacao financeira!")
    return append_fragment(reverse("student-quick-update", args=[student.id]), financial_fragment)


def resolve_student_quick_update_lock_holder(*, request, student):
    role = get_user_role(request.user)
    role_slug = getattr(role, "slug", None)
    if not role_slug or role_slug == ROLE_DEV:
        return None

    current_lock = get_student_lock_status(student.id)
    if current_lock and current_lock.get("user_id") != request.user.id:
        return current_lock
    return None


def execute_student_quick_update(
    *,
    request,
    student,
    form,
    selected_intake,
    append_fragment,
    form_fragment,
    reverse,
):
    role = get_user_role(request.user)
    role_slug = getattr(role, "slug", None)
    request_profile_version = request.POST.get("profile_version", "")

    if role_slug and role_slug != ROLE_DEV:
        current_lock = get_student_lock_status(student.id)
        if not current_lock or current_lock.get("user_id") != request.user.id:
            if not current_lock:
                lock_result = acquire_student_lock(student.id, request.user, role_slug)
                if not lock_result.acquired:
                    messages.error(
                        request,
                        "A edicao desta ficha nao esta reservada para voce agora. Entre em modo de edicao novamente antes de salvar.",
                    )
                    return append_fragment(reverse("student-quick-update", args=[student.id]), form_fragment)
            else:
                holder = current_lock
                messages.error(
                    request,
                    f"{holder.get('user_display', 'Outro usuario')} ({holder.get('role_label', '')}) "
                    f"assumiu a edicao deste aluno enquanto voce preenchia. "
                    f"Suas alteracoes nao foram salvas. Fale com ele para coordenar.",
                )
                return append_fragment(reverse("student-quick-update", args=[student.id]), form_fragment)

    current_profile_version = build_profile_version(student)
    if request_profile_version and current_profile_version and request_profile_version != current_profile_version:
        record_student_save_conflict("student-form")
        messages.error(
            request,
            "A ficha mudou antes do seu salvar. Reabrimos a leitura oficial para evitar sobrescrever informacao mais nova.",
        )
        return append_fragment(reverse("student-quick-update", args=[student.id]), form_fragment)

    workflow = run_student_quick_update_workflow(
        actor=request.user,
        form=form,
        changed_fields=list(form.changed_data),
        selected_intake=selected_intake,
    )
    updated_student = workflow["student"]

    if role_slug and role_slug != ROLE_DEV:
        release_student_lock(updated_student.id, request.user.id)
        publish_student_stream_event(
            student_id=updated_student.id,
            event_type="student.lock.released",
            meta={
                "holder": {
                    "user_display": request.user.get_full_name() or request.user.username,
                },
                "reason": "student_form_saved",
            },
        )

    messages.success(request, f"Cadastro de {updated_student.full_name} atualizado com sucesso.")
    return updated_student


def execute_student_drawer_profile_save(
    *,
    request,
    student,
    form,
    build_drawer_response,
):
    role = get_user_role(request.user)
    role_slug = getattr(role, "slug", None)
    request_profile_version = request.POST.get("profile_version", "")

    if role_slug and role_slug != ROLE_DEV:
        current_lock = get_student_lock_status(student.id)
        if not current_lock or current_lock.get("user_id") != request.user.id:
            holder = current_lock or {}
            return 409, build_drawer_response(
                request=request,
                student=student,
                form=form,
                status="error",
                message=(
                    f"{holder.get('user_display', 'Outro usuario')} ({holder.get('role_label', '')}) esta com a edicao desta ficha."
                    if current_lock
                    else "Entre em modo de edicao novamente antes de salvar."
                ),
            )

    current_profile_version = build_profile_version(student)
    if request_profile_version and current_profile_version and request_profile_version != current_profile_version:
        record_student_save_conflict("drawer-profile")
        return 409, build_drawer_response(
            request=request,
            student=student,
            form=form,
            status="conflict",
            message="A ficha mudou antes do seu salvar. Atualizamos a leitura oficial para evitar conflito.",
        )

    if not form.is_valid():
        return 400, build_drawer_response(
            request=request,
            student=student,
            form=form,
            status="error",
            message="Revise os campos destacados antes de salvar.",
        )

    workflow = run_student_quick_update_workflow(
        actor=request.user,
        form=form,
        changed_fields=list(form.changed_data),
        selected_intake=None,
    )
    updated_student = workflow["student"]

    if role_slug and role_slug != ROLE_DEV:
        release_student_lock(updated_student.id, request.user.id)
        publish_student_stream_event(
            student_id=updated_student.id,
            event_type="student.lock.released",
            meta={
                "holder": {
                    "user_display": request.user.get_full_name() or request.user.username,
                },
                "reason": "profile_saved",
            },
        )

    return 200, build_drawer_response(
        request=request,
        student=updated_student,
        form=None,
        status="success",
        message=f"Perfil de {updated_student.full_name} atualizado com sucesso.",
    )
