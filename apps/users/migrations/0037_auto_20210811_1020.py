# Generated by Django 3.1.2 on 2021-08-11 10:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0036_auto_20210809_1112'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cuenta',
            name='cuentaclave',
            field=models.CharField(blank=True, editable=False, max_length=18, null=True),
        ),
    ]
