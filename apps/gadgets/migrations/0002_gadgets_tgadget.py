# Generated by Django 3.1.2 on 2021-07-26 14:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gadgets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='gadgets',
            name='tGadget',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.DO_NOTHING, to='gadgets.tipos'),
        ),
    ]
