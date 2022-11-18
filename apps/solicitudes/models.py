from django.db import models

from apps.solicitudes.manager import ManagerSolicitudes, ManagerEdoSolicitud, ManagerTipoSolicitud
# from apps.solicitudes.management import SolicitudesManager
from apps.users.models import persona


class TipoSolicitud(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nombreSol = models.CharField(max_length=30)
    descripcionSol = models.CharField(max_length=254)
    objects = ManagerTipoSolicitud()

    def get_tipo_solicitud(self):
        return self.nombreSol


class EdoSolicitud(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nombreEdo = models.CharField(max_length=30)
    descripcion = models.TextField(max_length=255, default=None)
    objects = ManagerEdoSolicitud()

    def get_estado_solicitud(self):
        return self.nombreEdo


class Solicitudes(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=254)
    tipoSolicitud = models.ForeignKey(TipoSolicitud, on_delete=models.DO_NOTHING, null=False, blank=False)
    personaSolicitud = models.ForeignKey(persona, on_delete=models.DO_NOTHING, null=False, blank=False,
                                         related_name="persona_solicita")
    fechaSolicitud = models.DateTimeField(auto_now_add=True)
    estado = models.ForeignKey(EdoSolicitud, on_delete=models.DO_NOTHING, null=False, blank=False)
    intentos = models.IntegerField(null=True)
    monto_req_min = models.FloatField(null=True, blank=True)
    monto_total = models.FloatField(null=True, blank=True)
    dato_json = models.TextField(max_length=None, null=True)
    referencia = models.CharField(max_length=30, blank=True)
    fechaChange = models.DateTimeField(default=None, null=True)
    personChange = models.ForeignKey(persona, on_delete=models.DO_NOTHING, null=True,
                                     related_name="persona_autorizacion")

    objects = ManagerSolicitudes()

    def get_solicitudes(self):
        return {
            "id": self.id,
            "tipo_solicitud": self.tipoSolicitud.get_tipo_solicitud(),
            "estado": self.estado.get_estado_solicitud(),
            "intentos": self.intentos
        }

    def get_solicitudes_CE(self):
        return {
            "id": self.id,
            "fecha": self.fechaSolicitud,
            "tipo_solicitud": self.tipoSolicitud.get_tipo_solicitud(),
            "monto": self.monto_req_min,
            "estado": self.estado.get_estado_solicitud(),
            "monto_total": self.monto_total
        }

    def get_solicitud_id(self):
        return self.id

    def get_solicitud_transfer(self):
        return {
            "id": self.id,
            "nombre": self.personaSolicitud.get_name_company(),
            "referencia": self.referencia,
            "monto_total": self.monto_total,
            "monto_req_min": self.monto_req_min,
            "fecha_solicitud": self.fechaSolicitud

        }
    def get_name_persona_solicitud(self):
        return {
            "nombre": self.personaSolicitud.get_name_company()
        }


class Detalle_solicitud(models.Model):  # tabla para guardar el historial detallado de las solicitudes
    id = models.AutoField(primary_key=True)
    sol_rel = models.ForeignKey(Solicitudes, on_delete=models.DO_NOTHING, null=False, blank=False)
    fechaReg = models.DateTimeField(auto_now_add=True)
    fechaEntrega = models.DateField()
    fechaEntregaNew = models.DateTimeField()
    detalle = models.TextField()
    edodetail = models.ForeignKey(EdoSolicitud, on_delete=models.DO_NOTHING, null=False, blank=False)

    def get_edodetail(self):
        return {
            'edodetail': self.edodetail,
            'fechaEntregaNew': self.fechaEntregaNew
        }
