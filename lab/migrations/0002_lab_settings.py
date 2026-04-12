from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('lab', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='LabSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('lab_name', models.CharField(default='Indian Path-Lab', max_length=200)),
                ('tagline', models.CharField(default='AN ISO 9001:2015 CERTIFIED LAB', max_length=200)),
                ('unit_text', models.CharField(default='A UNIT OF PMEGP GOVT. OF INDIA', max_length=200)),
                ('email', models.EmailField(default='indianpathlab@gmail.com', max_length=254)),
                ('phone', models.CharField(default='9213303786, 9971404170', max_length=100)),
                ('address', models.TextField(default='C-451, Gali No. 5, Old Mustafabad,\n(Lovely Public School Market)\nNear Tirpal Factory, DELHI-110094')),
                ('logo_image', models.ImageField(blank=True, null=True, upload_to='branding/')),
                ('letterhead_image', models.ImageField(blank=True, null=True, upload_to='branding/')),
                ('signature_ansari', models.ImageField(blank=True, null=True, upload_to='branding/')),
                ('signature_saleem', models.ImageField(blank=True, null=True, upload_to='branding/')),
                ('signature_kumar', models.ImageField(blank=True, null=True, upload_to='branding/')),
                ('signature_maurya', models.ImageField(blank=True, null=True, upload_to='branding/')),
                ('pdf_footer_text', models.TextField(blank=True, default='Note : Above Mentioned Finding Are Professional Opinion and Not a Final Diagnosis All Laboratory Test & Other Investigation Results are to be Corelate Clinical Pathology. Discrepancies if any Necessitate Review Repeat of the Test Contact, Laboratory Immediately This Report is for the perusal for physician/Doctors only.\nNot Valid for Medico Legal Purpose (Court Cases)')),
                ('pdf_footer_image', models.ImageField(blank=True, null=True, upload_to='branding/')),
                ('show_timing_bar', models.BooleanField(default=True)),
                ('timing_text', models.CharField(default='Timing : 9 A.M. to 9 P.M. (Sunday Evening Closed)', max_length=200)),
                ('facilities_text', models.TextField(default='Facilities : X-Ray, E.C.G., Examination of Blood, Urine, Stool, Sputum, Semen & All Spl. Test')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Lab Settings', 'verbose_name_plural': 'Lab Settings'},
        ),
        migrations.CreateModel(
            name='TestNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('note_text', models.TextField()),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('test', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='note', to='lab.test')),
            ],
        ),
        # Add custom_id field to Patient for editable ID display
        migrations.AddField(
            model_name='patient',
            name='custom_display_id',
            field=models.CharField(max_length=50, blank=True, help_text='Custom ID shown on reports (leave blank to use auto patient_id)'),
        ),
        # Add custom dates to Report
        migrations.AddField(
            model_name='report',
            name='sample_drawn_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='report',
            name='sample_received_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='report',
            name='result_reported_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='report',
            name='custom_report_no',
            field=models.CharField(max_length=50, blank=True, help_text='Custom receipt/report number shown on report'),
        ),
    ]
