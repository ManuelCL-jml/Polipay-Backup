# Generated by Django 3.1.2 on 2022-06-21 13:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paycash', '0003_paycashreference_comission_pay'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paycashregistranotificacionpago',
            name='emisor',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='paycashregistranotificacionpago',
            name='folio',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='paycashregistranotificacionpago',
            name='resultado',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='paycashregistranotificacionpago',
            name='secuencia',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='paycashregistranotificacionpago',
            name='tipo',
            field=models.IntegerField(),
        ),
    ]