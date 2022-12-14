# Generated by Django 3.1.2 on 2022-01-17 15:15

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Cat_type_token',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(default=None, max_length=30, null=True)),
                ('description', models.CharField(default=None, max_length=254, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='User_token',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('token', models.CharField(default=None, max_length=50, null=True)),
                ('json_content', models.TextField()),
                ('is_active', models.BooleanField(default=False)),
                ('effective_date', models.DateTimeField()),
                ('person_id', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
                ('token_related', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='api_dynamic_token.cat_type_token')),
            ],
        ),
        migrations.CreateModel(
            name='Token_detail',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('time_config', models.IntegerField(default=3)),
                ('person_id', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
