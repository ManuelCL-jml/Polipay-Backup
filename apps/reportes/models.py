# Modulos nativos
from django.db import models

# Modulos locales
from apps.users.models import cuenta
from .choices import TYPE_REPORT_CHOICE

class Reporte(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    type_report = models.CharField(choices=TYPE_REPORT_CHOICE, default='Robo o Extravio', max_length=100)
    description = models.TextField(max_length=500, null=False, blank=False)

class CatTipoReporte(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nombre = models.CharField(max_length=30, null=False, blank=False)
    description = models.TextField(max_length=500)


class ReporteCuentas(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    cuentaRel = models.ForeignKey(cuenta, on_delete=models.DO_NOTHING)
    fechaReporte = models.DateTimeField(auto_now_add=True)
    nombre_docto = models.CharField(max_length=30)
    ext_docto = models.CharField(max_length=4)
    tipo_reporte = models.ForeignKey(CatTipoReporte, on_delete=models.DO_NOTHING)
    fecha_inicio = models.DateTimeField(null=False, blank=False)
    fecha_fin = models.DateTimeField(null=False, blank=False)
    detalle = models.TextField(null=False, blank=False)