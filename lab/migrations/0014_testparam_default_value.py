from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('lab', '0013_staff_qr_prosuite'),
    ]
    operations = [
        migrations.AddField(
            model_name='testparameter',
            name='default_value',
            field=models.CharField(max_length=100, blank=True, default='',
                                   help_text='Default value auto-filled when no reading entered'),
        ),
    ]
