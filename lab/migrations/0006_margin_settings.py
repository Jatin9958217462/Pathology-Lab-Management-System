from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0005_update_test_parameters'),
    ]

    operations = [
        # Single Report
        migrations.AddField(model_name='labsettings', name='print_single_margin_top',    field=models.PositiveIntegerField(default=100)),
        migrations.AddField(model_name='labsettings', name='print_single_margin_bottom', field=models.PositiveIntegerField(default=96)),
        migrations.AddField(model_name='labsettings', name='print_single_margin_left',   field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='print_single_margin_right',  field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='pdf_single_margin_top',      field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='pdf_single_margin_bottom',   field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='pdf_single_margin_left',     field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='pdf_single_margin_right',    field=models.PositiveIntegerField(default=0)),
        # Bulk Report
        migrations.AddField(model_name='labsettings', name='print_bulk_margin_top',      field=models.PositiveIntegerField(default=100)),
        migrations.AddField(model_name='labsettings', name='print_bulk_margin_bottom',   field=models.PositiveIntegerField(default=96)),
        migrations.AddField(model_name='labsettings', name='print_bulk_margin_left',     field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='print_bulk_margin_right',    field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='pdf_bulk_margin_top',        field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='pdf_bulk_margin_bottom',     field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='pdf_bulk_margin_left',       field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='pdf_bulk_margin_right',      field=models.PositiveIntegerField(default=0)),
        # Bill
        migrations.AddField(model_name='labsettings', name='print_bill_margin_top',      field=models.PositiveIntegerField(default=100)),
        migrations.AddField(model_name='labsettings', name='print_bill_margin_bottom',   field=models.PositiveIntegerField(default=96)),
        migrations.AddField(model_name='labsettings', name='print_bill_margin_left',     field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='print_bill_margin_right',    field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='pdf_bill_margin_top',        field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='pdf_bill_margin_bottom',     field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='pdf_bill_margin_left',       field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='labsettings', name='pdf_bill_margin_right',      field=models.PositiveIntegerField(default=0)),
    ]
