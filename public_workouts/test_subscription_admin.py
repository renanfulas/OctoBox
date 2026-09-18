"""
ARQUIVO: testes do admin de PublicWorkoutSubscription (Entrega 5, Fase 2 —
docs/plans/public-workouts-escala-e-nutricao-corda.md, D.2/RT2).

POR QUE ELE EXISTE:
- RT2 exige que a fila de ativação (quem pagou mas ainda não tem
  plan_slug) apareça em algum lugar que se olhe todo dia, não que só
  exista no banco — o filtro customizado é o "lugar", vale testar a
  query dele isoladamente da tela funcionar.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription, PublicWorkoutSubscriptionStatus, PublicWorkoutTier


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

    def test_awaiting_activation_filter_shows_only_paid_without_slug(self):
        waiting = _make_subscription(email='esperando@example.com', status=PublicWorkoutSubscriptionStatus.ACTIVE, plan_slug=None)
        _make_subscription(email='comslug@example.com', status=PublicWorkoutSubscriptionStatus.ACTIVE, plan_slug='bruno')
        _make_subscription(email='pendente@example.com', status=PublicWorkoutSubscriptionStatus.PENDING_PAYMENT, plan_slug=None)

        response = self.client.get(
            reverse('admin:public_workouts_publicworkoutsubscription_changelist'), {'aguardando_ativacao': 'sim'}
        )

        self.assertContains(response, 'esperando@example.com')
        self.assertNotContains(response, 'comslug@example.com')
        self.assertNotContains(response, 'pendente@example.com')
        self.assertEqual(response.context['cl'].queryset.count(), 1)
        self.assertEqual(response.context['cl'].queryset.first().pk, waiting.pk)

    def test_without_filter_shows_every_status(self):
        _make_subscription(email='a@example.com', status=PublicWorkoutSubscriptionStatus.ACTIVE, plan_slug='bruno')
        _make_subscription(email='b@example.com', status=PublicWorkoutSubscriptionStatus.PENDING_PAYMENT, plan_slug=None)

        response = self.client.get(reverse('admin:public_workouts_publicworkoutsubscription_changelist'))

        self.assertContains(response, 'a@example.com')
        self.assertContains(response, 'b@example.com')
