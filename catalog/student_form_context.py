"""
Corredor de contexto e pré-preenchimento das views de ficha do aluno.
"""

from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from catalog.forms import EnrollmentManagementForm, PaymentManagementForm
from catalog.presentation import build_student_form_page
from catalog.presentation.shared import attach_catalog_page_payload
from catalog.student_queries import build_student_financial_snapshot, get_operational_enrollment
from onboarding.attribution import extract_acquisition_channel
from onboarding.models import StudentIntake


def resolve_selected_intake(request):
    intake_id = request.GET.get("intake") if request.method == "GET" else request.POST.get("intake_record")
    if not intake_id:
        return None
    return StudentIntake.objects.filter(pk=intake_id).first()


def build_student_quick_initial(*, initial, selected_intake, page_mode):
    if not selected_intake or page_mode != "create":
        return initial

    intake_raw_payload = getattr(selected_intake, "raw_payload", {}) or {}
    intake_channel = extract_acquisition_channel(
        raw_payload=intake_raw_payload,
        fallback_source=getattr(selected_intake, "source", ""),
    )
    intake_detail = ((intake_raw_payload.get("attribution") or {}).get("acquisition") or {}).get("declared_detail", "")
    initial.update(
        {
            "full_name": selected_intake.full_name,
            "phone": selected_intake.phone,
            "email": selected_intake.email,
            "intake_record": selected_intake,
            "acquisition_source": intake_channel,
            "acquisition_source_detail": intake_detail,
        }
    )
    return initial


def build_student_payment_management_form(student):
    if not student:
        return None
    latest_payment = student.payments.order_by("-due_date", "-created_at").first()
    if latest_payment is None:
        return PaymentManagementForm(
            initial={
                "amount": "",
                "due_date": timezone.localdate().strftime("%d/%m/%Y"),
            }
        )

    return PaymentManagementForm(
        instance=latest_payment,
        initial={
            "payment_id": latest_payment.id,
            "amount": latest_payment.amount,
            "due_date": latest_payment.due_date,
            "method": latest_payment.method,
            "reference": latest_payment.reference,
            "notes": latest_payment.notes,
        },
    )


def build_student_enrollment_management_form(student):
    if not student:
        return None
    latest_enrollment = get_operational_enrollment(student)
    if latest_enrollment is None:
        return None
    return EnrollmentManagementForm(
        initial={
            "enrollment_id": latest_enrollment.id,
            "action_date": timezone.localdate(),
        }
    )


def build_student_quick_page_context(
    *,
    request,
    context,
    base_context,
    form,
    student_object,
    page_mode,
    build_browser_snapshot,
    build_return_context,
    build_source_capture_url,
):
    selected_intake = resolve_selected_intake(request)
    financial_overview = build_student_financial_snapshot(student_object)
    role_slug = base_context["current_role"].slug
    financial_overview["payment_management_form"] = (
        build_student_payment_management_form(student_object)
        if role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
        else None
    )
    financial_overview["enrollment_management_form"] = (
        build_student_enrollment_management_form(student_object)
        if role_slug in (ROLE_OWNER, ROLE_MANAGER)
        else None
    )
    page_payload = build_student_form_page(
        form=form,
        student_object=student_object,
        selected_intake=selected_intake,
        financial_overview=financial_overview,
        page_mode=page_mode,
        current_role_slug=role_slug,
        browser_snapshot=build_browser_snapshot(request=request, student=student_object) if student_object else None,
        return_context=build_return_context(request),
    )
    if student_object is not None:
        page_payload["data"]["source_snapshot"]["capture_url"] = build_source_capture_url(request=request, student=student_object)

    return attach_catalog_page_payload(
        context,
        payload_key="student_form_page",
        payload=page_payload,
        include_sections=("context", "shell"),
    )


def build_student_express_page_context(*, context):
    return attach_catalog_page_payload(
        context,
        payload_key="student_express_page",
        payload={
            "data": {
                "hero": {
                    "title": "Checkout Rapido (Balcao)",
                    "subtitle": "Nome e Zap para fechar a venda agora.",
                    "icon": "zap",
                    "back_url": reverse("student-directory"),
                }
            }
        },
        include_sections=("context", "shell"),
    )


def build_student_drawer_profile_response(
    *,
    request,
    student,
    message,
    status,
    build_browser_snapshot,
    build_drawer_fragments,
    form=None,
):
    return {
        "status": status,
        "message": message,
        "snapshot": build_browser_snapshot(request=request, student=student),
        "fragments": build_drawer_fragments(request=request, student=student, form=form),
    }
