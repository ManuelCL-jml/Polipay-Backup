# Generated by Django 3.1.2 on 2021-10-12 16:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0003_solicitudes_dato_json'),
    ]

    operations = [
        migrations.CreateModel(
            name='Detalle_solicitud',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('fechaReg', models.DateTimeField(auto_now_add=True)),
                ('fechaEntrega', models.DateField()),
                ('fechaEntregaNew', models.DateTimeField()),
                ('detalle', models.TextField()),
                ('edodetail', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='solicitudes.edosolicitud')),
                ('sol_rel', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='solicitudes.solicitudes')),
            ],
        ),
    ]
