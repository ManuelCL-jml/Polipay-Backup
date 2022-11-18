# Generated by Django 3.1.2 on 2021-06-03 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_auto_20210603_1327'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentos',
            name='tdocumento',
            field=models.CharField(choices=[('A', 'Acta Nacimiento/constitutiva'), ('R', 'RFC'), ('C', 'Constancia'), ('I', 'Identificacion'), ('U', 'Curp'), ('N', 'S/E')], default='N', max_length=1),
        ),
    ]
