"""Resolve the tenant touched by each Stripe webhook event family."""

from __future__ import annotations

from typing import Callable


def tenant_schema_for_event(
    event,
    resolve_box_schema: Callable,
    extract_billing_ids: Callable,
    resolve_box_for_billing: Callable,
    lookup_payment_ref: Callable,
) -> str:
    obj = ((event.payload or {}).get('data') or {}).get('object') or {}
    if event.event_type.startswith('checkout.session.'):
        metadata = obj.get('metadata') or {}
        if metadata.get('pending_signup_id'):
            return ''
        if metadata.get('payment_id'):
            return resolve_box_schema(metadata.get('box_schema'), event)
        return ''

    if event.event_type in {
        'invoice.payment_failed', 'invoice.payment_succeeded', 'customer.subscription.deleted',
    }:
        subscription_id, customer_id = extract_billing_ids(obj, event.event_type)
        box = resolve_box_for_billing(subscription_id, customer_id, event)
        return box.schema_name if box else ''

    if event.event_type in {'charge.refunded', 'charge.dispute.created', 'charge.dispute.closed'}:
        ref = lookup_payment_ref(obj.get('payment_intent') or '')
        return ref.box_schema if ref else ''
    return ''


__all__ = ['tenant_schema_for_event']
