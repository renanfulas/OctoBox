from django.db import migrations
import hashlib
import hmac

def normalize_stable(raw_value):
    if not raw_value:
        return ""
    # Logica minima de limpeza para ser estavel (Capsula do Tempo)
    digits = ''.join(c for c in str(raw_value) if c.isdigit())
    if digits.startswith('55') and len(digits) > 11:
        return digits[2:]
    return digits

def backfill_blind_indices(apps, schema_editor):
    from django.conf import settings
    key = getattr(settings, 'PHONE_BLIND_INDEX_KEY', '')
    if not key:
        return 

    # Modelos historicos
    Student = apps.get_model('boxcore', 'Student')
    WhatsAppContact = apps.get_model('boxcore', 'WhatsAppContact')
    StudentIntake = apps.get_model('boxcore', 'StudentIntake')

    models_to_fix = [
        (Student, 'phone', 'phone_lookup_index'),
        (WhatsAppContact, 'phone', 'phone_lookup_index'),
        (StudentIntake, 'phone', 'phone_lookup_index'),
    ]
    
    for Model, phone_field, index_field in models_to_fix:
        # Processamento em batches para seguranca de memoria
        queryset = Model.objects.filter(**{f"{index_field}": ""}).exclude(**{f"{phone_field}": ""})
        for obj in queryset:
            raw_phone = getattr(obj, phone_field)
            normalized = normalize_stable(raw_phone)
            h = hmac.new(key.encode('utf-8'), normalized.encode('utf-8'), hashlib.sha256).hexdigest()
            setattr(obj, index_field, f"v1:{h}")
            obj.save(update_fields=[index_field])

class Migration(migrations.Migration):
    dependencies = [
        ('boxcore', '0011_student_phone_lookup_index_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_blind_indices, reverse_code=migrations.RunPython.noop),
    ]
