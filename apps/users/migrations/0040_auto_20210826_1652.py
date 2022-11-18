# Generated by Django 3.1.2 on 2021-08-26 16:52

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0039_proveedores_tarj'),
    ]

    operations = [
        migrations.AddField(
            model_name='tarjeta',
            name='fecha_register',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tarjeta',
            name='rel_proveedor',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.DO_NOTHING, to='users.proveedores_tarj'),
        ),
    ]