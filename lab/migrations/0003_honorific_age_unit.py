from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('lab', '0002_lab_settings')]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='honorific',
            field=models.CharField(
                choices=[('Mr.','Mr.'),('Mrs.','Mrs.'),('Ms.','Ms.'),('Miss','Miss'),
                         ('Dr.','Dr.'),('Prof.','Prof.'),('Master','Master'),('Baby','Baby'),('M/s','M/s')],
                default='Mr.', max_length=10
            ),
        ),
        migrations.AddField(
            model_name='patient',
            name='age_unit',
            field=models.CharField(
                choices=[('Years','Years'),('Months','Months'),('Days','Days')],
                default='Years', max_length=10
            ),
        ),
        migrations.AlterField(
            model_name='patient',
            name='mobile',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
