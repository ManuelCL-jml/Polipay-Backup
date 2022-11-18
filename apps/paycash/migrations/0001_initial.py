# Generated by Django 3.1.2 on 2022-06-20 12:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('transaction', '0019_auto_20220509_1222'),
        ('users', '0061_auto_20220617_1031'),
        ('suppliers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PayCashTypeReference',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, unique=True)),
                ('type_reference', models.CharField(max_length=50)),
                ('description', models.CharField(max_length=150)),
            ],
        ),
        migrations.CreateModel(
            name='PayCashReference',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, unique=True)),
                ('amount', models.FloatField()),
                ('value', models.CharField(max_length=40)),
                ('expiration_date', models.DateTimeField()),
                ('reference_number', models.CharField(max_length=16, null=True)),
                ('payment_concept', models.CharField(max_length=100, null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_cancel', models.DateTimeField(auto_now=True)),
                ('persona_cuenta', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='users.cuenta')),
                ('status_reference', models.ForeignKey(default=3, on_delete=django.db.models.deletion.DO_NOTHING, to='transaction.status')),
                ('supplier', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='suppliers.cat_supplier')),
                ('type_reference', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='paycash.paycashtypereference')),
            ],
        ),
        migrations.CreateModel(
            name='PayCashPagos',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, unique=True)),
                ('payment_id', models.CharField(max_length=20)),
                ('type', models.IntegerField()),
                ('sender_id', models.IntegerField()),
                ('amount', models.FloatField()),
                ('commission', models.FloatField()),
                ('date', models.DateField()),
                ('hour', models.TimeField()),
                ('authorization', models.IntegerField()),
                ('reference_number', models.IntegerField()),
                ('status', models.IntegerField()),
                ('ref_value', models.CharField(max_length=40)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('reference', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='paycash.paycashreference')),
            ],
        ),
    ]
