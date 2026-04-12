from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0015_doctor_linked_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='labsettings',
            name='pdf_header_image',
            field=models.ImageField(
                blank=True, null=True, upload_to='branding/',
                help_text='PDF Header image — shown at top of PDF & Bulk PDF (not in direct print)'
            ),
        ),
    ]
