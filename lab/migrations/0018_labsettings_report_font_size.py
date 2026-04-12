from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('lab', '0017_labsettings_signer_image_height'),
    ]
    operations = [
        migrations.AddField(
            model_name='labsettings',
            name='report_font_size',
            field=models.PositiveIntegerField(
                default=12,
                help_text='Base font size for printed/PDF reports (pt). Recommended: 10–14.'
            ),
        ),
    ]
