"""
ARQUIVO: gatilho que liga check-in de aluno de parceiro ao ledger financeiro.

POR QUE ELE EXISTE:
- Attendance (presenca) pertence ao app operations; PartnerCheckInCharge
  (ledger de reconciliacao) pertence ao app finance. operations ja importa de
  finance (finance.models.Payment etc.), entao finance nao pode importar
  operations.models no topo do arquivo sem criar import circular — por isso o
  model Attendance e resolvido via apps.get_model() dentro de ready().

O QUE ESTE ARQUIVO FAZ:
1. Conecta um post_save em Attendance (resolvido em runtime).
2. Delega toda a decisao de negocio para
   finance.partner_checkin_reminders.sync_partner_checkin_charge.

PONTOS CRITICOS:
- register_partner_checkin_signal() deve ser chamado uma unica vez, em
  FinanceConfig.ready().
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


def register_partner_checkin_signal():
    from django.apps import apps

    Attendance = apps.get_model('boxcore', 'Attendance')

    @receiver(post_save, sender=Attendance, weak=False, dispatch_uid='finance_sync_partner_checkin_charge')
    def _handle_attendance_saved(instance, **kwargs):
        from finance.partner_checkin_reminders import sync_partner_checkin_charge

        sync_partner_checkin_charge(instance)


__all__ = ['register_partner_checkin_signal']
