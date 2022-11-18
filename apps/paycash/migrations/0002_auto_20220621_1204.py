# Generated by Django 3.1.2 on 2022-06-21 12:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('paycash', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PayCashRegistraNotificacionPago',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, unique=True)),
                ('folio', models.IntegerField(max_length=11)),
                ('resultado', models.IntegerField(max_length=5)),
                ('tipo', models.IntegerField(max_length=2)),
                ('emisor', models.IntegerField(max_length=11)),
                ('secuencia', models.IntegerField(max_length=11)),
                ('monto', models.FloatField()),
                ('fecha', models.CharField(max_length=20)),
                ('hora', models.CharField(max_length=20)),
                ('autorizacion', models.CharField(max_length=20)),
                ('referencia', models.CharField(max_length=40)),
                ('value', models.CharField(max_length=40)),
                ('fecha_creacion', models.DateTimeField()),
                ('fecha_confirmacion', models.DateTimeField()),
                ('fecha_vencimiento', models.DateTimeField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('reference', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='paycash.paycashreference')),
            ],
        ),
        migrations.DeleteModel(
            name='PayCashPagos',
        ),
    ]