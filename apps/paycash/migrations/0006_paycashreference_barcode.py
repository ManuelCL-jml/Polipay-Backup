# Generated by Django 3.1.2 on 2022-06-24 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paycash', '0005_paycashreference_date_modify'),
    ]

    operations = [
        migrations.AddField(
            model_name='paycashreference',
            name='barcode',
            field=models.FileField(default='No se cargo el documento', upload_to='PayCashBarCode'),
        ),
    ]