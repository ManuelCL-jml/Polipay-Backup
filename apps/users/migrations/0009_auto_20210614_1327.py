# Generated by Django 3.1.2 on 2021-06-14 13:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_auto_20210609_1133'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentos',
            name='documento',
            field=models.FileField(default='No se cargo el documento', upload_to='documento'),
        ),
    ]
