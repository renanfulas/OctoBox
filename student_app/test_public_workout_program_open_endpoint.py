"""POST /renan/<slug>/abertura — abertura do app que o servidor não vê sozinho
(cópia offline e volta ao app em segundo plano), com o horário do aparelho."""

import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutProgramOpen,
    PublicWorkoutSubscription,
)
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)

IPHONE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148'


def _ms(value):
    return int(value.timestamp() * 1000)


class PublicWorkoutProgramOpenEndpointTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aberturas@example.com')
        PublicWorkoutSubscription.objects.create(account=self.account, plan_slug='bruno')
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=self.account.pk, identity_verified=True
        )

    def _post(self, payload, slug='bruno'):
        return self.client.post(
            reverse('public-workout-program-open', kwargs={'plan_slug': slug}),
            data=json.dumps(payload), content_type='application/json', HTTP_USER_AGENT=IPHONE_UA,
        )

    def test_offline_open_is_recorded_at_the_device_time(self):
        opened = timezone.now() - timedelta(hours=3)

        response = self._post({'opened_at': _ms(opened)})

        self.assertEqual(response.json(), {'ok': True, 'recorded': True})
        row = PublicWorkoutProgramOpen.objects.get(account=self.account)
        self.assertEqual(row.plan_slug, 'bruno')
        self.assertEqual(row.device, 'mobile')
        self.assertLess(abs((row.opened_at - opened).total_seconds()), 1)

    def test_resend_and_duplicates_inside_the_window_count_once(self):
        opened = timezone.now() - timedelta(hours=3)
        self._post({'opened_at': _ms(opened)})
        again = self._post({'opened_at': _ms(opened)})
        self.assertEqual(again.json()['recorded'], False)
        self.assertEqual(PublicWorkoutProgramOpen.objects.filter(account=self.account).count(), 1)

    def test_offline_open_older_than_a_recorded_one_is_still_counted(self):
        # Abertura online às 20h gravada antes; a offline das 19h chega depois.
        at_eight = timezone.now() - timedelta(hours=1)
        at_seven = at_eight - timedelta(hours=1)
        self._post({'opened_at': _ms(at_eight)})
        response = self._post({'opened_at': _ms(at_seven)})
        self.assertEqual(response.json()['recorded'], True)
        # E uma 10 min antes da gravada é a mesma abertura (janela dos dois lados).
        dup = self._post({'opened_at': _ms(at_eight - timedelta(minutes=10))})
        self.assertEqual(dup.json()['recorded'], False)
        self.assertEqual(PublicWorkoutProgramOpen.objects.filter(account=self.account).count(), 2)

    def test_slightly_ahead_device_clock_is_clamped_to_now(self):
        response = self._post({'opened_at': _ms(timezone.now() + timedelta(minutes=2))})
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(PublicWorkoutProgramOpen.objects.get().opened_at, timezone.now())

    def test_invalid_future_and_too_old_times_are_rejected(self):
        for value in (None, 'ontem', True, _ms(timezone.now() + timedelta(hours=1)),
                      _ms(timezone.now() - timedelta(days=31))):
            self.assertEqual(self._post({'opened_at': value}).status_code, 400, value)
        self.assertFalse(PublicWorkoutProgramOpen.objects.exists())

    def test_requires_login_and_ownership(self):
        self.assertEqual(self._post({'opened_at': _ms(timezone.now())}, slug='juliana').status_code, 404)
        self.client.cookies.clear()
        self.assertEqual(self._post({'opened_at': _ms(timezone.now())}).status_code, 401)
        self.assertFalse(PublicWorkoutProgramOpen.objects.exists())
