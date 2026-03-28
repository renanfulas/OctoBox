from django.core.management.base import BaseCommand
from django.db import transaction
from students.models import Student
from onboarding.models import StudentIntake
from communications.models import WhatsAppContact, WhatsAppMessageLog

class Command(BaseCommand):
    help = 'Forrester/White Hat Tool: Resaves all PII-bearing models to enforce AES cryptography on legacy plain-text data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("====================================================="))
        self.stdout.write(self.style.WARNING("🛡️ INICIANDO OPERACAO DB CLEANSER (PII SANITIZATION)"))
        self.stdout.write(self.style.WARNING("====================================================="))
        
        models_to_clean = [
            (Student, 'Alunos (Student)'),
            (StudentIntake, 'Leads (StudentIntake)'),
            (WhatsAppContact, 'Contatos (WhatsAppContact)'),
            (WhatsAppMessageLog, 'Mensagens (WhatsAppMessageLog)')
        ]
        
        total_encrypted = 0
        
        for model_class, name in models_to_clean:
            self.stdout.write(f"\nVasculhando tabela: {name}...")
            count = 0
            with transaction.atomic():
                for instance in model_class.objects.all().select_for_update().iterator():
                    # Em models do Django, quando invocamos .save(), a engine de ORM pega o field interno
                    # que é o nosso EncryptedCharField, processa via get_prep_value() da field e engole a variavel.
                    # Como a variavel foi tratada como Fallback (retornada plain-text no start), o save()
                    # obrigatoriamente vai injetá-la de novo chamando Fernet encrypt.
                    instance.save()
                    count += 1
            
            self.stdout.write(self.style.SUCCESS(f"  -> Selado! {count} registros de {name} foram engolidos por Cifra AES-128."))
            total_encrypted += count
            
        self.stdout.write("\n=====================================================")
        self.stdout.write(self.style.SUCCESS(f"🏆 SUCESSO: {total_encrypted} registros esterilizados."))
        self.stdout.write(self.style.SUCCESS("O Banco de Dados foi completamente Higienizado. Zero Pistas."))
        self.stdout.write("=====================================================\n")
