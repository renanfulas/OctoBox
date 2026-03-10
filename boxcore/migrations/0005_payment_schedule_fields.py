from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0004_student_profile_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='billing_group',
            field=models.CharField(blank=True, max_length=36),
        ),
        migrations.AddField(
            model_name='payment',
            name='installment_number',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='payment',
            name='installment_total',
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]