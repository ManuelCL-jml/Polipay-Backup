# Generated by Django 3.1.2 on 2021-09-27 13:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0002_auto_20210818_1031'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudes',
            name='dato_json',
            field=models.TextField(null=True),
        ),
    ]
