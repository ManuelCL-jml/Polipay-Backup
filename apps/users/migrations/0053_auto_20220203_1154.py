# Generated by Django 3.2.8 on 2022-02-03 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0052_alter_persona_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='tarjeta',
            name='deletion_date',
            field=models.DateTimeField(default=None),
        ),
        migrations.AddField(
            model_name='tarjeta',
            name='was_eliminated',
            field=models.BooleanField(default=False),
        ),
    ]
