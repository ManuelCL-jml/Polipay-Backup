# Generated by Django 3.1.2 on 2021-07-09 16:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_comisiones_productos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='persona',
            name='clabeinterbancaria_dos',
            field=models.CharField(blank=True, max_length=18, null=True),
        ),
        migrations.AlterField(
            model_name='persona',
            name='clabeinterbancaria_uno',
            field=models.CharField(blank=True, max_length=18, null=True),
        ),
    ]
