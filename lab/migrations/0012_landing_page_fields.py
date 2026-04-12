from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0011_new_lab_features'),
    ]

    operations = [
        migrations.AddField(model_name='labsettings', name='landing_patients',
            field=models.CharField(default='5000+', max_length=20)),
        migrations.AddField(model_name='labsettings', name='landing_tests',
            field=models.CharField(default='200+', max_length=20)),
        migrations.AddField(model_name='labsettings', name='landing_years',
            field=models.CharField(default='10+', max_length=20)),
        migrations.AddField(model_name='labsettings', name='about_text',
            field=models.TextField(blank=True, default='We are committed to providing accurate, reliable and timely diagnostic services.')),
        migrations.AddField(model_name='labsettings', name='services_text',
            field=models.TextField(blank=True, default='Comprehensive range of pathology tests covering all major specialties.')),
        migrations.AddField(model_name='labsettings', name='feedback_email',
            field=models.EmailField(blank=True)),
    ]
