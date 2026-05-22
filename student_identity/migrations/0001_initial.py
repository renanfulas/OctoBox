# Hybrid squash 0001-0009 (Sprint 2 schema-per-tenant migration).
#
# Originalmente esta era a migracao 0001_initial gerada pelo Django quando
# StudentIdentity/StudentBoxMembership/StudentAppInvitation/StudentTransfer
# tinham FKs para boxcore.Student (cross-schema, frigil). Esta versao foi
# RE-ESCRITA para refletir o estado pos Sprint 2: sem FKs cross-schema,
# usando student_id: IntegerField (referencia fraca) + student_name
# denormalizado + box: FK(control.Box).
#
# Esta migracao agora consolida o que originalmente eram 0001 + 0002 + 0003
# + 0004 + 0005 + 0006 + 0007(photo) + 0007(push) + 0008(merge) + 0009.
# As migracoes 0002-0008 foram REMOVIDAS; 0009 permanece como marker vazio
# para preservar a dependencia historica de boxcore/0026.
#
# Decisao tomada em pilot controlado (ver §3.5 de docs/plans/
# schema-per-tenant-migration-plan.md): banco de dev/pilot e descartavel.

import django.db.models.deletion
import django.utils.timezone
import student_identity.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('control', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentAppInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('token', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('invite_type', models.CharField(choices=[('individual', 'Individual'), ('open_box', 'Box com aprovacao')], db_index=True, default='individual', max_length=16)),
                ('student_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('student_name', models.CharField(blank=True, max_length=150)),
                ('box_root_slug', models.CharField(db_index=True, default=student_identity.models._default_box_root_slug, max_length=64)),
                ('invited_email', models.EmailField(blank=True, max_length=254)),
                ('onboarding_journey', models.CharField(choices=[('mass_box_invite', 'Link em massa do box'), ('imported_lead_invite', 'Lead importado'), ('registered_student_invite', 'Aluno ja cadastrado')], db_index=True, default='registered_student_invite', max_length=32)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('box', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_invitations', to='control.box')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_app_invitations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StudentIdentity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('student_name', models.CharField(blank=True, db_index=True, max_length=150)),
                ('box_root_slug', models.CharField(db_index=True, default=student_identity.models._default_box_root_slug, max_length=64)),
                ('primary_box_root_slug', models.CharField(db_index=True, default=student_identity.models._default_box_root_slug, max_length=64)),
                ('provider', models.CharField(choices=[('google', 'Google'), ('apple', 'Apple')], max_length=16)),
                ('provider_subject', models.CharField(max_length=255, unique=True)),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('status', models.CharField(choices=[('pending', 'Pendente'), ('active', 'Ativa'), ('transferred', 'Transferida'), ('blocked', 'Bloqueada')], db_index=True, default='pending', max_length=16)),
                ('invited_at', models.DateTimeField(blank=True, null=True)),
                ('activated_at', models.DateTimeField(blank=True, null=True)),
                ('last_authenticated_at', models.DateTimeField(blank=True, null=True)),
                ('photo_url', models.URLField(blank=True, max_length=500)),
                ('box', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_identities', to='control.box')),
                ('primary_box', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='primary_student_identities', to='control.box')),
            ],
            options={
                'ordering': ['student_name'],
            },
        ),
        migrations.CreateModel(
            name='StudentBoxInviteLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('token', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('box_root_slug', models.CharField(db_index=True, default=student_identity.models._default_box_root_slug, max_length=64)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('max_uses', models.PositiveIntegerField(default=200)),
                ('use_count', models.PositiveIntegerField(default=0)),
                ('paused_at', models.DateTimeField(blank=True, null=True)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('box', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_invite_links', to='control.box')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_box_invite_links', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StudentInvitationDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('channel', models.CharField(choices=[('email', 'E-mail'), ('whatsapp', 'WhatsApp')], max_length=16)),
                ('provider', models.CharField(db_index=True, max_length=32)),
                ('status', models.CharField(choices=[('sent', 'Enviado'), ('failed', 'Falhou'), ('delivered', 'Entregue'), ('delayed', 'Atrasado'), ('bounced', 'Bounce'), ('complained', 'Reclamado'), ('suppressed', 'Suprimido')], db_index=True, max_length=16)),
                ('recipient', models.CharField(max_length=255)),
                ('provider_message_id', models.CharField(blank=True, max_length=120)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('failed_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.CharField(blank=True, max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('invitation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to='student_identity.studentappinvitation')),
                ('requested_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_invitation_deliveries', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StudentInvitationDeliveryEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider_event_id', models.CharField(db_index=True, max_length=120, unique=True)),
                ('provider', models.CharField(db_index=True, max_length=32)),
                ('event_type', models.CharField(db_index=True, max_length=64)),
                ('occurred_at', models.DateTimeField(blank=True, null=True)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('delivery', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='student_identity.studentinvitationdelivery')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StudentBoxMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('box_root_slug', models.CharField(db_index=True, max_length=64)),
                ('status', models.CharField(choices=[('pending_approval', 'Aguardando aprovacao'), ('active', 'Ativo'), ('inactive', 'Inativo'), ('suspended_financial', 'Suspenso financeiro'), ('revoked', 'Revogado'), ('expired', 'Expirado')], db_index=True, default='pending_approval', max_length=24)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('last_access_at', models.DateTimeField(blank=True, null=True)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('revoked_reason', models.CharField(blank=True, max_length=255)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_student_box_memberships', to=settings.AUTH_USER_MODEL)),
                ('box', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_memberships', to='control.box')),
                ('created_from_invite', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='memberships_created', to='student_identity.studentappinvitation')),
                ('identity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='student_identity.studentidentity')),
            ],
            options={
                'ordering': ['box_root_slug'],
                'constraints': [models.UniqueConstraint(fields=('identity', 'box_root_slug'), name='unique_student_membership_per_identity_box')],
            },
        ),
        migrations.CreateModel(
            name='StudentTransfer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('from_box_root_slug', models.CharField(max_length=64)),
                ('to_box_root_slug', models.CharField(max_length=64)),
                ('status', models.CharField(choices=[('requested', 'Solicitada'), ('completed', 'Concluida'), ('canceled', 'Cancelada')], db_index=True, default='requested', max_length=16)),
                ('effective_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('audit_summary', models.TextField(blank=True)),
                ('from_box', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transfers_from', to='control.box')),
                ('to_box', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transfers_to', to='control.box')),
                ('identity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfers', to='student_identity.studentidentity')),
                ('requested_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='requested_student_transfers', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StudentPushSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('box_root_slug', models.CharField(db_index=True, default=student_identity.models._default_box_root_slug, max_length=64)),
                ('endpoint', models.CharField(db_index=True, max_length=500, unique=True)),
                ('subscription', models.JSONField(blank=True, default=dict)),
                ('device_fingerprint', models.CharField(blank=True, db_index=True, max_length=64)),
                ('user_agent', models.CharField(blank=True, max_length=255)),
                ('last_seen_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('last_push_sent_at', models.DateTimeField(blank=True, null=True)),
                ('last_error_at', models.DateTimeField(blank=True, null=True)),
                ('last_error_message', models.CharField(blank=True, max_length=255)),
                ('revoked_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('box', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_push_subscriptions', to='control.box')),
                ('identity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='push_subscriptions', to='student_identity.studentidentity')),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='studentidentity',
            constraint=models.UniqueConstraint(condition=models.Q(('status__in', ['pending', 'active'])), fields=('email', 'box_root_slug'), name='unique_student_identity_email_box_when_live'),
        ),
    ]
