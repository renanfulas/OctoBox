"""
ARQUIVO: testes do admin de PublicWorkoutSubscription (Entrega 5, Fase 2 —
docs/plans/public-workouts-escala-e-nutricao-corda.md, D.2/RT2).

POR QUE ELE EXISTE:
- RT2 exige que a fila de ativação (quem pagou mas ainda não tem
  plan_slug) apareça em algum lugar que se olhe todo dia, não que só
  exista no banco — o filtro customizado é o "lugar", vale testar a
  query dele isoladamente da tela funcionar.
- Ampliado junto com a anamnese+IA (ver AwaitingActivationFilter em
  admin.py): plan_slug preenchido deixou de significar "já tem programa
  publicado" — Renan agora tipicamente preenche plan_slug ANTES de gerar
  o rascunho de IA. Uma assinatura com plan_slug mas sem
  PublicWorkoutProgram ativo continua "aguardando ativação" de verdade.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription, PublicWorkoutSubscriptionStatus, PublicWorkoutTier
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program


def _make_subscription(*, email, status, plan_slug=None, tier=PublicWorkoutTier.ESSENCIAL):
    account = PublicWorkoutAccount.objects.create(email=email)
    return PublicWorkoutSubscription.objects.create(account=account, status=status, plan_slug=plan_slug, tier=tier)


class PublicWorkoutSubscriptionAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='senha-forte-123',
        )
        self.client.force_login(self.superuser)

    def test_changelist_loads_and_lists_subscriptions(self):
        _make_subscription(email='aluno@example.com', status=PublicWorkoutSubscriptionStatus.ACTIVE, plan_slug='bruno')

        response = self.client.get(reverse('admin:public_workouts_publicworkoutsubscription_changelist'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aluno@example.com')

    def test_awaiting_activation_filter_shows_paid_without_active_program(self):
        waiting_without_slug = _make_subscription(
            email='esperando@example.com', status=PublicWorkoutSubscriptionStatus.ACTIVE, plan_slug=None
        )
        # plan_slug ja' preenchido (Renan atribuiu antes de gerar o
        # rascunho de IA) mas AINDA sem PublicWorkoutProgram ativo — isto
        # continua "aguardando ativacao" de verdade, nao deveria sumir da
        # fila so' por ter ganho um slug.
        waiting_with_slug_no_program = _make_subscription(
            email='comslugsemtreino@example.com', status=PublicWorkoutSubscriptionStatus.ACTIVE, plan_slug='bruno'
        )
        with_active_program = _make_subscription(
            email='comtreinoativo@example.com', status=PublicWorkoutSubscriptionStatus.ACTIVE, plan_slug='giovanna'
        )
        publish_program(slug='giovanna', payload=build_example_payload())
        _make_subscription(email='pendente@example.com', status=PublicWorkoutSubscriptionStatus.PENDING_PAYMENT, plan_slug=None)

        response = self.client.get(
            reverse('admin:public_workouts_publicworkoutsubscription_changelist'), {'aguardando_ativacao': 'sim'}
        )

        self.assertContains(response, 'esperando@example.com')
        self.assertContains(response, 'comslugsemtreino@example.com')
        self.assertNotContains(response, 'comtreinoativo@example.com')
        self.assertNotContains(response, 'pendente@example.com')
        queryset_pks = set(response.context['cl'].queryset.values_list('pk', flat=True))
        self.assertEqual(queryset_pks, {waiting_without_slug.pk, waiting_with_slug_no_program.pk})
        self.assertNotIn(with_active_program.pk, queryset_pks)

    def test_without_filter_shows_every_status(self):
        _make_subscription(email='a@example.com', status=PublicWorkoutSubscriptionStatus.ACTIVE, plan_slug='bruno')
        _make_subscription(email='b@example.com', status=PublicWorkoutSubscriptionStatus.PENDING_PAYMENT, plan_slug=None)

        response = self.client.get(reverse('admin:public_workouts_publicworkoutsubscription_changelist'))

        self.assertContains(response, 'a@example.com')
        self.assertContains(response, 'b@example.com')
