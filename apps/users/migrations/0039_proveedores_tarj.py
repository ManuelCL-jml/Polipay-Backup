# Generated by Django 3.1.2 on 2021-08-26 16:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0038_cuenta_rel_cuenta_prod'),
    ]

    operations = [
        migrations.CreateModel(
            name='proveedores_tarj',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, unique=True)),
                ('nombre', models.CharField(max_length=20, null=True, unique=True)),
                ('descripcion', models.CharField(max_length=20, null=True)),
            ],
        ),
    ]
