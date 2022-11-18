import datetime
from django.db import models
from typing import List, Any, Dict
from django.db.models import Q


class ManagerSolicitudes(models.Manager):
    def create_solicitud(self, **kwargs):
        self.model(
            nombre=kwargs.get('description', ''),
            personaSolicitud_id=kwargs.get('person_id'),
            dato_json=kwargs.get('extra_data'),
            intentos=1,
            tipoSolicitud_id=kwargs.get('tipo_solicitud', 1),
            estado_id=kwargs.get('status_id', 1),
            fechaChange=datetime.datetime.now()
        ).save(using=self._db)

    def filter_request_cost_center(self, estado: str, list_cost_center_id: List[int], date1, date2):
        if estado == 'null':
            estado = ''
        if date1 == 'null':
            date1 = datetime.datetime.now() - datetime.timedelta(days=91)
            print(date1)
        if date2 == 'null':
            date2 = datetime.datetime.now()

        return (
            super()
                .get_queryset()
                .select_related('personaSolicitud')
                .filter(
                Q(estado_id=1) | Q(estado_id=2) | Q(estado_id=4)
            )
                .filter(
                personaSolicitud_id__in=list_cost_center_id,
                tipoSolicitud_id=1,
                fechaSolicitud__range=(date1, date2),
                estado__nombreEdo__icontains=estado
            )
                .values('personaSolicitud_id', 'personaSolicitud__name', 'fechaSolicitud', 'estado__nombreEdo')
                .order_by('-fechaSolicitud')
        )

    # (ManuelCalixtro 20/01/2022) Metodo para filtrar las solicitudes de tarjetas de todos los centros de costos de una cuenta eje
    def filter_request_cards_all_cost_center(self, centro_costos: str, list_cost_centers_id: List[int], date1, date2):
        if centro_costos == 'null':
            centro_costos = ''
        if date1 == 'null':
            date1 = datetime.datetime.now() - datetime.timedelta(days=91)
            print(date1)
        if date2 == 'null':
            date2 = datetime.datetime.now()

        return (
            super()
                .get_queryset()
                .select_related('personaSolicitud')
                .filter(
                personaSolicitud_id__in=list_cost_centers_id,
                tipoSolicitud_id=9,
                fechaSolicitud__range=(date1, date2),
                personaSolicitud__name__icontains=centro_costos,
                estado_id__in=[1,10,11]
            )
                .values('id',
                        'personaSolicitud_id',
                        'fechaSolicitud',
                        'personaSolicitud__name',
                        'estado_id',
                        'estado__nombreEdo',
                        'dato_json')
                .order_by('-fechaSolicitud')
        )

    # (ManuelCalixtro 21/01/2022) Metodo para filtrar las solicitudes de tarjetas de un centro de costos
    def filter_request_cards_cost_center(self, cost_center_id: int, estado: str, date1, date2):
        if estado == 'null':
            estado = ''
        if date1 == 'null':
            date1 = datetime.datetime.now() - datetime.timedelta(days=91)
        if date2 == 'null':
            date2 = datetime.datetime.now()

        return (
            super()
                .get_queryset()
                .select_related('personaSolicitud')
                .filter(
                Q(estado_id=1) | Q(estado_id=11)
            )
                .filter(
                personaSolicitud_id=cost_center_id,
                tipoSolicitud_id=9,
                estado__nombreEdo__icontains=estado,
                fechaSolicitud__range=(date1, date2),
            )
                .values('id', 'personaSolicitud_id', 'fechaSolicitud', 'estado__nombreEdo', 'dato_json')
                .order_by('-fechaSolicitud')
        )

    # (AAboytes 2021-11-25) listar todas las solicitudes del centro de costos, pendientes y devueltas
    def get_admin_(self):
        return (
            super()
                .get_queryset()
                .filter(
                tipoSolicitud_id=1
            )
                .filter(
                Q(estado_id=1) | Q(estado_id=2)
            )
                .values(
                'id',
                'personaSolicitud_id',
                'tipoSolicitud__nombreSol',
                'fechaSolicitud',
                'intentos',
                'estado__nombreEdo'
            )
        )

    # (AAboytes 2021-11-25)
    def get_Sol(self, idSol: int):
        return (
            super()
                .get_queryset()
                .filter(
                id=idSol
            )
                .values(
                'id',
                'personaSolicitud_id',
                'tipoSolicitud__nombreSol',
                'fechaSolicitud',
                'intentos',
                'estado__nombreEdo',
                'estado_id',
                'referencia'
            )
        )

    def filter_request_extern_client(self, list_cost_center_id: List[int]) -> List[Dict[str, Any]]:
        return (
            super()
                .get_queryset()
                .select_related('persona_cuenta')
                .filter(
                personaSolicitud_id__in=list_cost_center_id,
                tipoSolicitud_id__in=[1, 22]
            ).filter(
                Q(estado_id=1) |
                Q(estado_id=2))
            ) .values('id',
                      'intentos',
                      'personaSolicitud_id',
                      'personaSolicitud__name',
                      'personaSolicitud__tipo_persona_id',
                      'estado_id',
                      'referencia',
                      'tipoSolicitud__nombreSol',
                      'dato_json',
                      'fechaSolicitud').order_by('-fechaSolicitud')


class ManagerTipoSolicitud(models.Manager):
    def get_all(self):
        return (
            super()
            .get_queryset()
            .all()
            .values(
                'id',
                'nombreSol',
                'descripcionSol'
            )
        )


class ManagerEdoSolicitud(models.Manager):
    def get_all(self):
        return (
            super()
            .get_queryset()
            .all()
            .values(
                'id',
                'nombreEdo',
                'descripcion'
            )
        )







