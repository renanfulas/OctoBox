"""
ARQUIVO: configuracao do app control (control plane da plataforma).

POR QUE ELE EXISTE:
- Registra o app control/ como parte de SHARED_APPS (schema public).
- Contém Box, Domain, Membership, BoxProvisioningEvent, PlatformAuditEvent.
"""

from django.apps import AppConfig


class ControlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'control'
    verbose_name = 'Control Plane'
