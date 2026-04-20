"""
Corredor de leitura do drawer do aluno.

Concentra snapshot enxuto e fragments oficiais da ficha para que as views
de leitura parcial permaneçam finas.
"""

from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_RECEPTION, get_user_role
from catalog.forms import StudentQuickForm
from catalog.presentation import build_student_form_page
from catalog.student_queries import build_student_financial_snapshot
from shared_support.editing_locks import get_student_lock_status
from shared_support.student_snapshot_versions import build_profile_version, build_student_snapshot_version


def build_student_browser_snapshot(*, request, student, financial_fragment, build_source_capture_url, append_fragment):
    financial_overview = build_student_financial_snapshot(student)
    latest_enrollment = financial_overview.get("latest_enrollment")
    latest_payment = next(iter(financial_overview.get("payments") or []), None)
    current_lock = get_student_lock_status(student.id)
    snapshot_version = build_student_snapshot_version(
        student=student,
        latest_enrollment=latest_enrollment,
        latest_payment=latest_payment,
    )
    profile_version = build_profile_version(student)

    if not current_lock:
        lock_payload = {"status": "free"}
    elif current_lock.get("user_id") == request.user.id:
        lock_payload = {"status": "owner"}
    else:
        lock_payload = {
            "status": "blocked",
            "holder": {
                "user_display": current_lock.get("user_display", ""),
                "role_label": current_lock.get("role_label", ""),
            },
        }

    return {
        "id": student.id,
        "full_name": student.full_name,
        "email": student.email or "",
        "phone": student.phone or "",
        "status": student.status,
        "financial": {
            "latest_plan_name": latest_enrollment.plan.name if latest_enrollment and getattr(latest_enrollment, "plan", None) else "",
            "latest_payment_status": getattr(latest_payment, "status", "") or "",
            "latest_payment_due_date": latest_payment.due_date.isoformat() if getattr(latest_payment, "due_date", None) else "",
            "overdue_count": financial_overview.get("metrics", {}).get("pagamentos_atrasados", 0),
            "pending_count": financial_overview.get("metrics", {}).get("pagamentos_pendentes", 0),
        },
        "presence": {
            "percent_30d": financial_overview.get("metrics", {}).get("presenca_percentual_30d", 0) or 0,
        },
        "snapshot_version": snapshot_version,
        "profile_version": profile_version,
        "lock": lock_payload,
        "links": {
            "edit": append_fragment(reverse("student-quick-update", args=[student.id]), financial_fragment),
            "source_capture": build_source_capture_url(request=request, student=student),
        },
        "generated_at": timezone.now().isoformat(),
        "source": "backend-snapshot",
    }


def build_student_drawer_fragments(
    *,
    request,
    student,
    form,
    build_browser_snapshot,
    build_source_capture_url,
):
    role = get_user_role(request.user)
    role_slug = getattr(role, "slug", ROLE_RECEPTION)
    financial_overview = build_student_financial_snapshot(student)
    page = build_student_form_page(
        form=form or StudentQuickForm(instance=student),
        student_object=student,
        selected_intake=None,
        financial_overview=financial_overview,
        page_mode="update",
        current_role_slug=role_slug,
        browser_snapshot=build_browser_snapshot(request=request, student=student),
    )
    page["context"]["surface_mode"] = "drawer"
    page["data"]["source_snapshot"]["capture_url"] = build_source_capture_url(request=request, student=student)
    context = {"page": page}

    return {
        "profile": render_to_string("includes/catalog/student_page/student_page_profile_panel.html", context=context, request=request),
        "financial": render_to_string("catalog/includes/student/student_quick_panel_financial.html", context=context, request=request),
    }


def build_student_snapshot_response(*, request, student, build_browser_snapshot):
    return {
        "status": "ok",
        "snapshot": build_browser_snapshot(request=request, student=student),
    }


def build_student_drawer_fragments_response(*, request, student, build_browser_snapshot, build_fragments):
    return {
        "status": "ok",
        "snapshot": build_browser_snapshot(request=request, student=student),
        "fragments": build_fragments(request=request, student=student, form=None),
    }
