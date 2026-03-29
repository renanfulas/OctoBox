import sys
from django.core.management.base import BaseCommand
from django.db.models import Count
from students.models import Student
from communications.models import WhatsAppContact
from shared_support.crypto_fields import generate_blind_index

class Command(BaseCommand):
    help = 'Audita a integridade dos Blind Indices de telefone no sistema.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("--- Auditoria de Integridade OctoBOX (Blind Index) ---"))
        
        has_issues = False
        
        models_to_audit = [
            (Student, "Student"),
            (WhatsAppContact, "WhatsAppContact"),
        ]

        for model, label in models_to_audit:
            self.stdout.write(f"\nVerificando {label}...")
            
            # 1. Detectar Duplicatas
            duplicates = (
                model.objects.exclude(phone_lookup_index='')
                .values('phone_lookup_index')
                .annotate(count=Count('id'))
                .filter(count__gt=1)
            )
            
            if duplicates.exists():
                has_issues = True
                self.stdout.write(self.style.ERROR(f"  [!] Duplicatas encontradas em {label}:"))
                for entry in duplicates:
                    idx = entry['phone_lookup_index']
                    count = entry['count']
                    ids = list(model.objects.filter(phone_lookup_index=idx).values_list('id', flat=True))
                    self.stdout.write(f"      - Índice: {idx} | Ocorrências: {count} | IDs: {ids}")

            # 2. Detectar Drift e Indices Vazios Indevidos
            # Processamos em batches se a base for grande, mas para auditoria simples vamos iterar.
            drift_count = 0
            missing_index_count = 0
            
            results = model.objects.exclude(phone='')
            for obj in results:
                calculated = generate_blind_index(obj.phone)
                
                if not obj.phone_lookup_index:
                    missing_index_count += 1
                    has_issues = True
                    if missing_index_count <= 5: # Limitar output detalhado
                        self.stdout.write(self.style.WARNING(f"      [-] ID {obj.id}: Telefone preenchido mas índice vazio."))
                
                elif obj.phone_lookup_index != calculated:
                    drift_count += 1
                    has_issues = True
                    if drift_count <= 5:
                        self.stdout.write(self.style.ERROR(f"      [X] ID {obj.id}: Drift detectado! Gravado={obj.phone_lookup_index}, Calculado={calculated}"))

            if missing_index_count > 5:
                self.stdout.write(self.style.WARNING(f"      ... e mais {missing_index_count - 5} casos de índice vazio."))
            elif missing_index_count > 0:
                self.stdout.write(self.style.WARNING(f"      Total de índices vazios indevidos: {missing_index_count}"))

            if drift_count > 5:
                self.stdout.write(self.style.ERROR(f"      ... e mais {drift_count - 5} casos de drift."))
            elif drift_count > 0:
                self.stdout.write(self.style.ERROR(f"      Total de drift detectado: {drift_count}"))

        if has_issues:
            self.stdout.write(self.style.ERROR("\n🔴 STATUS: FALHA. Base de dados inconsistente para unicidade."))
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS("\n🟢 STATUS: SUCESSO. Base de dados pronta para unicidade."))
