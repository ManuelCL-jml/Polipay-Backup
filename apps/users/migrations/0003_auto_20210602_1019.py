# Generated by Django 3.1.2 on 2021-06-02 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20210601_1539'),
    ]

    operations = [
        migrations.RenameField(
            model_name='documentos',
            old_name='dateauth',
            new_name='dateauthActa',
        ),
        migrations.AddField(
            model_name='documentos',
            name='dateauthConst',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='documentos',
            name='dateauthCurp',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='documentos',
            name='dateauthID',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='documentos',
            name='dateauthRFC',
            field=models.DateField(null=True),
        ),
    ]
