from django.db import models


# Create your models here.

class Tipos(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nombreT = models.CharField(max_length=20, blank=False, null=False)
    descripcion = models.CharField(max_length=255, blank=True, null=True)

class Gadgets(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    idgadget = models.CharField(max_length=24, null=False, unique=True)
    alias = models.CharField(max_length=70, blank=True, null=True)
    monto = models.FloatField(null=False, blank=False, default=0)
    tGadget = models.ForeignKey(Tipos, on_delete=models.DO_NOTHING, null=False, blank=False, default=1)

