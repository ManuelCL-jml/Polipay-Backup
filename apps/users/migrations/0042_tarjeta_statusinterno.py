# Generated by Django 3.1.2 on 2021-09-13 17:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0041_auto_20210913_1657'),
    ]

    operations = [
        migrations.AddField(
            model_name='tarjeta',
            name='statusInterno',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.DO_NOTHING, to='users.statuspolipay'),
        ),
    ]