from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0029_backfill_intake_outcome_markers'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='payment_source',
            field=models.CharField(
                choices=[('direct', 'Direto (aluno)'), ('wellhub', 'Wellhub (Gympass)'), ('totalpass', 'TotalPass')],
                db_index=True,
                default='direct',
                help_text='Quem fecha essa mensalidade com o box: o aluno direto ou um parceiro (Wellhub/TotalPass).',
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name='PartnerCheckInCharge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('partner', models.CharField(
                    choices=[('direct', 'Direto (aluno)'), ('wellhub', 'Wellhub (Gympass)'), ('totalpass', 'TotalPass')],
                    db_index=True,
                    max_length=16,
                )),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pendente'),
                        ('reminded', 'Lembrete enviado'),
                        ('confirmed', 'Confirmado pelo aluno'),
                        ('reconciled', 'Reconciliado com extrato'),
                        ('disputed', 'Em disputa'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=16,
                )),
                ('declared_value', models.DecimalField(
                    blank=True, decimal_places=2, max_digits=10, null=True,
                    help_text='So preenchido na reconciliacao com o extrato oficial do parceiro.',
                )),
                ('reminder_attempts', models.PositiveSmallIntegerField(default=0)),
                ('last_reminder_at', models.DateTimeField(blank=True, null=True)),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('reconciled_at', models.DateTimeField(blank=True, null=True)),
                ('statement_reference', models.CharField(blank=True, max_length=100)),
                ('notes', models.TextField(blank=True)),
                ('attendance', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='partner_checkin_charge',
                    to='boxcore.attendance',
                )),
                ('enrollment', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='partner_checkin_charges',
                    to='boxcore.enrollment',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
