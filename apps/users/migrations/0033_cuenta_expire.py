# Generated by Django 3.1.2 on 2021-07-27 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0032_merge_20210726_1406'),
    ]

    operations = [
        migrations.AddField(
            model_name='cuenta',
            name='expire',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
