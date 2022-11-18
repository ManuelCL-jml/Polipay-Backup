from django.db import models
import datetime as dt

from rest_framework.settings import api_settings

from apps.paycash.manager import ManagerPayCashReference
from apps.users.models import cuenta
from apps.suppliers.models import cat_supplier
from apps.transaction.models import Status


class PayCashTypeReference(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    type_reference = models.CharField(max_length=50, null=False)
    description = models.CharField(max_length=150)


class PayCashReference(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    amount = models.FloatField(null=False)
    value = models.CharField(max_length=40, null=False)
    expiration_date = models.DateTimeField(null=False)
    reference_number = models.CharField(max_length=16, null=True)
    payment_concept = models.CharField(max_length=100, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_cancel = models.DateTimeField(auto_now=True)
    date_modify = models.DateTimeField(default=None)
    comission_pay = models.FloatField(null=True)
    type_reference = models.ForeignKey(PayCashTypeReference, on_delete=models.DO_NOTHING, null=True)
    persona_cuenta = models.ForeignKey(cuenta, on_delete=models.DO_NOTHING, null=True)
    supplier = models.ForeignKey(cat_supplier, on_delete=models.DO_NOTHING, null=True)
    status_reference = models.ForeignKey(Status, on_delete=models.DO_NOTHING, default=3)
    barcode = models.FileField(upload_to='PayCashBarCode', default="No se cargo el documento")
    objects = ManagerPayCashReference()

    @property
    def get_url_aws_document(self) -> str:
        value = getattr(self, 'barcode', api_settings.UPLOADED_FILES_USE_URL)
        return value.url


class PayCashRegistraNotificacionPago(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    folio = models.IntegerField()
    resultado = models.IntegerField()
    tipo = models.IntegerField()
    emisor = models.IntegerField()
    secuencia = models.IntegerField()
    monto = models.FloatField()
    fecha = models.CharField(max_length=20)
    hora = models.CharField(max_length=20)
    autorizacion = models.CharField(max_length=20)
    referencia = models.CharField(max_length=40)
    value = models.CharField(max_length=40)
    fecha_creacion = models.DateTimeField()
    fecha_confirmacion = models.DateTimeField()
    fecha_vencimiento = models.DateTimeField()
    date_created = models.DateTimeField(auto_now_add=True)
    reference = models.ForeignKey(PayCashReference, on_delete=models.DO_NOTHING, null=True)
