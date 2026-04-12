from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0003_honorific_age_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='labsettings',
            name='signer1_name',
            field=models.CharField(default='Dr. M. SALEEM', max_length=100),
        ),
        migrations.AddField(
            model_name='labsettings',
            name='signer1_qual',
            field=models.CharField(default='(MD)\n(LabIncharge)', max_length=200),
        ),
        migrations.AddField(
            model_name='labsettings',
            name='signer2_name',
            field=models.CharField(default='N.KUMAR', max_length=100),
        ),
        migrations.AddField(
            model_name='labsettings',
            name='signer2_qual',
            field=models.CharField(default='(MLT)\n(Sr.Lab Tech.)', max_length=200),
        ),
        migrations.AddField(
            model_name='labsettings',
            name='signer3_name',
            field=models.CharField(default='Dr. V.P.MAURYA', max_length=100),
        ),
        migrations.AddField(
            model_name='labsettings',
            name='signer3_qual',
            field=models.CharField(default='MBBS(AM),B.Sc. MLT\n(Sr.Lab Tech.)', max_length=200),
        ),
        migrations.AddField(
            model_name='labsettings',
            name='signer4_name',
            field=models.CharField(default='Dr. M. AHMAD ANSARI', max_length=100),
        ),
        migrations.AddField(
            model_name='labsettings',
            name='signer4_qual',
            field=models.CharField(default='Consultant Biochemistry\nPhD.( AIIMS)', max_length=200),
        ),
        migrations.AddField(
            model_name='labsettings',
            name='footer_image',
            field=models.ImageField(
                blank=True, null=True,
                upload_to='branding/',
                help_text='Footer letterhead image (shown at bottom of PDF)'
            ),
        ),
    ]
