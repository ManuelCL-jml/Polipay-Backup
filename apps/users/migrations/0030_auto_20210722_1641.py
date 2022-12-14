# Generated by Django 3.1.2 on 2021-07-22 16:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0029_auto_20210722_1638'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentos',
            name='tdocumento',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.DO_NOTHING, related_name='tipo_documento', to='users.tdocumento'),
        ),
        migrations.AlterField(
            model_name='tdocumento',
            name='descripcion',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
