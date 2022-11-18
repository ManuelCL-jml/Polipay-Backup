from django.db import models

from apps.commissions.manager import ManagerComission, ManagerCommissionDetail, ManagerCatCommission
from apps.transaction.models import transferencia
from apps.users.models import persona
from apps.productos.models import producto, rel_prod_serv


class Cat_commission_apply(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    type = models.CharField(max_length=23)
    description = models.CharField(max_length=100)


class Cat_commission_status(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    type = models.CharField(max_length=23)
    description = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)


class Cat_commission_type(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    type = models.CharField(max_length=25)
    description = models.TextField(max_length=100)
    creation_date = models.DateTimeField(auto_now_add=True)


class Cat_commission(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    # producto = models.ForeignKey(producto, on_delete=models.DO_NOTHING, default=1)
    percent = models.DecimalField(max_digits=11, decimal_places=4)
    amount = models.DecimalField(max_digits=11, decimal_places=4)
    description = models.CharField(max_length=150)
    creation_date = models.DateTimeField(auto_now_add=True)
    # total_payment_date = models.DateTimeField(default=None, null=True)
    type = models.ForeignKey(Cat_commission_type, on_delete=models.DO_NOTHING)
    # status = models.ForeignKey(Cat_commission_status, on_delete=models.DO_NOTHING)
    application = models.ForeignKey(Cat_commission_apply, on_delete=models.DO_NOTHING)
    is_active = models.BooleanField(default=True)
    servicio = models.ForeignKey(rel_prod_serv, on_delete=models.DO_NOTHING)

    objects = ManagerCatCommission()


class Commission(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    person_payer = models.ForeignKey(persona, on_delete=models.DO_NOTHING, related_name="pago_secundario")
    person_debtor = models.ForeignKey(persona, on_delete=models.DO_NOTHING, related_name="pago_primario")
    commission_rel = models.ForeignKey(Cat_commission, on_delete=models.DO_NOTHING)
    is_active = models.BooleanField(default=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    total_payment_date = models.DateTimeField(default=None, null=True)
    # # status = models.ForeignKey(Cat_commission_status, on_delete=models.DO_NOTHING)

    objects = ManagerComission()


class Commission_detail(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    commission = models.ForeignKey(Commission, on_delete=models.DO_NOTHING)
    transaction_rel = models.ForeignKey(transferencia, on_delete=models.DO_NOTHING, default=None, null=True, related_name="transaccion_original")
    commission_record = models.ForeignKey(transferencia, on_delete=models.DO_NOTHING, default=None, null=True, related_name="transaccion_comision_cobrada")
    mount = models.DecimalField(max_digits=11, decimal_places=4)
    payment_date = models.DateField(default=None, null=True)
    status = models.ForeignKey(Cat_commission_status, on_delete=models.DO_NOTHING, default=2)

    objects = ManagerCommissionDetail()