# Generated by Django 3.1.2 on 2022-02-12 16:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0056_auto_20220212_1627'),
    ]

    operations = [
        migrations.AlterField(
            model_name='concentradosauxiliar',
            name='id',
            field=models.AutoField(editable=False, primary_key=True, serialize=False),
        ),
    ]