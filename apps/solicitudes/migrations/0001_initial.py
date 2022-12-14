# Generated by Django 3.1.2 on 2021-07-19 14:05

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EdoSolicitud',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('nombreEdo', models.CharField(max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='TipoSolicitud',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('nombreSol', models.CharField(max_length=30)),
                ('descripcionSol', models.CharField(max_length=254)),
            ],
        ),
        migrations.CreateModel(
            name='Solicitudes',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=100)),
                ('fechaSolicitud', models.DateTimeField(auto_now_add=True)),
                ('intentos', models.IntegerField(null=True)),
                ('estado', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='solicitudes.edosolicitud')),
                ('personaSolicitud', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
                ('tipoSolicitud', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='solicitudes.tiposolicitud')),
            ],
        ),
    ]
