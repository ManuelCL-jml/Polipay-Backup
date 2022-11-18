import datetime
from typing import List, Dict, Optional

from django.db.models import FilteredRelation, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.viewsets import GenericViewSet
from rest_framework.generics import ListAPIView, DestroyAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from polipaynewConfig.exceptions import satus_ok
from apps.users.management import get_id_cuenta_eje, get_person_and_empresa
from apps.users.models import grupoPersona, persona, cuenta
from apps.users.api.web.cliente.serializers.serializer_grupo_persona import SerializerGrupoPersona, \
    SerializerEditGrupoPersona


class ListGrupoPersona(ListAPIView):
    """
    Listar grupo de personal externo
    """

    pagination_class = PageNumberPagination

    def queryset(self, cuenta_eje: int, nombre_grupo: str, date_1, date_2) -> List:
        """
        Filtrado y listado de un grupo de personal externo
        """
        return grupoPersona.objects.values(
            'id',
            'nombre_grupo',
            'fechacreacion',
        ).filter(
            Q(fechacreacion__date__gte=date_1) & Q(fechacreacion__date__lte=date_2)
        ).filter(
            empresa_id=cuenta_eje,
            relacion_grupo_id=7,
            is_admin=True,
            nombre_grupo__icontains=nombre_grupo,
        ).order_by('-fechacreacion')

    def add_numero_persona(self, querys: List, cuenta_eje: int) -> List:
        """
        Agregar numero de personas en grupo persona
        """
        for query in querys:
            numero_persona = grupoPersona.objects.filter(
                empresa_id=cuenta_eje,
                relacion_grupo_id=7,
                nombre_grupo=query['nombre_grupo'],
                is_admin=False,
            ).count()
            query['numero_persona'] = numero_persona

        return querys

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        self.pagination_class.page_size = request.query_params['size']
        cuenta_eje = self.request.query_params['company_id']
        nombre_grupo = request.query_params['nombre_grupo']
        date_1 = request.query_params['date_1']
        date_2 = request.query_params['date_2']
        log.json_request(request.query_params)

        if date_1 == 'null':
            date_1 = datetime.datetime(2000, 12, 31, 00, 00, 00)

        if date_2 == 'null':
            date_2 = datetime.datetime.now()

        if nombre_grupo == 'null':
            nombre_grupo = ''

        queryset = self.queryset(cuenta_eje, nombre_grupo, date_1, date_2)
        list_data = self.add_numero_persona(queryset, cuenta_eje)

        for i in list_data:
            log.json_response(i)

        page = self.paginate_queryset(list_data)
        return self.get_paginated_response(page)


# Endpoint: users/web/cliente/v2/SeaPerExt/list/?razon_social_id=1077
# (ChrGil 2022-02-16) Listar o buscar personal externo
class SearchPersonalExterno(ListAPIView):
    """
    Buscar personal externo
    """

    # def queryset(self, nombre_personal_externo: str, cuenta_eje: int) -> List:
    #     return grupoPersona.objects.annotate(
    #         filter_persona=FilteredRelation(
    #             "person", condition=Q(person__state=True),
    #         )
    #     ).filter(
    #         filter_persona__name__icontains=nombre_personal_externo,
    #         empresa_id=cuenta_eje,
    #         relacion_grupo_id=6
    #     ).values('person_id', 'person__name', 'person__last_name', 'person__email', 'nombre_grupo')

    def queryset(self, nombre_personal_externo: str, cuenta_eje: int) -> List:
        return grupoPersona.objects.annotate(
            filter_persona=FilteredRelation(
                "person", condition=Q(person__state=True),
            )
        ).filter(
            empresa_id=cuenta_eje,
            relacion_grupo_id=6
        ).values('person_id', 'person__name', 'person__last_name', 'person__email', 'nombre_grupo')

    def set_cuenta(self, queryset: List) -> List:
        list_data: List = []
        for query in queryset:
            cuentas = cuenta.objects.filter(persona_cuenta_id=query['person_id']).values('cuenta')
            if cuentas:
                query['cuenta'] = cuentas
                list_data.append(query)

        return list_data

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        razon_social_id: int = self.request.query_params['razon_social_id']
        nombre_personal_externo: str = request.query_params['nombre_personal_externo']
        log.json_request(request.query_params)

        queryset = self.queryset(nombre_personal_externo, razon_social_id)

        for query in queryset:
            log.json_response(query)

        list_data = self.set_cuenta(queryset)
        return Response(list_data, status=status.HTTP_200_OK)


