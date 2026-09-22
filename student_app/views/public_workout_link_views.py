"""
ARQUIVO: ponte do aluno de box pro corredor de treinos (Onda B3 do CORDA,
resto do item 5 — docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- ao contrario de public_workout_views.py (roda SEM tenant, schema
  public puro), esta view roda DENTRO do tenant do box, autenticada como
  StudentIdentity (StudentIdentityRequiredMixin) — precisa resolver a
  PublicWorkoutAccount (schema public, SHARED_APP) da mesma pessoa.

PONTOS CRITICOS:
- Resolucao por e-mail, get_or_create simples: "nao havera duplicatas"
  (unique=True em PublicWorkoutAccount.email e' a garantia real, nao uma
  reconciliacao elaborada). Se ja existe conta com este e-mail, o
  `student_identity_id` dela NUNCA e' sobrescrito aqui (mesma regra do
  resto do produto: resolvido so na criacao, D.5 da Onda A1 Fatia B).
- Concede sessao do corredor (cookie octobox_treinos_session) direto,
  sem o roundtrip de magic-link do login (`student_identity/
  public_workout_login.py`): a autenticacao do box (StudentIdentityRequiredMixin
  ja fez o middleware validar o cookie assinado do aluno) e' prova de
  identidade suficiente para a MESMA pessoa - nao esta pulando auth, esta
  reconhecendo uma que ja aconteceu.
- Sem assinatura ativa: nao ha pra onde redirecionar ainda (o fluxo de
  assinatura do corredor, POST /treinos/subscribe, e' uma chamada de API
  que ja exige `plan_slug` conhecido, nao uma tela de "escolha seu
  plano") — devolve uma pagina minima informativa em vez de inventar
  destino que nao existe. Mesma logica se aplica a uma assinatura que
  existe mas ainda nao tem `plan_slug` (cadastro a frio, Entrega 5/Fase 2,
  D.2): sem isso o redirect virava literalmente `/renan/None`.
"""

from __future__ import annotations

from django.http import HttpResponseRedirect
from django.views.generic import View

from .base import StudentIdentityRequiredMixin


class StudentPublicWorkoutLinkView(StudentIdentityRequiredMixin, View):
    """GET /aluno/consultoria/ — leva o aluno de box logado pro treino do
    corredor de consultoria, se ele tiver assinatura ativa."""

    def get(self, request, *args, **kwargs):
        from public_workouts.models import PublicWorkoutAccount

        identity = request.student_identity
        account, _created = PublicWorkoutAccount.objects.get_or_create(
            email=identity.email,
            defaults={'student_identity_id': identity.id},
        )

        from student_identity.public_workout_session import attach_public_workout_session_cookie
        from public_workouts.models import PublicWorkoutSubscriptionStatus

        subscription = getattr(account, 'subscription', None)
        if (
            subscription is not None
            and subscription.status == PublicWorkoutSubscriptionStatus.ACTIVE
            and subscription.plan_slug
        ):
            destination = f'/renan/{subscription.plan_slug}'
        else:
            destination = '/treinos/minha-conta'
        response = HttpResponseRedirect(destination)
        return attach_public_workout_session_cookie(response, account_id=account.pk)
