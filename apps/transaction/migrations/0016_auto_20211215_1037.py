# Generated by Django 3.1.2 on 2021-12-15 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transaction', '0015_auto_20211130_0939'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transferencia',
            name='rfc_curp_beneficiario',
            field=models.CharField(blank=True, max_length=13, null=True),
        ),
    ]