from itertools import chain
from typing import List

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from apps import permision
from apps.logspolipay.manager import RegisterLog
from apps.transaction import messages
from operator import itemgetter
import mimetypes

from django.http.response import FileResponse
from django.db import transaction
from django.db.models.query import QuerySet

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status

from apps.permision.permisions import BlocklistPermissionV2
from apps.transaction.api.web.views.views_listar_movimientos import ListIngresos, ListEgresos
from apps.users.api.web.serializers.cliente_externo_serializer import *
from apps.users.management import get_Object_orList_error, filter_data_or_return_none
from apps.users.models import *
from apps.transaction.models import *


# Endpoint: users/web/v2/personal-externo/?CuentaEjeId=1077
class PersontaExterna(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear personal externo por grupo",
                "Editar personal externo por grupo",
                "Eliminar personal externo por grupo",
                "Crear personal externo por centro de costo",
                "Editar personal externo por centro de costo",
                "Eliminar personal externo por centro de costo"]
    serializer_class = SerializerPersonalExternoIn

    def create(self, request):
        log = RegisterLog(request.user, request)
        file = request.data["documento"]
        pk_user_filter = request.query_params["CuentaEjeId"]
        if pk_user_filter:
            log.json_request(request.data)
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid(raise_exception=True):
                num_cuenta, instance = serializer.create_personalExterno(file, pk_user_filter)
                succ = {"status": {"mensaje": "Se creo personal externo", "id": instance.id, "Su cuenta es:": str(num_cuenta)}}
                log.json_response(succ)
                return Response(succ, status=status.HTTP_200_OK)
        else:
            err = {"status": "Cuenta Eje no encontrada"}
            return Response(err, status=status.HTTP_200_OK)

    def put(self, request):
        log = RegisterLog(request.user, request)
        instance = get_Object_orList_error(persona, id=self.request.query_params["id"])
        log.json_request(request.data)
        serializer = SerializerEditarPersonalExternoIn(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update_personal_externo(instance)
            succ = {"status": "Se actualizo personal externo"}
            log.json_response(succ)
            return Response(succ, status=status.HTTP_200_OK)

    def delete(self, request):
        log = RegisterLog(request.user, request)
        id = self.request.query_params["id"]
        instance = get_Object_orList_error(persona, id=id)
        queryset = grupoPersona.objects.filter(
            Q(person_id=instance.id, relacion_grupo_id=6) | Q(person_id=instance.id, relacion_grupo_id=7))
        log.json_request(request.data)
        serializer = EliminarPersonaExternaIn(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.Eliminar_persona_externa(instance, queryset)
            succ = {"status": "Persona externa eliminada"}
            log.json_response(succ)
            return Response(succ, status=status.HTTP_200_OK)
        else:
            err = {"status": "Persona externa no encontrada"}
            return Response(err, status=status.HTTP_400_BAD_REQUEST)


class FiltroPersonalExterno(ListAPIView):
    """
    Listado de persona externo con filtro recibe mas
    de un parametro


    """
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Ver personal externo en lista por centro de costo"]
    serializer_class = FilterPersonExtSerializer
    pagination_class = PageNumberPagination

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        size = request.query_params['size']
        self.pagination_class.page_size = size

        date_1 = request.query_params['date_1']
        date_2 = request.query_params['date_2']
        name = request.query_params['name']
        numero_cuenta = request.query_params['numero_cuenta']
        numero_tarjeta: str = request.query_params['numero_tarjetas']
        razon_social_id: str = request.query_params['razon_social_id']

        data = {
            "name": '' if name == 'null' else name,
            "is_active": request.query_params['is_active'],
            "numero_tarjetas": "null" if numero_tarjeta == 'null' else numero_tarjeta,
            "empresa_id": razon_social_id,
            "date_1": datetime.date(2000, 1, 1) if date_1 == 'null' else date_1,
            "date_2": datetime.date.today() if date_2 == 'null' else date_2,
            "numero_cuenta": '' if numero_cuenta == 'null' else numero_cuenta,
        }

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        queryset = serializer.filter_querys()

        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(page)


# Endpoint: users/web/v2/LisPerExt/list/?size=100&state=true&razon_social_id=7506
class ListarPersonalExterno(ListAPIView):
    """
    Listado de personal externo sin filtro, solo recibe como parametro size y state


    """
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Ver personal externo en lista por centro de costo"]
    pagination_class = PageNumberPagination

    def list_person_with_number_cards(self, inquiries: List) -> List:
        list_data = []
        _number_targets: int = 0

        for query in inquiries:
            # (ChrGil 2022-01-07) Se elimina asterisco
            if query["person__last_name"]:
                last_name: str = query.get('person__last_name')
                result = remove_asterisk(last_name)
                query["person__last_name"] = None if result == '' else result

            _number_targets = tarjeta.objects.filter(cuenta__persona_cuenta_id=query['person_id']).count()
            query['number_targets'] = _number_targets
            list_data.append(query)
        return list_data

    # (ChrGil 2021-11-16) Se optimiza y se corrige bug en el listado de personal externo
    def filter_querys(self, company_id: int, state: bool) -> List:
        return grupoPersona.objects.annotate(
            persona=FilteredRelation(
                'person', condition=Q(person__state=state)
            )
        ).filter(
            empresa_id=company_id,
            relacion_grupo_id=6,
            persona__name__icontains='',
        ).values('person_id', 'person__name', 'person__last_name').order_by('-person__date_joined')

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        self.pagination_class.page_size = request.query_params['size']
        state: bool = request.query_params['state'].title()
        company_id: int = request.query_params['razon_social_id']

        inquiries = self.filter_querys(company_id, state)
        list_data = self.list_person_with_number_cards(inquiries)

        page = self.paginate_queryset(list_data)
        return self.get_paginated_response(page)


class DetailPersonaExterna(GenericViewSet):
    """
    Ver detalle de un personal externo
    """
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver detalles del personal externo por centro de costo",
                "Ver detalles del personal externo por grupo"]
    serializer_class = SerializerDetailPersonaExternaOut

    def get_queryset(self, *args, **kwargs):
        return filter_data_or_return_none(*args, **kwargs)

    def list(self, request, *args, **kwargs):
        id = request.query_params['id']
        usuario = persona.objects.get(id=request.query_params["usuario"])
        queryset = grupoPersona.objects.filter(empresa_id=id, relacion_grupo_id=6, person_id=usuario)
        serializer = self.serializer_class(instance=queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MovimientosTarjeta(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver todos los movimientos de una tarjeta de  un personal externo"]

    def list(self, request, *args, **kwargs):
        error = []
        NumeroTarjeta = request.query_params["Tarjeta"]
        FechaDesde = request.query_params["FechaDesde"]
        FechaHasta = request.query_params["FechaHasta"]
        cuenta_eje = request.query_params["CuentaEjeId"]
        tipo_inntec = request.query_params["Tipo"]
        queryset = tarjeta.objects.filter(clientePrincipal_id=cuenta_eje, tarjeta=NumeroTarjeta)
        if queryset:
            queryMovimientosTarjetaInntec = MovimientosTarjetaInntec(NumeroTarjeta, FechaDesde, FechaHasta, tipo_inntec)

            if len(queryMovimientosTarjetaInntec) == 0:
                return Response({"status": "No hay movimientos para mostrar"})

            return Response(queryMovimientosTarjetaInntec, status=status.HTTP_200_OK)
        else:
            error.append({"field": "tarjeta", "data": NumeroTarjeta,
                          "message": "Tarjeta no encontrada en la cuenta eje"})
            MensajeError(error)


class BuscarSaldosTarjetaInntec(ListAPIView):
    permission_classes = ()

    def list(self, request, *args, **kwargs):  # CuentaEje
        error = []
        NumeroTarjeta = request.query_params["Tarjeta"]
        cuenta_eje = request.query_params["CuentaEjeId"]
        tipo_inntec = request.query_params["Tipo"]
        queryset = tarjeta.objects.filter(clientePrincipal_id=cuenta_eje, tarjeta=NumeroTarjeta)
        if queryset:
            querySaldosInntec = None
            if tipo_inntec == "Pruebas":
                querySaldosInntec = SaldoTarjetaInntecPruebas(NumeroTarjeta)
            if tipo_inntec == "Produccion":
                querySaldosInntec = SaldoTarjetaInntec(NumeroTarjeta)
            return Response(querySaldosInntec, status=status.HTTP_200_OK)
        else:
            error.append({"field": "tarjeta", "data": NumeroTarjeta,
                          "message": "Tarjeta no encontrada en la cuenta eje"})
            MensajeError(error)


class MovimientosCuentaView(ListAPIView):
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Ver todos los movimientos de una cuenta de un personal externo"]

    def list(self, request, *args, **kwargs):
        NumeroCuenta = request.query_params["Cuenta"]
        FechaDesde = request.query_params["FechaDesde"]
        FechaHasta = request.query_params["FechaHasta"]
        FechaDesde, FechaHasta = MovimientosCuenta(NumeroCuenta, FechaDesde, FechaHasta)

        queryEgresos: List[Dict] = transferencia.objects.filter(
            cuenta_emisor=NumeroCuenta,
            fecha_creacion__gte=FechaDesde,
            fecha_creacion__lte=FechaHasta
        ).values("id", "concepto_pago", "monto", "fecha_creacion", "transmitter_bank__institucion").order_by(
            "fecha_creacion")

        listEgre = []
        listIng = []

        for query in queryEgresos:
            query["monto"] = "-$" + str(query["monto"])
            query['banco_emisor'] = query.pop('transmitter_bank__institucion')
            listEgre.append(query)

        queryIngresos = transferencia.objects.filter(
            cta_beneficiario=NumeroCuenta,
            fecha_creacion__gte=FechaDesde,
            fecha_creacion__lte=FechaHasta
        ).values("id", "concepto_pago", "monto", "fecha_creacion", "transmitter_bank__institucion").order_by(
            "fecha_creacion")

        for query in queryIngresos:
            query["monto"] = "$" + str(query["monto"])
            query['banco_emisor'] = query.pop('transmitter_bank__institucion')
            listIng.append(query)
        listEgre.extend(listIng)
        lista_ordenada = sorted(listEgre, key=itemgetter('id'), reverse=True)
        return Response({"listado": lista_ordenada}, status=status.HTTP_200_OK)


class DetallesMovimientosCuenta(ListAPIView):
    serializer_class = DetallesMovimientosCuenta

    def list(self, request, *args, **kwargs):
        idTransferencia = self.request.query_params["id"]
        instance = get_Object_orList_error(transferencia, id=idTransferencia)
        serializer = self.serializer_class(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


# (Jose 08/12/2021 Se descarga el archivo excel)

class LayoutPersonalExternoMasivo(GenericViewSet):
    permission_classes = ()

    def list(self, request):
        filename = 'TEMPLATES/web/Personal-Externo-Masivo.xlsx'
        filepath = filename
        path = open(filepath, 'r')
        mime_type, _ = mimetypes.guess_type(filepath)
        response = FileResponse(open(filename, 'rb'))
        response['Content-Disposition'] = "attachment; filename=%s" % filename
        return response


# (Jose 08/12/2021 Se recibe los datos y se crea los beneficiarios)
# colocar email en otro ligar para no demore el codigo
class PersonalExternoMasivo(GenericViewSet):
    permission_classes = ()
    serializer_class = AltaBeneficiarioMasivo

    def create(self, request):
        # a = pruebas()
        instance = GetObjectOrError(persona, id=self.request.query_params["userId"])
        listado_excel = request.data["PersonList"]
        serializer = self.serializer_class(data=request.data)
        pk_user = instance.id
        listado_excel = serializer.validate(listado_excel)
        try:
            with transaction.atomic():
                beneficiarios_id = serializer.create(listado_excel, pk_user)
                mensaje, data, field = "Se crearon beneficiarios", "Null", "Null"
                respuesta = MessageOK(mensaje, data, field)
                # Mejorar el envio de correo
                self.enviar_email(beneficiarios_id)
                return Response(respuesta, status=status.HTTP_200_OK)
        except Exception as e:
            message = "Ocurrio un error durante el proceso de creación de Beneficiarios masivos, Error:   " + str(e)
            error = {'field': '', "data": '', 'message': message}
            MensajeError(error)

    # return Response(a, status=status.HTTP_200_OK)

    def enviar_email(self, beneficiarios_id):
        send_email_beneficario_masivo(beneficiario=beneficiarios_id)
        return True


# (Jose 17/01/2022 ) Crear,editar y eliminar beneficiarios por centro de costos

class beneficiarios_centro_costos(GenericViewSet):
    # permission_classes = (BlocklistPermissionV2,)
    permission_classes = ()
    permisos = ["Crear personal externo por centro de costo", "Editar personal externo por centro de costo",
                "Eliminar personal externo por centro de costo"]
    serializer_class = SerializerPersonalExternoIn

    def create(self, request):
        file = request.data["documento"]
        serializer = self.serializer_class(data=request.data)
        pk_user = request.data["CentroCostoId"]
        if serializer.is_valid(raise_exception=True):
            try:
                with transaction.atomic():
                    num_cuenta, instance = serializer.create_personalExterno(file, pk_user)
                    Lis_dic = [{"field": "Null", "data": "Null", "message": "Se creo beneficiarios"},
                               {"field": "Null", "data": instance.id, "message": "Id del beneficiario"},
                               {"field": "Null", "data": num_cuenta, "message": "Numero de cuenta del beneficiario"}]
                    respuesta = MessageOkList(Lis_dic)
                    return Response(respuesta, status=status.HTTP_200_OK)
            except Exception as e:
                message = "Ocurrio un error durante el proceso de la creación de Beneficiario, Error:   " + str(e)
                error = {'field': '', "data": '', 'message': message}
                MensajeError(error)

    def put(self, request):
        instance = GetObjectOrError(persona, id=self.request.query_params["id"])
        serializer = SerializerEditarPersonalExternoIn(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update_personal_externo(instance)
            mensaje, data, field = "Se actualizo beneficiarios", "Null", "Null"
            respuesta = MessageOK(mensaje, data, field)
            return Response(respuesta, status=status.HTTP_200_OK)

    def delete(self, request):
        instance = GetObjectOrError(persona, id=self.request.query_params["id"])
        queryset = grupoPersona.objects.filter(person_id=instance.id, relacion_grupo_id=6)
        serializer = EliminarPersonaExternaIn(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.Eliminar_persona_externa(instance, queryset)
            return Response({"status": "Persona externa eliminada"}, status=status.HTTP_200_OK)


class ListBeneficiariosCentroCostos(ListAPIView):
    """
    Listado de personal externo sin filtro, solo recibe como parametro size y state


    """
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Ver personal externo en lista por centro de costo"]
    permission_classes = ()
    pagination_class = PageNumberPagination

    @method_decorator(cache_page(60 * 0.1))
    def list_person_with_number_cards(self, inquiries: List) -> List:
        list_data = []
        _number_targets: int = 0

        for query in inquiries:
            if query["person__last_name"]:
                last_name: str = query.get('person__last_name')
                result = remove_asterisk(last_name)
                query["person__last_name"] = None if result == '' else result

            _number_targets = tarjeta.objects.filter(cuenta__persona_cuenta_id=query['person_id']).count()
            query['number_targets'] = _number_targets
            list_data.append(query)
        return list_data

    def filter_querys(self, company_id: int, state: bool) -> List:
        return grupoPersona.objects.annotate(
            persona=FilteredRelation(
                'person', condition=Q(person__state=state)
            )
        ).filter(
            empresa_id=company_id,
            relacion_grupo_id=6,
            persona__name__icontains='',
        ).values('person_id', 'person__name', 'person__last_name').order_by('-person__date_joined')

    def list(self, request, *args, **kwargs):
        self.pagination_class.page_size = request.query_params['size']
        state: bool = request.query_params['state'].title()
        company = GetObjectOrError(persona, id=request.query_params["CentroCostoId"])
        company_id: int = company.id

        inquiries = self.filter_querys(company_id, state)
        list_data = self.list_person_with_number_cards(inquiries)

        page = self.paginate_queryset(list_data)
        return self.get_paginated_response(page)

class FiltroPersonalExternoCentroCosto(ListAPIView):
    """
    Listado de persona externo con filtro recibe mas
    de un parametro
    """
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver personal externo en lista por centro de costo"]
    serializer_class = FilterPersonExtSerializer
    pagination_class = PageNumberPagination

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        size = request.query_params['size']
        self.pagination_class.page_size = size

        date_1 = request.query_params['date_1']
        date_2 = request.query_params['date_2']
        name = request.query_params['name']
        numero_cuenta = request.query_params['numero_cuenta']
        numero_tarjeta: str = request.query_params['numero_tarjetas']

        data = {
            "name": '' if name == 'null' else name,
            "is_active": request.query_params['is_active'],
            "numero_tarjetas": "null" if numero_tarjeta == 'null' else numero_tarjeta,
            "empresa_id": request.query_params["CentroCostoId"],
            "date_1": datetime.date(2000, 1, 1) if date_1 == 'null' else date_1,
            "date_2": datetime.date.today() if date_2 == 'null' else date_2,
            "numero_cuenta": '' if numero_cuenta == 'null' else numero_cuenta,
        }

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        queryset = serializer.filter_querys()

        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(page)
