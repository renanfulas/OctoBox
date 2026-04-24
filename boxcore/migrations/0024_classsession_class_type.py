from django.db import migrations, models


CLASS_TYPE_KEYWORDS = (
    ('mobility', ('mob', 'mobilidade', 'alongamento', 'flexibilidade', 'flow')),
    ('oly', ('halterofilia', 'oly', 'olimpic', 'olimpica', 'olympic', 'weightlifting', 'clean', 'snatch')),
    ('strength', ('forca', 'strength', 'powerlifting', 'levantamento')),
    ('open_gym', ('open gym', 'open-gym', 'livre', 'uso livre')),
    ('cross', ('crossfit', 'cross', 'wod', 'metcon')),
)


def infer_class_type(title):
    normalized = (title or '').strip().lower()
    if not normalized:
        return 'other'
    for class_type, keywords in CLASS_TYPE_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return class_type
    return 'other'


def backfill_class_type(apps, schema_editor):
    ClassSession = apps.get_model('boxcore', 'ClassSession')
    for session in ClassSession.objects.all().only('id', 'title'):
        inferred = infer_class_type(session.title)
        ClassSession.objects.filter(pk=session.pk).update(class_type=inferred)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0023_alter_asyncjob_status_alter_studentintake_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='classsession',
            name='class_type',
            field=models.CharField(
                choices=[
                    ('cross', 'CrossFit'),
                    ('mobility', 'Mobilidade / Alongamento'),
                    ('oly', 'Halterofilia'),
                    ('strength', 'Forca'),
                    ('open_gym', 'Open Gym'),
                    ('other', 'Outro'),
                ],
                db_index=True,
                default='other',
                max_length=24,
            ),
        ),
        migrations.RunPython(backfill_class_type, noop_reverse),
    ]
