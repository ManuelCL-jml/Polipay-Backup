# Generated by Django 3.1.2 on 2021-12-07 12:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transaction', '0015_auto_20211130_0939'),
        ('notifications', '0002_auto_20211206_1328'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='transaction',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='transaction.transferencia'),
        ),
    ]
