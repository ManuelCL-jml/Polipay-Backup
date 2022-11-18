# Generated by Django 3.1.2 on 2022-06-23 09:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transaction', '0019_auto_20220509_1222'),
        ('commissions', '0007_cat_commission_servicio'),
    ]

    operations = [
        migrations.AddField(
            model_name='commission_detail',
            name='commission_record',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='transferencia_comision_cobrada', to='transaction.transferencia'),
        ),
        migrations.AlterField(
            model_name='commission_detail',
            name='transaction_rel',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='transferencia_original', to='transaction.transferencia'),
        ),
    ]
