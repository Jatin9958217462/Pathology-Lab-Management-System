from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0016_labsettings_pdf_header_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='labsettings',
            name='signer_image_height',
            field=models.PositiveIntegerField(
                default=30,
                help_text='Signature image height in PDF/Print (px).'
            ),
        ),
    ]
