"""
ARQUIVO: sinais de sincronia de estado para Alunos.

POR QUE ELE EXISTE:
- Garante que o Redis (Shadow State) reflita o Banco de Dados em tempo real.
- Aciona a atualização do snapshot quando o aluno, matricula ou pagamento mudar.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
from students.models import Student
from shared_support.redis_snapshots import update_student_snapshot, invalidate_student_snapshot

@receiver(post_save, sender=Student)
def student_ghost_sync_on_save(sender, instance, **kwargs):
    """Sincroniza quando o cadastro principal do aluno mudar."""
    update_student_snapshot(instance.id)

@receiver(post_save, sender='finance.Enrollment')
def enrollment_ghost_sync_on_save(sender, instance, **kwargs):
    """Sincroniza quando o plano ou status comercial mudar."""
    if instance.student_id:
        update_student_snapshot(instance.student_id)

@receiver(post_save, sender='finance.Payment')
def payment_ghost_sync_on_save(sender, instance, **kwargs):
    """Sincroniza quando houver mudancas financeiras (pagamento vs atraso)."""
    if instance.student_id:
        update_student_snapshot(instance.student_id)

@receiver(post_delete, sender=Student)
def student_ghost_cleanup(sender, instance, **kwargs):
    """Limpa o cache se o aluno for deletado (Despawn)."""
    invalidate_student_snapshot(instance.id)
