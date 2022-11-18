from django.db import models

from apps.services_pay.manager import ManagerLogEfectiva
from apps.users.models import persona

class Category(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=20)
    icon = models.CharField(max_length=20)

class Transmitter(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    family = models.CharField(max_length=20)
    id_transmitter = models.IntegerField()
    name_transmitter = models.CharField(max_length=45)
    short_name = models.CharField(max_length=45)
    description = models.CharField(max_length=255)
    presence = models.CharField(max_length=20)
    acept_partial_payment = models.BooleanField(default=False)
    max_amount = models.FloatField()
    image = models.FileField(upload_to='transmitters', null=True, blank=True, default=None)
    catRel = models.ForeignKey(Category, on_delete=models.DO_NOTHING, default="1")


class Reference(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=45)


class TransmitterHaveReference(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    description = models.CharField(max_length=255)
    type = models.CharField(max_length=10)
    length = models.IntegerField()
    length_required = models.BooleanField()
    required = models.BooleanField()
    reference = models.ForeignKey(Reference, on_delete=models.CASCADE)
    transmitter = models.ForeignKey(Transmitter, on_delete=models.CASCADE)


class Fee(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    description = models.CharField(max_length=255)
    amount = models.FloatField()
    transmitter = models.ForeignKey(Transmitter, on_delete=models.CASCADE)


class CodeEfectiva(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    code = models.IntegerField()
    message = models.CharField(max_length=100)


class LogEfectiva(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    payment_date = models.DateTimeField(auto_now_add=True)
    folio = models.IntegerField(null=True, blank=True, default=0)
    autorization = models.CharField(max_length=10, null=True, blank=True, default=None)
    ticket = models.CharField(max_length=15)
    correspondent = models.IntegerField()
    transmitterid = models.IntegerField()
    reference_one = models.CharField(max_length=1000, null=True, blank=True, default=None)
    reference_two = models.CharField(max_length=1000, null=True, blank=True, default=None)
    reference_three = models.CharField(max_length=10000, null=True, blank=True, default=None)
    amount = models.IntegerField()
    commission = models.IntegerField()
    charge = models.IntegerField()
    transmitter_rel = models.ForeignKey(Transmitter, on_delete=models.CASCADE)
    code = models.ForeignKey(CodeEfectiva, on_delete=models.CASCADE)
    user_rel = models.ForeignKey(persona, on_delete=models.DO_NOTHING)

    objects = ManagerLogEfectiva()


class TranTypes(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    number = models.IntegerField()
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)


class TransmitterHaveTypes(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    transmitter = models.ForeignKey(Transmitter, on_delete=models.CASCADE)
    type = models.ForeignKey(TranTypes, on_delete=models.CASCADE)



class Frequents(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    user_rel = models.ForeignKey(persona, on_delete=models.DO_NOTHING)
    transmmiter_Rel = models.ForeignKey(Transmitter, on_delete=models.DO_NOTHING)
