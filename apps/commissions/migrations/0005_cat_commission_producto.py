# Generated by Django 3.2.8 on 2022-01-21 11:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0006_caracteristicas_comision'),
        ('commissions', '0004_remove_cat_commission_producto'),
    ]

    operations = [
        migrations.AddField(
            model_name='cat_commission',
            name='producto',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.DO_NOTHING, to='productos.producto'),
        ),
    ]