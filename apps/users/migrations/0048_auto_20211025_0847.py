# Generated by Django 3.1.2 on 2021-10-25 08:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0047_delete_contactus'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tarjeta',
            name='cvc',
            field=models.CharField(blank=True, default='n/a', max_length=24),
        ),
        migrations.AlterField(
            model_name='tarjeta',
            name='nip',
            field=models.CharField(blank=True, default=None, max_length=24, null=True),
        ),
    ]
