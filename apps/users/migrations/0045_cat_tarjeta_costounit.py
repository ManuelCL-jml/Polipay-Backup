# Generated by Django 3.1.2 on 2021-09-28 16:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0044_auto_20210927_1304'),
    ]

    operations = [
        migrations.AddField(
            model_name='cat_tarjeta',
            name='costoUnit',
            field=models.FloatField(default=10),
        ),
    ]
