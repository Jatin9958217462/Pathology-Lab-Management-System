from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0006_margin_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='full_name',
            field=models.CharField(
                blank=True,
                max_length=300,
                help_text='Optional full name shown on reports (e.g. "Complete Blood Count" for CBC). Leave blank to use short name.',
            ),
        ),
    ]
