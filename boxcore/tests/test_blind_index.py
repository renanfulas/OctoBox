from django.test import TestCase
from students.models import Student
from communications.models import WhatsAppContact
from onboarding.models import StudentIntake
from shared_support.crypto_fields import generate_blind_index
from integrations.whatsapp.identity import resolve_whatsapp_channel_identity
from django.core.management import call_command
from io import StringIO
import logging

class BlindIndexTests(TestCase):
    def test_blind_index_determinism(self):
        """Telefones equivalentes apos normalizacao devem gerar exatamente o mesmo hash."""
        phone1 = "+55 11 99999-8888"
        phone2 = "11999998888"
        
        index1 = generate_blind_index(phone1)
        index2 = generate_blind_index(phone2)
        
        self.assertEqual(index1, index2)
        self.assertTrue(index1.startswith("v1:"))
        self.assertEqual(len(index1), 3 + 64) # v1: + 64 hex chars

    def test_blind_index_uniqueness(self):
        """Telefones diferentes devem gerar hashes diferentes."""
        phone1 = "11999998888"
        phone2 = "11999997777"
        
        index1 = generate_blind_index(phone1)
        index2 = generate_blind_index(phone2)
        
        self.assertNotEqual(index1, index2)

    def test_student_dual_write(self):
        """O campo phone_lookup_index deve ser populado/limpo automaticamente no save() de Student."""
        student = Student.objects.create(
            full_name="Test Student",
            phone="11999998888"
        )
        self.assertTrue(student.phone_lookup_index.startswith("v1:"))
        
        # Limpeza do telefone deve limpar o indice
        student.phone = ""
        student.save()
        self.assertEqual(student.phone_lookup_index, "")

    def test_whatsapp_contact_dual_write(self):
        """O campo phone_lookup_index deve ser populado automaticamente no save() de WhatsAppContact."""
        contact = WhatsAppContact.objects.create(
            phone="11999998888",
            display_name="Test Contact"
        )
        self.assertTrue(contact.phone_lookup_index.startswith("v1:"))

    def test_student_intake_dual_write(self):
        """O campo phone_lookup_index deve ser populado automaticamente no save() de StudentIntake."""
        intake = StudentIntake.objects.create(
            full_name="Test Intake",
            phone="11999998888"
        )
        self.assertTrue(intake.phone_lookup_index.startswith("v1:"))

    def test_identity_resolution_via_index(self):
        """A resolucao de identidade deve encontrar Student, Contact e Intake usando o indice."""
        phone = "11999993333"
        student = Student.objects.create(full_name="Student Test", phone=phone)
        contact = WhatsAppContact.objects.create(phone=phone, display_name="Contact Test")
        intake = StudentIntake.objects.create(full_name="Intake Test", phone=phone)
        
        identity = resolve_whatsapp_channel_identity(phone=phone)
        
        self.assertEqual(identity.student.id, student.id)
        self.assertEqual(identity.contact.id, contact.id)
        self.assertEqual(identity.intake.id, intake.id)

    def test_backfill_integrity_simulation(self):
        """Simula um cenario de backfill onde registros antigos sem indice passam a ser localizaveis."""
        phone = "11888887777"
        # Criar sem usar save() para simular dado legado (ou bypass de save)
        Student.objects.filter(pk=Student.objects.create(full_name="Legacy", phone=phone).pk).update(phone_lookup_index="")
        
        # Lookup inicial falha (regra de cinto de seguranca localiza via student vinculado se houvesse contact, 
        # mas aqui testamos o indice direto no resolve_student)
        identity_pre = resolve_whatsapp_channel_identity(phone=phone)
        self.assertIsNone(identity_pre.student)
        
        # Executa "backfill" manual
        student = Student.objects.get(full_name="Legacy")
        student.save() # Gatilha o Dual-Write do plano
        
        # Lookup agora funciona
        identity_post = resolve_whatsapp_channel_identity(phone=phone)
        self.assertEqual(identity_post.student.full_name, "Legacy")

    def test_identity_resolution_detects_ambiguity(self):
        """Validar que a resolucao nao associa ninguem se houver ambiguidade no indice."""
        phone = "11977776666"
        
        # Criar registros duplicados (antes da constraint de banco)
        s1 = Student.objects.create(full_name="Student 1", phone=phone)
        s2 = Student.objects.create(full_name="Student 2", phone=phone)
        # Garantir que possuem o mesmo indice
        self.assertEqual(s1.phone_lookup_index, s2.phone_lookup_index)
        
        # Ao tentar resolver, deve logar CRITICAL e retornar None para evitar falso positivo
        with self.assertLogs('integrations.whatsapp.identity', level='CRITICAL') as cm:
            identity = resolve_whatsapp_channel_identity(phone=phone)
            self.assertIsNone(identity.student)
            
        self.assertIn("AMBIGUIDADE: Multiplos Student", cm.output[0])

    def test_audit_command_gatekeeper(self):
        """Validar que o comando de auditoria detecta erros e retorna exit code 1."""
        phone = "11955554444"
        
        # Caso 1: Duplicata
        Student.objects.create(full_name="Dup 1", phone=phone)
        Student.objects.create(full_name="Dup 2", phone=phone)
        
        out = StringIO()
        # call_command com audit_blind_index deve levantar SystemExit(1)
        with self.assertRaises(SystemExit) as cm:
            call_command('audit_blind_index', stdout=out)
        
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Duplicatas encontradas em Student", out.getvalue())

    def test_audit_command_detects_drift(self):
        """Validar que a auditoria detecta quando o indice nao bate com o telefone atual."""
        student = Student.objects.create(full_name="Drifter", phone="11999991111")
        # Forçar um indice errado via update (bypass save)
        Student.objects.filter(id=student.id).update(phone_lookup_index="v1:fakehash")
        
        out = StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command('audit_blind_index', stdout=out)
            
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Drift detectado", out.getvalue())

    def test_student_intake_allows_duplicates(self):
        """Validar que StudentIntake propositalmente nao e unico."""
        phone = "11988889999"
        i1 = StudentIntake.objects.create(full_name="Lead 1", phone=phone)
        i2 = StudentIntake.objects.create(full_name="Lead 2", phone=phone)
        
        self.assertEqual(i1.phone_lookup_index, i2.phone_lookup_index)
        
        # A resolucao de identidade de intake pega o mais recente (comportamento original mantido)
        identity = resolve_whatsapp_channel_identity(phone=phone)
        self.assertEqual(identity.intake.id, i2.id)
