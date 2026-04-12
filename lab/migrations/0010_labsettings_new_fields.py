from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0009_all_new_features'),
    ]

    operations = [
        migrations.AddField(model_name='labsettings', name='sms_provider',
            field=models.CharField(choices=[('none','Disabled'),('msg91','MSG91'),('twilio','Twilio')], default='none', max_length=20)),
        migrations.AddField(model_name='labsettings', name='msg91_auth_key',
            field=models.CharField(blank=True, max_length=200)),
        migrations.AddField(model_name='labsettings', name='msg91_sender_id',
            field=models.CharField(blank=True, default='IPLABS', max_length=10)),
        migrations.AddField(model_name='labsettings', name='msg91_template_id',
            field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='labsettings', name='twilio_account_sid',
            field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='labsettings', name='twilio_auth_token',
            field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='labsettings', name='twilio_from_number',
            field=models.CharField(blank=True, max_length=20)),
        migrations.AddField(model_name='labsettings', name='whatsapp_enabled',
            field=models.BooleanField(default=False)),
        migrations.AddField(model_name='labsettings', name='whatsapp_token',
            field=models.CharField(blank=True, max_length=300)),
        migrations.AddField(model_name='labsettings', name='whatsapp_phone_id',
            field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='labsettings', name='razorpay_key_id',
            field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='labsettings', name='razorpay_key_secret',
            field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='labsettings', name='razorpay_webhook_secret',
            field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='labsettings', name='his_endpoint_url',
            field=models.CharField(blank=True, max_length=300)),
        migrations.AddField(model_name='labsettings', name='his_auth_token',
            field=models.CharField(blank=True, max_length=200)),
        migrations.AddField(model_name='labsettings', name='ai_auto_interpret',
            field=models.BooleanField(default=True)),
        migrations.AddField(model_name='labsettings', name='openai_api_key',
            field=models.CharField(blank=True, max_length=200)),
    ]
