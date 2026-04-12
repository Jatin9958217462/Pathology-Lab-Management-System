"""
Migration 0009 — adds all new feature models:
  Branch, NotificationLog, PaymentOrder, InsuranceCompany, InsuranceClaim,
  HL7FHIRLog, AnalyserInterface, AnalyserResult, AIInterpretation, MobileDeviceToken
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0008_alter_booking_id_alter_doctor_id_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── Branch ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('branch_id', models.CharField(editable=False, max_length=20, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('address', models.TextField(blank=True)),
                ('phone', models.CharField(blank=True, max_length=100)),
                ('email', models.EmailField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name_plural': 'Branches'},
        ),

        # ── NotificationLog ─────────────────────────────────────────────────
        migrations.CreateModel(
            name='NotificationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel', models.CharField(choices=[('sms', 'SMS'), ('whatsapp', 'WhatsApp')], default='sms', max_length=20)),
                ('mobile', models.CharField(max_length=20)),
                ('message', models.TextField()),
                ('status', models.CharField(choices=[('sent', 'Sent'), ('delivered', 'Delivered'), ('failed', 'Failed'), ('pending', 'Pending')], default='pending', max_length=20)),
                ('provider_ref', models.CharField(blank=True, max_length=100)),
                ('error_msg', models.TextField(blank=True)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='lab.patient')),
                ('related_report', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='lab.report')),
            ],
            options={'ordering': ['-sent_at']},
        ),

        # ── PaymentOrder ────────────────────────────────────────────────────
        migrations.CreateModel(
            name='PaymentOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('razorpay_order_id', models.CharField(max_length=100, unique=True)),
                ('razorpay_payment_id', models.CharField(blank=True, max_length=100)),
                ('razorpay_signature', models.CharField(blank=True, max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='INR', max_length=5)),
                ('status', models.CharField(choices=[('created', 'Created'), ('attempted', 'Attempted'), ('paid', 'Paid'), ('failed', 'Failed'), ('refunded', 'Refunded')], default='created', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_orders', to='lab.booking')),
            ],
            options={'ordering': ['-created_at']},
        ),

        # ── InsuranceCompany ────────────────────────────────────────────────
        migrations.CreateModel(
            name='InsuranceCompany',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('tpa_name', models.CharField(blank=True, max_length=200)),
                ('contact', models.CharField(blank=True, max_length=100)),
                ('email', models.EmailField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['name']},
        ),

        # ── InsuranceClaim ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='InsuranceClaim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('claim_no', models.CharField(editable=False, max_length=50, unique=True)),
                ('policy_number', models.CharField(blank=True, max_length=100)),
                ('member_id', models.CharField(blank=True, max_length=100)),
                ('claim_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('approved_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('under_review', 'Under Review'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('settled', 'Settled')], default='draft', max_length=20)),
                ('remarks', models.TextField(blank=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('settled_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='insurance_claims', to='lab.booking')),
                ('insurance_co', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='lab.insurancecompany')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),

        # ── HL7FHIRLog ──────────────────────────────────────────────────────
        migrations.CreateModel(
            name='HL7FHIRLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('direction', models.CharField(choices=[('outbound', 'Outbound (to HIS)'), ('inbound', 'Inbound (from HIS)')], max_length=20)),
                ('msg_type', models.CharField(choices=[('ORU_R01', 'ORU^R01 — Lab Result'), ('ORM_O01', 'ORM^O01 — Order'), ('ADT_A01', 'ADT^A01 — Admission'), ('FHIR_Bundle', 'FHIR Bundle'), ('FHIR_DiagReport', 'FHIR DiagnosticReport')], max_length=30)),
                ('raw_message', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('sent', 'Sent'), ('ack', 'Acknowledged'), ('error', 'Error')], default='sent', max_length=20)),
                ('error_detail', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('patient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='lab.patient')),
                ('report', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='lab.report')),
            ],
            options={'ordering': ['-created_at']},
        ),

        # ── AnalyserInterface ───────────────────────────────────────────────
        migrations.CreateModel(
            name='AnalyserInterface',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('protocol', models.CharField(choices=[('ASTM', 'ASTM E1394'), ('HL7', 'HL7 2.x'), ('CSV', 'CSV/TXT file'), ('SERIAL', 'Serial port'), ('TCP', 'TCP/IP socket')], default='ASTM', max_length=20)),
                ('host', models.CharField(blank=True, max_length=200)),
                ('port', models.PositiveIntegerField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('test_mapping', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),

        # ── AnalyserResult ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='AnalyserResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sample_id', models.CharField(max_length=100)),
                ('raw_data', models.TextField()),
                ('parsed_json', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('pending', 'Pending import'), ('imported', 'Imported to report'), ('error', 'Import error'), ('ignored', 'Ignored')], default='pending', max_length=20)),
                ('error_detail', models.TextField(blank=True)),
                ('received_at', models.DateTimeField(auto_now_add=True)),
                ('analyser', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='lab.analyserinterface')),
                ('linked_report', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='lab.report')),
            ],
            options={'ordering': ['-received_at']},
        ),

        # ── AIInterpretation ────────────────────────────────────────────────
        migrations.CreateModel(
            name='AIInterpretation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('interpretation', models.TextField(blank=True)),
                ('flags_summary', models.TextField(blank=True)),
                ('severity', models.CharField(blank=True, choices=[('normal', 'Normal'), ('mild', 'Mild concern'), ('moderate', 'Moderate concern'), ('critical', 'Critical')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('generated', 'Generated'), ('reviewed', 'Reviewed'), ('approved', 'Approved')], default='pending', max_length=20)),
                ('model_used', models.CharField(default='rule-based-v1', max_length=100)),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('report', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ai_interpretation', to='lab.report')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),

        # ── MobileDeviceToken ───────────────────────────────────────────────
        migrations.CreateModel(
            name='MobileDeviceToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.TextField()),
                ('platform', models.CharField(choices=[('android', 'Android'), ('ios', 'iOS')], default='android', max_length=10)),
                ('is_active', models.BooleanField(default=True)),
                ('registered_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='device_tokens', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
