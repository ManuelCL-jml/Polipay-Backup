# Generated by Django 3.1.2 on 2022-06-17 10:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0060_persona_name_stp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cuenta',
            name='cuenta',
            field=models.CharField(editable=False, max_length=16),
        ),
        migrations.AlterField(
            model_name='cuenta',
            name='cuentaclave',
            field=models.CharField(blank=True, editable=False, max_length=18, null=True),
        ),
    ]
