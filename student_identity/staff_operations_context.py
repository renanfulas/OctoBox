"""
ARQUIVO: contexto da central operacional de ativacao do aluno.

POR QUE ELE EXISTE:
- tira de `student_identity/staff_views.py` a orquestracao pesada de leitura, recommendation e payload.
"""

from shared_support.page_payloads import attach_page_payload

from .forms import StudentInvitationCreateForm
from .presentation import build_student_invitation_operations_page
from .presenters import StudentInvitationOperationsPresenter
from .queries.invitation_operations_queries import StudentInvitationOperationsQueries
from .recommendations.invitation_operations_recommendations import StudentInvitationOperationsRecommendations


def build_student_invitation_operations_context(view, *, context, **kwargs):
    form = kwargs.get('form') or StudentInvitationCreateForm()
    access_matrix = view._build_access_matrix(view.request)
    presenter = StudentInvitationOperationsPresenter(
        request=view.request,
        access_matrix=access_matrix,
    )
    operations_queries = StudentInvitationOperationsQueries(
        presenter=presenter,
        request=view.request,
        access_matrix=access_matrix,
    )
    recommendations = StudentInvitationOperationsRecommendations(
        request=view.request,
        presenter=presenter,
    )
    box_root_slug = operations_queries.get_box_root_slug()
    active_box_invite_link = operations_queries.get_active_box_invite_link()
    pending_memberships = operations_queries.build_pending_memberships()
    managed_memberships = operations_queries.build_managed_memberships()
    recent_invites, stalled_invites = operations_queries.build_recent_invites_snapshot()
    observability_snapshot = operations_queries.build_observability_snapshot(
        pending_memberships=pending_memberships,
        stalled_invites=stalled_invites,
    )
    journey_funnels = recommendations.build_journey_funnels(
        box_root_slug=box_root_slug,
        active_box_invite_link=active_box_invite_link,
    )
    priority_of_day = recommendations.build_priority_of_day(
        stalled_invites=stalled_invites,
        pending_memberships=pending_memberships,
        journey_funnels=journey_funnels,
        active_box_invite_link=active_box_invite_link,
        recent_invites_last_24h=observability_snapshot['recent_invites_last_24h'],
    )
    recommended_queue = recommendations.build_recommended_queue(
        priority_of_day=priority_of_day,
        stalled_invites=stalled_invites,
        pending_memberships=pending_memberships,
        active_box_invite_link=active_box_invite_link,
    )

    page_payload = build_student_invitation_operations_page(
        current_box_slug=box_root_slug,
        access_matrix=access_matrix,
        recent_invites=recent_invites,
        stalled_invites=stalled_invites,
        pending_memberships=pending_memberships,
        managed_memberships=managed_memberships,
        observability_cards=observability_snapshot['observability_cards'],
        observability_alerts=observability_snapshot['observability_alerts'],
        journey_funnels=journey_funnels,
        priority_of_day=priority_of_day,
        recommended_queue=recommended_queue,
        active_box_invite_link=presenter.build_active_box_invite_link_payload(
            active_box_invite_link=active_box_invite_link,
        ),
    )
    attach_page_payload(
        context,
        payload_key='student_invitation_operations_page',
        payload=page_payload,
    )
    context['form'] = form
    return context
