# Generated by Django 3.1.2 on 2022-04-28 08:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0058_auto_20220311_1131'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cuenta',
            name='cuenta',
            field=models.CharField(editable=False, max_length=16, unique=True),
        ),
        migrations.AlterField(
            model_name='cuenta',
            name='cuentaclave',
            field=models.CharField(blank=True, editable=False, max_length=18, null=True, unique=True),
        ),
    ]
