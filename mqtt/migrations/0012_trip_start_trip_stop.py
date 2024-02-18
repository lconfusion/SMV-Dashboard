# Generated by Django 4.2.7 on 2024-02-01 02:50

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('mqtt', '0011_remove_mqtterror_ip_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='start',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='trip',
            name='stop',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
