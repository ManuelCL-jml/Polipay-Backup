# Generated by Django 3.1.2 on 2021-07-26 00:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0029_persona_nip'),
    ]

    operations = [
        migrations.AlterField(
            model_name='persona',
            name='nip',
            field=models.CharField(blank=True, default=None, max_length=10, null=True),
        ),
    ]
