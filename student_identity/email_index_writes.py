"""Keep model email indexes aligned on ORM writes, including partial saves."""

from django.conf import settings
from django.db import models

from shared_support.crypto_fields import (
    EncryptedCharField,
    EncryptedEmailField,
    generate_email_blind_index,
    generate_student_app_invitation_email_blind_index,
)


def encrypted_invitation_email_field():
    return EncryptedEmailField(
        blank=True,
        storage_max_length=2048,
        writer_enabled_setting='STUDENT_APP_INVITATION_EMAIL_ENCRYPTION_WRITE_READY',
    )


class _EmailLookupIndexWriteMixin(models.Model):
    email_lookup_index = models.CharField(max_length=67, blank=True, default='', db_index=True)
    email_value_field = 'email'
    email_ready_setting = ''
    email_index_generator = None

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._persisted_email_for_lookup = getattr(self, self.email_value_field)

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        email_persisted = update_fields is None or self.email_value_field in update_fields
        email = getattr(self, self.email_value_field)
        changed = self._state.adding or email != self._persisted_email_for_lookup
        should_index = email_persisted and (
            changed
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


class StudentIdentityEmailIndexWriteMixin(_EmailLookupIndexWriteMixin):
    email_ready_setting = 'STUDENT_IDENTITY_EMAIL_LOOKUP_INDEX_READY'
    email_index_generator = staticmethod(generate_email_blind_index)

    class Meta:
        abstract = True


class StudentAppInvitationEmailIndexWriteMixin(_EmailLookupIndexWriteMixin):
    email_value_field = 'invited_email'
    email_ready_setting = 'STUDENT_APP_INVITATION_EMAIL_LOOKUP_INDEX_READY'
    email_index_generator = staticmethod(generate_student_app_invitation_email_blind_index)

    class Meta:
        abstract = True
