"""
ARQUIVO: recomendacoes operacionais da central de ativacao do aluno.

POR QUE ELE EXISTE:
- separa heuristica de leitura operacional da view HTTP.

O QUE ESTE ARQUIVO FAZ:
1. monta funis por jornada.
2. calcula a prioridade do dia.
3. gera a fila operacional e resume fatos de coorte sem inferir saúde por contagem de eventos.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent

from ..funnel_events import build_student_onboarding_event_action
from ..box_scope import get_student_identity_box_scope
from ..models import StudentOnboardingJourney
from ..queries.activation_cohorts import build_activation_cohort_reports


class StudentInvitationOperationsRecommendations:
    def __init__(self, *, request):
        self.request = request

    def build_journey_funnels(self, *, box_root_slug: str, active_box_invite_link):
        scope = get_student_identity_box_scope(self.request)
        schema_name = getattr(connection, 'schema_name', '')
        if (
            scope.box is None or schema_name != scope.box.schema_name
            or box_root_slug not in {scope.box.schema_name, scope.box.slug}
        ):
            raise PermissionDenied('A leitura do funil exige o schema do box ativo.')
        window_start = timezone.now() - timedelta(days=30)
        activation_cohorts = {
            report['journey']: report for report in build_activation_cohort_reports()
        }
        # AuditEvent já é tenant-local. A referência HMAC dos logs não é uma
        # chave analítica: muda ao rotacionar SECRET_KEY, e o formato antigo
        # usava box_root_slug. Ambos continuam legíveis no schema autorizado.
        base_queryset = AuditEvent.objects.filter(created_at__gte=window_start)
        journeys = [
            {
                'journey': StudentOnboardingJourney.MASS_BOX_INVITE,
                'title': 'Link do grupo',
                'copy': 'Leitura da rede do box: da visita na landing até a entrada real no app.',
                'steps': [
                    ('landing_viewed', 'Visitas'),
                    ('oauth_completed', 'OAuth concluído'),
                    ('wizard_completed', 'Cadastro concluído'),
                    ('app_entry_completed', 'Entrada no app'),
                ],
                'scope_queryset': (
                    base_queryset.filter(metadata__box_invite_link_id=active_box_invite_link.id)
                    if active_box_invite_link is not None else base_queryset
                ),
            },
            {
                'journey': StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
                'title': 'Lead importado',
                'copy': 'Leitura do convite com mais controle: convite, WhatsApp, revisão curta e entrada.',
                'steps': [
                    ('invite_created', 'Convites'),
                    ('whatsapp_handoff_opened', 'WhatsApp aberto'),
                    ('landing_viewed', 'Landing aberta'),
                    ('oauth_completed', 'OAuth concluído'),
                    ('wizard_completed', 'Cadastro concluído'),
                    ('app_entry_completed', 'Entrada no app'),
                ],
                'scope_queryset': base_queryset,
            },
            {
                'journey': StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
                'title': 'Aluno já cadastrado',
                'copy': 'Leitura do convite mais direto: convite, autenticação e entrada direta.',
                'steps': [
                    ('invite_created', 'Convites'),
                    ('landing_viewed', 'Landing aberta'),
                    ('oauth_completed', 'OAuth concluído'),
                    ('app_entry_completed', 'Entrada no app'),
                ],
                'scope_queryset': base_queryset,
            },
        ]
        funnels = []
        for item in journeys:
            journey_queryset = item['scope_queryset'].filter(metadata__journey=item['journey'])
            steps = []
            for event_key, label in item['steps']:
                steps.append(
                    {
                        'key': event_key,
                        'label': label,
                        'value': journey_queryset.filter(
                            action=build_student_onboarding_event_action(journey=item['journey'], event=event_key),
                        ).count(),
                    }
                )
            first_step_value = steps[0]['value'] if steps else 0
            last_step_value = steps[-1]['value'] if steps else 0
            next_action = self._build_journey_next_action(
                cohort=activation_cohorts.get(item['journey']),
            )
            funnels.append(
                {
                    'journey': item['journey'],
                    'cohort': activation_cohorts.get(item['journey']),
                    'title': item['title'],
                    'copy': item['copy'],
                    'steps': steps,
                    'headline_value': f'{last_step_value} / {first_step_value}',
                    'headline_label': 'Contagens independentes de eventos finais / iniciais (30d).',
                    'headline_tone': 'muted',
                    'next_action': next_action,
                    'summary_cards': [
                        {
                            'eyebrow': 'Janela',
                            'value': '30d',
                            'detail': 'Leitura curta para operação.',
                            'tone': 'muted',
                        },
                        {
                            'eyebrow': 'Primeiro passo',
                            'value': str(first_step_value),
                            'detail': steps[0]['label'] if steps else 'Sem eventos',
                            'tone': 'muted',
                        },
                        {
                            'eyebrow': 'Último passo',
                            'value': str(last_step_value),
                            'detail': steps[-1]['label'] if steps else 'Sem eventos',
                            'tone': 'muted',
                        },
                        {
                            'eyebrow': 'Eventos finais / iniciais',
                            'value': f'{last_step_value} / {first_step_value}',
                            'detail': 'Contagens independentes de eventos na janela; sem leitura de conversão.',
                            'tone': 'muted',
                        },
                    ],
                    'alerts': [],
                }
            )
        return funnels

    def build_priority_of_day(
        self,
        *,
        stalled_invites: list[dict],
        pending_memberships: list[dict],
        journey_funnels: list[dict],
        active_box_invite_link,
        recent_invites_last_24h: int,
    ):
        if len(pending_memberships) >= 3:
            return {
                'kind': 'pending_memberships',
                'title': 'Liberar quem já chegou ao portão',
                'body': f'Existem {len(pending_memberships)} alunos aguardando aprovação. A melhor energia de hoje é destravar acesso para quem já fez a parte dele.',
                'tone': 'danger' if len(pending_memberships) >= 5 else 'attention',
                'pill': f'{len(pending_memberships)} aguardando',
            }

        if stalled_invites:
            return {
                'kind': 'stalled_invites',
                'title': 'Trabalhar a fila de mensagens do WhatsApp',
                'body': f'Existem {len(stalled_invites)} convites travados. O maior ganho rápido agora é recuperar quem já estava quase entrando.',
                'tone': 'danger' if len(stalled_invites) >= 3 else 'attention',
                'pill': f'{min(len(stalled_invites), 5)} para atacar agora',
            }

        mass_funnel = next(
            (item for item in journey_funnels if item['journey'] == StudentOnboardingJourney.MASS_BOX_INVITE),
            None,
        )
        mass_has_visits = bool(mass_funnel and mass_funnel['steps'] and mass_funnel['steps'][0]['value'])
        if active_box_invite_link is not None and active_box_invite_link.can_accept and not mass_has_visits:
            return {
                'kind': 'mass_link_reannounce',
                'title': 'Reanunciar o link do grupo',
                'body': 'O link do grupo está pronto, mas ainda sem tração real nesta janela. Vale republicar no grupo com uma chamada simples para entrar com Google ou Apple.',
                'tone': 'attention',
                'pill': 'Rede pronta',
            }

        if recent_invites_last_24h == 0:
            return {
                'kind': 'restart_momentum',
                'title': 'Reativar este tipo de convite hoje',
                'body': 'Não houve novos convites nas últimas 24h. O melhor agora é disparar algumas entradas para manter o onboarding vivo e aprendendo.',
                'tone': 'muted',
                'pill': 'Sem pulso recente',
            }

        if mass_funnel is not None:
            return {
                'kind': 'journey_focus',
                'title': mass_funnel['next_action']['title'],
                'body': mass_funnel['next_action']['body'],
                'tone': mass_funnel['next_action']['tone'],
                'pill': mass_funnel['next_action']['pill'],
            }

        return {
            'kind': 'monitoring',
            'title': 'Operação em observação',
            'body': 'Os convites estão sem gargalo grave agora. Vale manter o ritmo e observar a próxima rodada de dados.',
            'tone': 'ok',
            'pill': 'Estavel',
        }

    def build_recommended_queue(
        self,
        *,
        priority_of_day: dict | None,
        stalled_invites: list[dict],
        pending_memberships: list[dict],
        active_box_invite_link,
    ) -> list[dict]:
        if priority_of_day is None:
            return []

        if priority_of_day['kind'] == 'pending_memberships':
            return [
                {
                    'title': item['student_name'],
                    'detail': f"Pedido de acesso em {item['created_at']:%d/%m %H:%M} para o box {item['box_root_slug']}.",
                    'tone': 'attention',
                    'pill': 'Aprovar acesso',
                    'action_kind': 'approve-membership',
                    'action_label': 'Aprovar agora',
                    'membership_id': item['id'],
                }
                for item in pending_memberships[:5]
            ]

        if priority_of_day['kind'] == 'stalled_invites':
            return [
                {
                    'title': item['student_name'],
                    'detail': f"{item['reason_label']} {item['stalled_since_label']}",
                    'tone': item['priority_tone'],
                    'pill': item['priority_label'],
                    'action_kind': 'open-whatsapp',
                    'action_label': item['whatsapp_action_label'],
                    'invitation_id': item['invitation_id'],
                }
                for item in stalled_invites[:5]
            ]

        if priority_of_day['kind'] == 'mass_link_reannounce' and active_box_invite_link is not None:
            return [
                {
                    'title': 'Link do grupo pronto para republicar',
                    'detail': 'Use este link no grupo oficial do box e chame o aluno para entrar com Google ou Apple.',
                    'tone': 'attention',
                    'pill': f"{active_box_invite_link.use_count}/{active_box_invite_link.max_uses} usos",
                    'action_kind': 'copy-mass-link',
                    'action_label': 'Copiar link',
                    'copy_value': self.request.build_absolute_uri(
                        reverse('student-identity-box-invite', kwargs={'token': active_box_invite_link.token})
                    ),
                }
            ]

        return []

    def _build_journey_next_action(self, *, cohort: dict | None):
        if not cohort or cohort['maturity'] != 'ready' or cohort['eligible_count'] == 0:
            immature_count = cohort['immature_count'] if cohort else 0
            body = (
                f'{immature_count} coortes ainda aguardam maturação; não há denominador elegível para comparar.'
                if immature_count
                else 'Ainda não há coortes maduras suficientes para uma leitura de ativação e retorno.'
            )
            return {
                'title': 'Aguardando coortes maduras',
                'body': body,
                'tone': 'muted',
                'pill': 'Sem base madura',
            }

        eligible = cohort['eligible_count']
        activated = cohort['activated_count']
        retained = cohort['retained_count']
        if activated < eligible:
            detail = (
                f"Ativação {cohort['activation_window_label']}: "
                f'{activated} de {eligible} coortes maduras tiveram entrada autenticada no app.'
            )
            pill = f'{activated}/{eligible} ativadas'
        else:
            detail = (
                f"Retorno {cohort['retention_window_label']}: "
                f'{retained} de {activated} coortes ativadas tiveram atividade autenticada.'
            )
            pill = f'{retained}/{activated} retornaram'
        return {
            'title': 'Leitura da coorte madura',
            'body': detail,
            'tone': 'muted',
            'pill': pill,
        }
