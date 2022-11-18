# Generated by Django 3.2.8 on 2022-01-26 13:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0049_persona_token_device_app_token'),
    ]

    operations = [
        migrations.CreateModel(
            name='Access_credentials',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('credentials_type', models.BooleanField(default=False)),
                ('credential_access', models.TextField()),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('credential_app', models.CharField(choices=[('M', 'Aplicacion movil'), ('W', 'Aplicacion web')], default='M', max_length=1)),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]