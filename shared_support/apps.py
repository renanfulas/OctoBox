from django.apps import AppConfig

class SharedSupportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shared_support'

    def ready(self):
        from .crypto_keyring import validate_crypto_keyring_configuration

        validate_crypto_keyring_configuration()
