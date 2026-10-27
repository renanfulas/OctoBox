from django.db import migrations, models


def mark_legacy_qa_seed_invitations(apps, schema_editor):
    StudentAppInvitation = apps.get_model('student_identity', 'StudentAppInvitation')
    StudentAppInvitation.objects.using(schema_editor.connection.alias).filter(
        invited_email__iendswith='@qa.seed',
    ).update(is_qa_seed=True)


class Migration(migrations.Migration):

    dependencies = [
        ('student_identity', '0006_studentidentity_email_lookup_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentappinvitation',
            name='is_qa_seed',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            mark_legacy_qa_seed_invitations,
            migrations.RunPython.noop,
        ),
    ]
