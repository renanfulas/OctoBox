"""
ARQUIVO: fatos brutos da fundacao de churn financeiro.

POR QUE ELE EXISTE:
- separa coleta e reconciliacao de fatos operacionais da camada de heuristica.
"""

from __future__ import annotations

from decimal import Decimal

from finance.model_definitions import EnrollmentStatus, PaymentStatus


ZERO_MONEY = Decimal('0.00')


def normalize_datetime_to_date(value):
    if value is None:
        return None
    if hasattr(value, 'date'):
        return value.date()
    return value


def days_since(reference_date, value):
    normalized = normalize_datetime_to_date(value)
    if normalized is None:
        return None
    return max((reference_date - normalized).days, 0)


def is_payment_open(payment, *, today):
    return (
        payment.status in {PaymentStatus.PENDING, PaymentStatus.OVERDUE}
        and payment.due_date < today
    ) or (
        payment.status == PaymentStatus.OVERDUE
    )


def build_student_churn_facts(
    *,
    student,
    student_payments,
    student_enrollments,
    student_messages,
    today,
):
    open_amount = ZERO_MONEY
    overdue_days_sum = 0
    overdue_counter = 0
    overdue_30d = 0
    overdue_60d = 0
    overdue_90d = 0
    first_overdue_date = None
    first_overdue_payment_id = None
    last_paid_at = None
    paid_payment_count = 0

    for payment in student_payments:
        if payment.status == PaymentStatus.PAID:
            paid_payment_count += 1
            payment_paid_at = payment.paid_at or payment.due_date
            if last_paid_at is None or payment_paid_at > last_paid_at:
                last_paid_at = payment_paid_at

        if not is_payment_open(payment, today=today):
            continue

        overdue_days = max((today - payment.due_date).days, 0)
        open_amount += payment.amount or ZERO_MONEY
        overdue_days_sum += overdue_days
        overdue_counter += 1
        if first_overdue_date is None or payment.due_date < first_overdue_date:
            first_overdue_date = payment.due_date
            first_overdue_payment_id = payment.id
        if overdue_days <= 30:
            overdue_30d += 1
        if overdue_days <= 60:
            overdue_60d += 1
        if overdue_days <= 90:
            overdue_90d += 1

    latest_enrollment = student_enrollments[-1] if student_enrollments else None
    latest_enrollment_start_date = getattr(latest_enrollment, 'start_date', None)
    latest_enrollment_status = getattr(latest_enrollment, 'status', '')
    latest_enrollment_end_date = getattr(latest_enrollment, 'end_date', None)
    reactivated_after_inactive = student.status != 'inactive' and any(
        enrollment.status in {EnrollmentStatus.CANCELED, EnrollmentStatus.EXPIRED}
        for enrollment in student_enrollments[:-1]
    ) and latest_enrollment_status == EnrollmentStatus.ACTIVE

    latest_finance_touch = student_messages[0] if student_messages else None
    latest_finance_touch_at = getattr(latest_finance_touch, 'delivered_at', None) or getattr(latest_finance_touch, 'created_at', None)
    latest_finance_touch_payload = getattr(latest_finance_touch, 'raw_payload', {}) or {}
    finance_touches_30d = sum(
        1
        for message in student_messages
        if days_since(today, getattr(message, 'delivered_at', None) or getattr(message, 'created_at', None)) is not None
        and days_since(today, getattr(message, 'delivered_at', None) or getattr(message, 'created_at', None)) <= 30
    )

    return {
        'open_amount': open_amount,
        'overdue_days_sum': overdue_days_sum,
        'overdue_counter': overdue_counter,
        'overdue_30d': overdue_30d,
        'overdue_60d': overdue_60d,
        'overdue_90d': overdue_90d,
        'first_overdue_date': first_overdue_date,
        'first_overdue_payment_id': first_overdue_payment_id,
        'last_paid_at': last_paid_at,
        'paid_payment_count': paid_payment_count,
        'latest_enrollment': latest_enrollment,
        'latest_enrollment_start_date': latest_enrollment_start_date,
        'latest_enrollment_status': latest_enrollment_status,
        'latest_enrollment_end_date': latest_enrollment_end_date,
        'reactivated_after_inactive': reactivated_after_inactive,
        'latest_finance_touch_at': latest_finance_touch_at,
        'latest_finance_touch_payload': latest_finance_touch_payload,
        'finance_touches_30d': finance_touches_30d,
    }


__all__ = [
    'ZERO_MONEY',
    'build_student_churn_facts',
    'days_since',
]
