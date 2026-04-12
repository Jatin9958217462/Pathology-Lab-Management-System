from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0012_landing_page_fields'),
    ]

    operations = [
        # Add unique_code to UserProfile
        migrations.AddField(
            model_name='userprofile',
            name='unique_code',
            field=models.CharField(
                blank=True, null=True, max_length=20, unique=True,
                help_text='Auto-generated unique code for staff/doctor report access'
            ),
        ),
        # Add pro_suite_password to LabSettings
        migrations.AddField(
            model_name='labsettings',
            name='pro_suite_password',
            field=models.CharField(
                max_length=100, default='Jatin123',
                help_text='Password to unlock Pro Suite (Payments, Finance, etc.)'
            ),
        ),
        # Add nabl_text to LabSettings
        migrations.AddField(
            model_name='labsettings',
            name='nabl_text',
            field=models.CharField(
                max_length=300, blank=True, default='NABL',
                help_text='Accreditation/certification text (e.g. NABL, ISO 9001:2015). Shown on reports.'
            ),
        ),
    ]
