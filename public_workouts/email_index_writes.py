"""Shared exact-email blind-index write behavior for commerce models."""

from django.conf import settings
from django.db import models

from shared_support.crypto_fields import (
    generate_public_workout_account_email_blind_index,
    generate_public_workout_checkout_lead_email_blind_index,
    generate_public_workout_waitlist_email_blind_index,
)


class _EmailLookupIndexWriteMixin(models.Model):
    email_lookup_index = models.CharField(max_length=67, blank=True, default='', db_index=True)
    email_ready_setting = ''
    email_index_generator = None

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._persisted_email_for_lookup = self.email

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        email_persisted = update_fields is None or 'email' in update_fields
        email = self.email
        should_index = email_persisted and (
            self._state.adding or email != self._persisted_email_for_lookup
            or getattr(settings, 'EMAIL_BLIND_INDEX_KEY', '')
            or getattr(settings, self.email_ready_setting, False)
        )
        if should_index:
            self.email_lookup_index = self.email_index_generator(email)
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'email_lookup_index'}
        result = super().save(*args, **kwargs)
        if email_persisted:
            self._persisted_email_for_lookup = email
        return result


class PublicWorkoutAccountEmailIndexWriteMixin(_EmailLookupIndexWriteMixin):
    email_ready_setting = 'PUBLIC_WORKOUT_ACCOUNT_EMAIL_LOOKUP_INDEX_READY'
    email_index_generator = staticmethod(generate_public_workout_account_email_blind_index)

    class Meta:
        abstract = True


class PublicWorkoutCheckoutLeadEmailIndexWriteMixin(_EmailLookupIndexWriteMixin):
    email_ready_setting = 'PUBLIC_WORKOUT_CHECKOUT_LEAD_EMAIL_LOOKUP_INDEX_READY'
    email_index_generator = staticmethod(generate_public_workout_checkout_lead_email_blind_index)

    class Meta:
        abstract = True


class PublicWorkoutWaitlistEmailIndexWriteMixin(_EmailLookupIndexWriteMixin):
    email_ready_setting = 'PUBLIC_WORKOUT_WAITLIST_EMAIL_LOOKUP_INDEX_READY'
    email_index_generator = staticmethod(generate_public_workout_waitlist_email_blind_index)

    class Meta:
        abstract = True
