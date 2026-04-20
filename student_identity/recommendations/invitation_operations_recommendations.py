"""
ARQUIVO: recomendacoes operacionais da central de ativacao do aluno.

POR QUE ELE EXISTE:
- separa heuristica de leitura operacional da view HTTP.

O QUE ESTE ARQUIVO FAZ:
1. monta funis por jornada.
2. calcula a prioridade do dia.
3. gera a fila recomendada a partir do gargalo principal.
"""

from __future__ import annotations

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent

from ..funnel_events import build_student_onboarding_event_action
from ..models import StudentOnboardingJourney


class StudentInvitationOperationsRecommendations:
    def __init__(self, *, request, presenter):
        self.request = request
        self.presenter = presenter

    def build_journey_funnels(self, *, box_root_slug: str, active_box_invite_link):
        window_start = timezone.now() - timedelta(days=30)
        base_queryset = AuditEvent.objects.filter(
            created_at__gte=window_start,
            metadata__box_root_slug=box_root_slug,
        )
        journeys = [
            {
                'journey': StudentOnboardingJourney.MASS_BOX_INVITE,
                'title': 'Link em massa',
                'copy': 'Leitura da rede do box: da visita na landing ate a entrada real no app.',
                'steps': [
                    ('landing_viewed', 'Visitas'),
                    ('oauth_completed', 'OAuth concluido'),
                    ('wizard_completed', 'Cadastro concluido'),
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
                'copy': 'Leitura do corredor de precisao: convite, WhatsApp, revisao curta e entrada.',
                'steps': [
                    ('invite_created', 'Convites'),
                    ('whatsapp_handoff_opened', 'WhatsApp aberto'),
                    ('landing_viewed', 'Landing aberta'),
                    ('oauth_completed', 'OAuth concluido'),
                    ('wizard_completed', 'Cadastro concluido'),
                    ('app_entry_completed', 'Entrada no app'),
                ],
                'scope_queryset': base_queryset,
            },
            {
                'journey': StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
                'title': 'Aluno ja cadastrado',
                'copy': 'Leitura do corredor mais curto: convite, autenticacao e entrada direta.',
                'steps': [
                    ('invite_created', 'Convites'),
                    ('landing_viewed', 'Landing aberta'),
                    ('oauth_completed', 'OAuth concluido'),
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
            conversion_rate = round((last_step_value / first_step_value) * 100, 1) if first_step_value else 0
            alerts = []
            if first_step_value >= 5 and conversion_rate < 30:
                alerts.append('Conversao baixa nesta janela. Vale revisar copy, handoff ou friccao da jornada.')
            if len(steps) >= 3 and steps[-2]['value'] > steps[-1]['value']:
                alerts.append('Existe atrito perto da reta final: tem gente chegando quase la e nao entrando no app.')
            biggest_drop = self._find_biggest_funnel_drop(steps=steps)
            next_action = self._build_journey_next_action(
                journey=item['journey'],
                first_step_value=first_step_value,
                conversion_rate=conversion_rate,
                biggest_drop=biggest_drop,
            )
            funnels.append(
                {
                    'journey': item['journey'],
                    'title': item['title'],
                    'copy': item['copy'],
                    'steps': steps,
                    'headline_value': f'{conversion_rate:.1f}%',
                    'headline_label': 'Conversao final da janela',
                    'headline_tone': (
                        'ok'
                        if conversion_rate >= 60
                        else 'attention'
                        if conversion_rate >= 30
                        else 'danger'
                        if first_step_value
                        else 'muted'
                    ),
                    'next_action': next_action,
                    'summary_cards': [
                        {
                            'eyebrow': 'Janela',
                            'value': '30d',
                            'detail': 'Leitura curta para operacao.',
                            'tone': 'muted',
                        },
                        {
                            'eyebrow': 'Primeiro passo',
                            'value': str(first_step_value),
                            'detail': steps[0]['label'] if steps else 'Sem eventos',
                            'tone': 'attention' if first_step_value else 'muted',
                        },
                        {
                            'eyebrow': 'Ultimo passo',
                            'value': str(last_step_value),
                            'detail': steps[-1]['label'] if steps else 'Sem eventos',
                            'tone': 'ok' if last_step_value else 'muted',
                        },
                        {
                            'eyebrow': 'Conversao final',
                            'value': f'{conversion_rate:.1f}%',
                            'detail': 'Do primeiro ao ultimo passo.',
                            'tone': (
                                'ok'
                                if conversion_rate >= 60
                                else 'attention'
                                if conversion_rate >= 30
                                else 'danger'
                                if first_step_value
                                else 'muted'
                            ),
                        },
                    ],
                    'alerts': alerts,
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
                'title': 'Liberar quem ja chegou ao portao',
                'body': f'Existem {len(pending_memberships)} alunos aguardando aprovacao. A melhor energia de hoje e destravar acesso para quem ja fez a parte dele.',
                'tone': 'danger' if len(pending_memberships) >= 5 else 'attention',
                'pill': f'{len(pending_memberships)} aguardando',
            }

        if stalled_invites:
            return {
                'kind': 'stalled_invites',
                'title': 'Trabalhar a fila quente do WhatsApp',
                'body': f'Existem {len(stalled_invites)} convites travados. O maior ganho rapido agora e recuperar quem ja estava quase entrando.',
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
                'title': 'Reanunciar o link em massa',
                'body': 'O link do grupo esta pronto, mas ainda sem tracao real nesta janela. Vale republicar no grupo com uma chamada simples para entrar com Google ou Apple.',
                'tone': 'attention',
                'pill': 'Rede pronta',
            }

        if recent_invites_last_24h == 0:
            return {
                'kind': 'restart_momentum',
                'title': 'Reaquecer o corredor hoje',
                'body': 'Nao houve novos convites nas ultimas 24h. O melhor agora e disparar algumas entradas para manter o onboarding vivo e aprendendo.',
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
            'title': 'Operacao em observacao',
            'body': 'Os corredores estao sem gargalo gritante agora. Vale manter o ritmo e observar a proxima rodada de dados.',
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
                    'title': 'Link em massa pronto para republicar',
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

    def _find_biggest_funnel_drop(self, *, steps: list[dict]):
        biggest_drop = None
        for index in range(len(steps) - 1):
            current_value = steps[index]['value']
            next_value = steps[index + 1]['value']
            drop = current_value - next_value
            if drop <= 0:
                continue
            if biggest_drop is None or drop > biggest_drop['drop']:
                biggest_drop = {
                    'from_label': steps[index]['label'],
                    'to_label': steps[index + 1]['label'],
                    'drop': drop,
                }
        return biggest_drop

    def _build_journey_next_action(self, *, journey: str, first_step_value: int, conversion_rate: float, biggest_drop):
        if first_step_value == 0:
            return {
                'title': 'Acione este corredor',
                'body': self.presenter.build_empty_journey_copy(journey=journey),
                'tone': 'muted',
                'pill': 'Sem movimento',
            }

        if biggest_drop is None:
            if conversion_rate >= 60:
                return {
                    'title': 'Corredor saudavel',
                    'body': 'A jornada esta fechando bem. O melhor agora e manter volume e acompanhar se o ritmo continua.',
                    'tone': 'ok',
                    'pill': 'Fluxo bom',
                }
            return {
                'title': 'Acompanhe a proxima rodada',
                'body': 'O volume ainda e curto. Vale observar mais alguns alunos antes de mexer no fluxo.',
                'tone': 'attention',
                'pill': 'Em leitura',
            }

        from_label = biggest_drop['from_label']
        to_label = biggest_drop['to_label']
        journey_actions = {
            StudentOnboardingJourney.MASS_BOX_INVITE: {
                ('Visitas', 'OAuth concluido'): 'O grupo esta clicando, mas pouca gente esta entrando com Google ou Apple. Vale encurtar a copy e deixar a chamada de autenticacao mais obvia.',
                ('OAuth concluido', 'Cadastro concluido'): 'Tem gente autenticando e travando no wizard. O melhor ajuste e simplificar campos e reforcar que o cadastro leva menos de um minuto.',
                ('Cadastro concluido', 'Entrada no app'): 'Tem aluno terminando o cadastro e nao sentando no app. Revise a mensagem final e a sensacao de "pronto para usar".',
            },
            StudentOnboardingJourney.IMPORTED_LEAD_INVITE: {
                ('Convites', 'WhatsApp aberto'): 'Os convites existem, mas a recepcao ainda nao puxou o handoff do WhatsApp. O proximo passo e trabalhar a fila quente do dia.',
                ('WhatsApp aberto', 'Landing aberta'): 'A mensagem esta saindo, mas o aluno nao esta abrindo o link. Vale testar uma copy mais direta e pessoal no WhatsApp.',
                ('Landing aberta', 'OAuth concluido'): 'O aluno chegou na landing, mas hesitou na autenticacao. Deixe claro que basta tocar em Google ou Apple para entrar.',
                ('OAuth concluido', 'Cadastro concluido'): 'O aluno entrou com OAuth, mas o wizard ainda esta segurando gente demais. Revise os campos obrigatorios e a ordem visual.',
                ('Cadastro concluido', 'Entrada no app'): 'A jornada termina o cadastro, mas ainda nao fecha a entrada real. Revise o redirect final e a mensagem de sucesso.',
            },
            StudentOnboardingJourney.REGISTERED_STUDENT_INVITE: {
                ('Convites', 'Landing aberta'): 'O convite saiu, mas pouca gente abriu. Vale reenviar para quem esta quente e usar um texto mais claro no canal do box.',
                ('Landing aberta', 'OAuth concluido'): 'A landing esta atraindo clique, mas ainda falta confianca para autenticar. Simplifique a explicacao e destaque que o acesso e rapido.',
                ('OAuth concluido', 'Entrada no app'): 'Tem aluno autenticando e nao chegando ao app. Revise o callback final e a mensagem de acesso confirmado.',
            },
        }
        body = journey_actions.get(journey, {}).get(
            (from_label, to_label),
            f'O maior gargalo esta entre {from_label.lower()} e {to_label.lower()}. Vale atacar esse trecho primeiro.',
        )
        return {
            'title': f'Proxima melhor acao: atacar {from_label.lower()} -> {to_label.lower()}',
            'body': body,
            'tone': 'attention' if conversion_rate >= 30 else 'danger',
            'pill': 'Gargalo principal',
        }
