# Generated by Django 3.1.2 on 2021-10-25 08:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transaction', '0007_transferencia_saldo_remanente'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transferencia',
            name='referencia_numerica',
            field=models.CharField(max_length=24),
        ),
        migrations.CreateModel(
            name='detalleTransferencia',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, unique=True)),
                ('fecharegistro', models.DateTimeField(auto_now_add=True)),
                ('detalleT', models.TextField(default='por detallar', max_length=254)),
                ('transferReferida', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='transaction.transferencia')),
            ],
        ),
    ]