class GrupoPersonalExterno(GenericViewSet):
    """
    Crear grupo de personal externo
    """
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear grupo de personal externo"]
    serializer_class: Optional = SerializerGrupoPersona

    def create_grupo_persona(self, list_data: List, serializer) -> bool:
        for data in list_data:
            serializer.create(data)
        return True

    def validate_data(self, lista_personal_externo: List, context: Dict) -> bool:
        list_data: List = []
        serializer: Optional = None
        for index in lista_personal_externo:
            serializer = self.serializer_class(data=index, context=context)
            serializer.is_valid(raise_exception=True)
            list_data.append(serializer.data)

        return self.create_grupo_persona(list_data, serializer)

    def create(self, request):
        log = RegisterLog(request.user, request)
        admin_cuenta_eje: int = request.user.get_only_id()
        cuenta_eje = self.request.query_params['company_id']
        lista_personal_externo: List = request.data['personal_externo']
        log.json_request(request.data)

        context = {
            "empresa_id": cuenta_eje,
            "is_admin": cuenta_eje,
            "nombre_grupo": request.data.pop('nombre_grupo'),
            "longitud_lista_personal_externo": len(lista_personal_externo),
            'person_id': admin_cuenta_eje,
        }

        lista_personal_externo.append({'person_id': admin_cuenta_eje})
        self.validate_data(lista_personal_externo, context)

        data: Dict = satus_ok("Tu operación se realizo de manera satisfactoria", 201)
        log.json_response(data)
        return Response(data, status=status.HTTP_201_CREATED)


class DeleteGrupoPersona(DestroyAPIView):
    """
    Eliminar grupo de personas (Esta pendiente la validación de la dispersión)
    """
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Eliminar grupo de personal externo"]

    def delete_group(self, nombre_grupo: str, cuenta_eje: int) -> bool:
        grupoPersona.objects.filter(
            nombre_grupo=nombre_grupo,
            empresa_id=cuenta_eje,
            relacion_grupo_id=7
        ).delete()

        return True

    def destroy(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        cuenta_eje = self.request.query_params['company_id']
        nombre_grupo = request.query_params['nombre_grupo']
        log.json_request(request.query_params)
        self.delete_group(nombre_grupo, cuenta_eje)

        data: Dict = satus_ok("Se ha eliminado el grupo satisfactoriamente.", 200)
        log.json_response(data)
        return Response(data, status=status.HTTP_200_OK)


class EditGrupoPersona(UpdateAPIView):
    """
    Editar grupo persona, se puede agregar nuevas personas o eliminar
    (Queda pendiente la validacion de as dispersiones)
    """
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Editar grupo de personal externo"]

    serializer_class = SerializerEditGrupoPersona

    def editar_grupo_persona(self, cuenta_eje: int, nombre_grupo: str, list_grupo_persona: List) -> bool:
        context = {'nombre_grupo': nombre_grupo, 'empresa_id': cuenta_eje}

        for index in list_grupo_persona:
            if index['method'] == "new":
                serializer = self.serializer_class(data=index, context=context)
                serializer.is_valid(raise_exception=True)
                serializer.create(serializer.data)

            if index['method'] == "delete":
                self.delete_person_group(nombre_grupo, cuenta_eje, index['person_id'])

        return True

    def delete_person_group(self, nombre_grupo: str, cuenta_eje: int, person_id: int) -> bool:
        grupo_persona = grupoPersona.objects.get(
            person_id=person_id,
            nombre_grupo=nombre_grupo,
            empresa_id=cuenta_eje,
            relacion_grupo_id=7
        )

        grupo_persona.delete()
        return True

    def update(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        cuenta_eje = self.request.query_params['company_id']
        nombre_grupo = request.data[0]['nombre_grupo']
        list_grupo_persona = request.data[0]['personal_externo']
        log.json_request(request.data)

        self.editar_grupo_persona(cuenta_eje, nombre_grupo, list_grupo_persona)
        data: Dict = satus_ok("Tu operación se realizo de manera satisfactoria", 200)
        log.json_response(data)
        return Response(data, status=status.HTTP_200_OK)


class DetailGrupoPersona(ListAPIView):
    """ Mostrar todos los mienbros del grupo persona """

    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver al personal externo de un grupo"]

    def set_cuenta(self, queryset: List) -> List:
        list_data: List = []
        for query in queryset:
            cuentas = cuenta.objects.filter(persona_cuenta_id=query['person_id']).values('cuenta')

            if cuentas:
                query['cuenta'] = cuentas
                list_data.append(query)

        return list_data

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        cuenta_eje = self.request.query_params['company_id']
        nombre_grupo = request.query_params['nombre_grupo']
        log.json_request(request.query_params)

        queryset = grupoPersona.objects.values(
            'person_id',
            'person__name',
            'person__last_name',
            'person__email',
        ).filter(empresa_id=cuenta_eje, nombre_grupo=nombre_grupo, relacion_grupo_id=7, is_admin=False, person__state=True)

        list_data = self.set_cuenta(queryset)
        succ = {"nombre_grupo": nombre_grupo, "data": list_data}
        log.json_response(succ)
        return Response(succ, status=status.HTTP_200_OK)


class SelectGrupoPersona(ListAPIView):
    """
    |Listar nombre de grupo persona
    """
    permission_classes = ()

    def query(self, company_id: int) -> List:
        return grupoPersona.objects.values(
            'nombre_grupo'
        ).filter(empresa_id=company_id, relacion_grupo_id=7, is_admin=True)

    def list(self, request, *args, **kwargs):
        cuenta_eje = self.request.query_params['company_id']
        queryset = self.query(cuenta_eje)
        return Response(queryset, status=status.HTTP_200_OK)