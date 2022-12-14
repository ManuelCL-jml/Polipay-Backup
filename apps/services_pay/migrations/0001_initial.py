# Generated by Django 3.2.8 on 2022-02-11 13:25

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
            name='CodeEfectiva',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('code', models.IntegerField()),
                ('message', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Reference',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=45)),
            ],
        ),
        migrations.CreateModel(
            name='Transmitter',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('family', models.CharField(max_length=20)),
                ('id_transmitter', models.IntegerField()),
                ('name_transmitter', models.CharField(max_length=45)),
                ('short_name', models.CharField(max_length=20)),
                ('description', models.CharField(max_length=255)),
                ('presence', models.CharField(max_length=20)),
                ('acept_partial_payment', models.BooleanField(default=False)),
                ('max_amount', models.FloatField()),
                ('image', models.FileField(blank=True, default=None, null=True, upload_to='transmitters')),
            ],
        ),
        migrations.CreateModel(
            name='TranTypes',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('number', models.IntegerField()),
                ('name', models.CharField(max_length=255)),
                ('description', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='TransmitterHaveTypes',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('transmitter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services_pay.transmitter')),
                ('type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services_pay.trantypes')),
            ],
        ),
        migrations.CreateModel(
            name='TransmitterHaveReference',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=255)),
                ('type', models.CharField(max_length=10)),
                ('length', models.IntegerField()),
                ('length_required', models.BooleanField()),
                ('required', models.BooleanField()),
                ('reference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services_pay.reference')),
                ('transmitter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services_pay.transmitter')),
            ],
        ),
        migrations.CreateModel(
            name='LogEfectiva',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('payment_date', models.DateTimeField(auto_now_add=True)),
                ('folio', models.IntegerField(blank=True, default=0, null=True)),
                ('autorization', models.CharField(blank=True, default=None, max_length=10, null=True)),
                ('ticket', models.CharField(max_length=15)),
                ('correspondent', models.IntegerField()),
                ('transmitterid', models.IntegerField()),
                ('reference_one', models.CharField(blank=True, default=None, max_length=1000, null=True)),
                ('reference_two', models.CharField(blank=True, default=None, max_length=1000, null=True)),
                ('reference_three', models.CharField(blank=True, default=None, max_length=10000, null=True)),
                ('amount', models.IntegerField()),
                ('commission', models.IntegerField()),
                ('charge', models.IntegerField()),
                ('code', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services_pay.codeefectiva')),
                ('transmitter_rel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services_pay.transmitter')),
                ('user_rel', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Fee',
            fields=[
                ('id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=255)),
                ('amount', models.FloatField()),
                ('transmitter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services_pay.transmitter')),
            ],
        ),
    ]
