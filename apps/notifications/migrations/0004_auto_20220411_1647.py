# Generated by Django 3.1.2 on 2022-04-11 16:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0003_notification_transaction'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='json_content',
            field=models.TextField(),
        ),
    ]