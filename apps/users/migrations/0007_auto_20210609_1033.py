# Generated by Django 3.1.2 on 2021-06-09 10:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_auto_20210603_1414'),
    ]

    operations = [
        migrations.AddField(
            model_name='persona',
            name='photo',
            field=models.FileField(default=None, upload_to='Photo'),
        ),
    ]