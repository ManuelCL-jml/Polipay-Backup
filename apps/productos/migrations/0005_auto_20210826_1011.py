# Generated by Django 3.1.2 on 2021-08-26 10:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0004_auto_20210825_1545'),
    ]

    operations = [
        migrations.AlterField(
            model_name='caracteristicas',
            name='fecha_registro',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
