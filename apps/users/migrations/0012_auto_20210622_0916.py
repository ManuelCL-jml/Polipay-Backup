# Generated by Django 3.1.2 on 2021-06-22 09:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_auto_20210621_1533'),
    ]

    operations = [
        migrations.AlterField(
            model_name='corte',
            name='fecha',
            field=models.DateField(auto_now_add=True),
        ),
    ]
