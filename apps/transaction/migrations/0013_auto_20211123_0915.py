# Generated by Django 3.2.8 on 2021-11-23 09:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transaction', '0012_transmasivaprog'),
    ]

    operations = [
        migrations.AddField(
            model_name='transferencia',
            name='receiving_bank',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='banco_beneficiario', to='transaction.bancos'),
        ),
        migrations.AddField(
            model_name='transferencia',
            name='transmitter_bank',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='banco_emisor', to='transaction.bancos'),
        ),
    ]
