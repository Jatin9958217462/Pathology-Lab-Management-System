from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0014_testparam_default_value'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='doctor',
            name='linked_user',
            field=models.OneToOneField(
                blank=True,
                help_text='Portal user account linked to this doctor (for doctor panel access)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='doctor_profile',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
