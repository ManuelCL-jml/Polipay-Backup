# Generated by Django 3.2.8 on 2022-02-03 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0006_edosolicitud_descripcion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitudes',
            name='nombre',
            field=models.CharField(max_length=254),
        ),
    ]
