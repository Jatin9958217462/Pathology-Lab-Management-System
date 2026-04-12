from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0010_labsettings_new_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        migrations.CreateModel(
            name='TestProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('profile_code', models.CharField(editable=False, max_length=30, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('short_code', models.CharField(blank=True, max_length=20)),
                ('description', models.TextField(blank=True)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tests', models.ManyToManyField(blank=True, related_name='profiles', to='lab.test')),
            ],
            options={'ordering': ['sort_order', 'name'], 'verbose_name': 'Test Profile'},
        ),

        migrations.CreateModel(
            name='SampleCollection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('tube_type', models.CharField(choices=[('EDTA','EDTA (Purple cap)'),('Plain','Plain (Red cap)'),('Fluoride','Fluoride (Grey cap)'),('Citrate','Sodium Citrate (Blue cap)'),('Heparin','Heparin (Green cap)'),('SST','SST (Gold cap)'),('Urine','Urine container'),('Stool','Stool container'),('Other','Other')], max_length=30)),
                ('tube_count', models.PositiveIntegerField(default=1)),
                ('barcode', models.CharField(blank=True, max_length=50)),
                ('collected_at', models.DateTimeField(blank=True, null=True)),
                ('received_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending','Pending'),('collected','Collected'),('received','Lab Received'),('rejected','Rejected'),('processing','Processing')], default='pending', max_length=20)),
                ('remarks', models.CharField(blank=True, max_length=200)),
                ('temperature', models.CharField(blank=True, max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='samples', to='lab.booking')),
                ('collected_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='samples_collected', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['created_at']},
        ),

        migrations.CreateModel(
            name='HomeCollection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('address', models.TextField()),
                ('scheduled_date', models.DateField()),
                ('scheduled_time', models.TimeField()),
                ('status', models.CharField(choices=[('scheduled','Scheduled'),('assigned','Assigned'),('collected','Collected'),('cancelled','Cancelled')], default='scheduled', max_length=20)),
                ('collection_fee', models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ('remarks', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='home_collection', to='lab.booking')),
                ('phlebotomist', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='home_collections', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-scheduled_date', '-scheduled_time']},
        ),

        migrations.CreateModel(
            name='DoctorCommission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('month', models.DateField()),
                ('total_billing', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('commission_pct', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('commission_amt', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('pending','Pending'),('paid','Paid'),('hold','On Hold')], default='pending', max_length=20)),
                ('paid_on', models.DateField(blank=True, null=True)),
                ('remarks', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commissions', to='lab.doctor')),
                ('bookings', models.ManyToManyField(blank=True, to='lab.booking')),
            ],
            options={'ordering': ['-month']},
        ),

        migrations.CreateModel(
            name='ExpenseCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
            ],
        ),

        migrations.CreateModel(
            name='Expenditure',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('date', models.DateField()),
                ('description', models.CharField(max_length=300)),
                ('vendor', models.CharField(blank=True, max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_mode', models.CharField(choices=[('Cash','Cash'),('Bank Transfer','Bank Transfer'),('Cheque','Cheque'),('UPI','UPI')], default='Cash', max_length=30)),
                ('invoice_no', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='lab.expensecategory')),
                ('added_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date']},
        ),

        migrations.CreateModel(
            name='InventoryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('category', models.CharField(blank=True, max_length=100)),
                ('vendor', models.CharField(blank=True, max_length=200)),
                ('unit', models.CharField(choices=[('units','Units'),('ml','mL'),('L','Litre'),('g','Gram'),('kg','Kg'),('strips','Strips'),('vials','Vials'),('boxes','Boxes')], default='units', max_length=20)),
                ('current_stock', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('min_stock', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('unit_cost', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('last_restocked', models.DateField(blank=True, null=True)),
                ('expiry_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['category', 'name']},
        ),

        migrations.CreateModel(
            name='PatientNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('note', models.TextField()),
                ('note_type', models.CharField(choices=[('general','General'),('clinical','Clinical'),('allergy','Allergy/Alert'),('billing','Billing')], default='general', max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='lab.patient')),
                ('added_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),

        migrations.CreateModel(
            name='QCLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('date', models.DateField()),
                ('instrument', models.CharField(max_length=100)),
                ('test_name', models.CharField(max_length=100)),
                ('control_level', models.CharField(blank=True, max_length=50)),
                ('expected_value', models.CharField(blank=True, max_length=50)),
                ('obtained_value', models.CharField(blank=True, max_length=50)),
                ('result', models.CharField(choices=[('pass','Pass ✓'),('fail','Fail ✗'),('repeat','Repeat needed')], default='pass', max_length=20)),
                ('remarks', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('performed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date']},
        ),

        migrations.CreateModel(
            name='CriticalValueAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('parameter', models.CharField(max_length=200)),
                ('value', models.CharField(max_length=100)),
                ('normal_range', models.CharField(blank=True, max_length=100)),
                ('notified_to', models.CharField(blank=True, max_length=200)),
                ('notified_via', models.CharField(blank=True, max_length=50)),
                ('status', models.CharField(choices=[('pending','Pending'),('notified','Doctor Notified'),('acknowledged','Acknowledged')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='critical_alerts', to='lab.report')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
