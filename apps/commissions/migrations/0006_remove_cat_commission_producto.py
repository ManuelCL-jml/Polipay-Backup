# Generated by Django 3.2.8 on 2022-01-25 13:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('commissions', '0005_cat_commission_producto'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cat_commission',
            name='producto',
        ),
    ]
