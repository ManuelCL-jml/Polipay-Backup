# Generated by Django 3.2.8 on 2022-01-25 13:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0006_caracteristicas_comision'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rel_serv_cara',
            name='comisiones',
        ),
        migrations.RemoveField(
            model_name='rel_serv_cara',
            name='service',
        ),
        migrations.DeleteModel(
            name='caracteristicas',
        ),
        migrations.DeleteModel(
            name='rel_serv_cara',
        ),
    ]
