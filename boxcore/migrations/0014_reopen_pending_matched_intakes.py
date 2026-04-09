from django.db import migrations


def reopen_pending_matched_intakes(apps, schema_editor):
    StudentIntake = apps.get_model('boxcore', 'StudentIntake')
    StudentIntake.objects.filter(status='matched', linked_student__isnull=True).update(status='reviewing')


def restore_matched_status(apps, schema_editor):
    StudentIntake = apps.get_model('boxcore', 'StudentIntake')
    StudentIntake.objects.filter(status='reviewing', linked_student__isnull=True).update(status='matched')


class Migration(migrations.Migration):
    dependencies = [
        ('boxcore', '0013_unique_blind_indices'),
    ]

    operations = [
        migrations.RunPython(reopen_pending_matched_intakes, restore_matched_status),
    ]
