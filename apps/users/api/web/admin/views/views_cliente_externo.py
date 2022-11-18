from typing import Any, Dict, ClassVar, Union, List, NoReturn
import json
from operator import itemgetter
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.generics import UpdateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework import pagination, status, viewsets, permissions
from rest_framework.pagination import PageNumberPagination

from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from MANAGEMENT.Utils.utils import random_password, get_values_list
from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from apps.solicitudes.management import ValidaSolicitud, AceptarSolicitud, DevolverSolicitud
from apps.solicitudes.message import message_email
from apps.transaction.models import transferencia
from apps.users.management import ext_client, sol_ext_client, ActivaCuenta, get_Object_orList_error, \
    get_Object_orList_err, MessageOkList, MovimientosTarjetaInntec, MovimientosTarjetaInntecClienteExterno, \
    MovimientosCuenta, MovimientosCuentaClienteExternoFisico
from apps.users.api.web.admin.serializers.serializer_cliente_externo import *
from apps.users.api.web.admin.serializers.serializer_centro_costo import DocumentsUpdate
from apps.users.api.web.admin.serializers.serializer_cliente_externo import SerializerAuthorizeCE, \
    SerializerNotificacionCE
from apps.users.models import documentos, persona, cuenta, grupoPersona

# (AAF 2021-12-15) se añade id persona autorizacion al autorizar documentos
from polipaynewConfig.inntec import get_actual_state


class AutorizarClienteExterno(GenericViewSet):
    serializer_class = SerializerAuthorizeCE
    serializer_class_update = DocumentsUpdate

    def create(self, request):
        log = RegisterLog(request.user, request)
        try:
            with atomic():
                log.json_request(request.data)
                data = request.data
                listaResponse = []
                flag = {}
                listaFlag = []
                sol = ValidaSolicitud(data[0]['idSol'])
                idCentroCostos = data[0]['clienteExternoDetail']['id']
                idauth = data[0]['userAuth']
                # actualizando documentos
                if 'documentos_cliente-externo' in data[0]:
                    for docto in data[0]['documentos_cliente-externo']:
                        serializer = self.serializer_class_update(data=docto)
                        if serializer.is_valid():
                            if docto["status"] != 'C':
                                flag['idDocto'] = docto['id']
                                flag['status'] = docto["status"]
                                listaFlag.append(flag)
                            docto = documentos.objects.get_documento_instance(docto['id'])
                            docto = serializer.update(docto, serializer.validated_data, idauth)
                            listaResponse.append("Documento " + str(docto.id) + " actualizado")
                        else:
                            listaResponse.append("Datos Faltantes para el documento " + str(docto['id']))
                if 'documento_representante' in data[0]:
                    for docto in data[0]['documento_representante']:
                        serializer = self.serializer_class_update(data=docto)
                        if serializer.is_valid():
                            if docto["status"] != 'C':
                                flag['idDocto'] = docto['id']
                                flag['status'] = docto["status"]
                                listaFlag.append(flag)
                            docto = documentos.objects.get_documento_instance(docto['id'])
                            docto = serializer.update(docto, serializer.validated_data, idauth)
                            listaResponse.append("Documento " + str(docto.id) + " actualizado")
                        else:
                            listaResponse.append("Datos Faltantes para el documento " + str(docto['id']))
                # Validamos que la bandera este blanca
                if listaFlag != []:
                    err = MyHttpError(message=listaFlag, real_error="Documentos no Autorizados")
                    log.json_response(err.standard_error_responses())
                    return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
                # activamos cliente externo y aceptamos solicitud
                AceptarSolicitud(data[0]['idSol'])
                objCentro = persona.objects.get(id=idCentroCostos)
                objCentro.state = True
                password = random_password()
                objCentro.set_password(password)
                objCentro.save()
                ActivaCuenta(idCentroCostos)
                message_email(
                    template_name="cliente_externo_fisico_welcome.html",
                    context={"name": objCentro.name,
                             "usuario": objCentro.email,
                             "pass": password},
                    title="Notificacion Colaborador",
                    body="referencia",
                    email=objCentro.email
                )
                # obtenemos clabe de centro
                try:
                    clabe = cuenta.objects.values("cuentaclave").get(persona_cuenta_id=idCentroCostos)
                except:
                    clabe = "SINCLAVE"
                # objtenemos cta eje
                # print(idCentroCostos)
                ctaEje = grupoPersona.objects.filter(person_id=idCentroCostos, relacion_grupo_id__in=[9, 10])
                # obtenemos admins
                admins = grupoPersona.objects.get_list_ids_admin(ctaEje[0].empresa_id)
                # envio mails admins
                for admin in admins:
                    admin = persona.objects.get(id=admin)
                    message_email(
                        template_name="notificacion-cliente-externo.html",
                        context={"Admin": admin.name,
                                 "CentroCostos": data[0]['centroCostoDetail']['name'],
                                 "Estado": "Activado"},
                        title="Notificacion Centro de costos",
                        body="referencia",
                        email=admin.email
                    )
                succ = MyHtppSuccess(message={"clabe": clabe}, extra_data="Tu operación se realizo satisfactoriamente")
                log.json_response(succ.standard_success_responses())
                return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

        except Exception as e:
            err = MyHttpError("Ocurrió un error al autorizar el cliente externo", real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


# (AAF 2021-12-15) enviar notificacion a adminsitradores
class NotificarClienteExterno(GenericViewSet):
    serializer_class = SerializerNotificacionCE
    serializer_class_update = DocumentsUpdate

    def create(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.data)
        data = request.data
        listaResponse = []
        # idCentroCostos = data['idCentroCostos']
        idClienteE = data[0]['clienteExternoDetail']['id']
        idauth = data[0]['userAuth']
        # actualizando documentos
        if 'documentos_cliente-externo' in data[0]:
            for docto in data[0]['documentos_cliente-externo']:
                serializer = self.serializer_class_update(data=docto)
                if serializer.is_valid():
                    docto = documentos.objects.get_documento_instance(docto['id'])
                    docto = serializer.update(docto, serializer.validated_data, idauth)
                    listaResponse.append("Documento " + str(docto.id) + " actualizado")
                else:
                    listaResponse.append("Datos Faltantes para el documento " + str(docto['id']))
        if 'documento_representante' in data[0]:
            for docto in data[0]['documento_representante']:
                serializer = self.serializer_class_update(data=docto)
                if serializer.is_valid():
                    docto = documentos.objects.get_documento_instance(docto['id'])
                    # data = serializer.validated_data
                    docto = serializer.update(docto, serializer.validated_data, idauth)
                    listaResponse.append("Documento " + str(docto.id) + " actualizado")
                else:
                    listaResponse.append("Datos Faltantes para el documento " + str(docto['id']))
        # obtenemos cuenta eje
        ctaCC = grupoPersona.objects.filter(person_id=idClienteE, relacion_grupo_id__in=[9, 10])
        DevolverSolicitud(data[0]['idSol'], ctaCC[0].empresa_id)
        # obtenemos cta eje y admins
        ctaEje = grupoPersona.objects.get_values_empresa(ctaCC[0].empresa_id, 5)
        admins = grupoPersona.objects.get_list_ids_admin(ctaEje[0]["empresa_id"])
        # envio mails
        for admin in admins:
            admin = persona.objects.get(id=admin)
            message_email(
                template_name="devolucion-cliente-externo.html",
                context={"Admin": admin.name,
                         "CentroCostos": data[0]['clienteExternoDetail']['name'],
                         "Estado": "Devuelto"},
                title="Notificacion Cliente Externo",
                body="referencia",
                email=admin.email
            )
        succ = MyHtppSuccess(message="tu operacion se realizo satisfactoriamente", extra_data=listaResponse)
        log.json_response(succ.standard_success_responses())
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


# (ManuelCl 09-03-2022) Listado para clientes externo fisicos
class clienteList_C_E(viewsets.GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver clientes externos"]

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request):
        log = RegisterLog(request.user, request)
        cuenta_eje_id = self.request.query_params['centro_costos_id']
        log.json_request(request.query_params)

        get_cost_centers = grupoPersona.objects.get_list_actives_cost_centers_id(cuenta_eje_id)
        solitudes = grupoPersona.objects.get_list_actives_clientes_externo(get_cost_centers)
        cuentas = cuenta.objects.filter_account_clientes_externos(solitudes)

        page = self.paginate_queryset(cuentas)
        log.json_response(page)
        return self.get_paginated_response(page)


# (ManuelCl 09-03-2022) Listado para clientes externo fisicos
class SolclientList(viewsets.GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver clientes externos"]
    pagination_class = PageNumberPagination

    @staticmethod
    def render_json(**kwargs) -> Dict[str, Any]:
        data = None

        if kwargs.get('dato_json'):
            data = json.loads(kwargs.get('dato_json'))

        return {
            "id": kwargs.get('id'),
            "intentos": kwargs.get('intentos'),
            "personaSolicitud_id": kwargs.get('personaSolicitud_id'),
            "personaSolicitud__name": kwargs.get('personaSolicitud__name'),
            "personaSolicitud__tipo_persona_id": kwargs.get('personaSolicitud__tipo_persona_id'),
            "estado_id": kwargs.get('estado_id'),
            "referencia": kwargs.get('referencia'),
            "tipoSolicitud__nombreSol": kwargs.get('tipoSolicitud__nombreSol'),
            "dato_json": data,
            "fechaSolicitud": kwargs.get('fechaSolicitud'),
        }

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request):
        log = RegisterLog(request.user, request)
        cuenta_eje_id = self.request.query_params['company_id']
        log.json_request(request.query_params)
        get_cost_centers = grupoPersona.objects.get_list_actives_cost_centers_id(cuenta_eje_id)
        solitudes = Solicitudes.objects.filter_request_extern_client(get_cost_centers)

        lista = [self.render_json(**i) for i in solitudes]

        page = self.paginate_queryset(lista)
        log.json_response(page)
        return self.get_paginated_response(page)


class SolDismiss(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Eliminar cliente externo"]

    serializer_class = DismissSoli
    serializer_doct_update = DocumentsUpdate
    serializer_class_get = SolicitudesOut
    pagination_class = PageNumberPagination

    # permission_classes = ()

    def create(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.data)
        sol = ValidaSolicitud(self.request.data['idSol'])
        CEInstance = get_Object_orList_error(persona, id=request.data['idCE'])
        adminInstance = get_Object_orList_error(persona, id=request.data['idPersonaSol'])
        # validar que corresponda a la solicitud
        if sol[0]['personaSolicitud_id'] != CEInstance.id:
            err = MyHttpError(message="Cliente Externo no corresponde con la solicitud", real_error="")
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            data = serializer.update(sol[0], serializer.validated_data)
        else:
            err = MyHttpError(message="Revisar datos enviados", real_error=str(serializer.errors))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        if "documents" in request.data:
            for docto in request.data["documents"]:
                serializer_doc = self.serializer_doct_update(data=docto)
                if serializer_doc.is_valid():
                    doctoInstance = documentos.objects.get_documento_instance(request.data["documents"][0]['id'])
                    serializer_doc.update(doctoInstance, serializer_doc.validated_data, request.data["idPersonaSol"])
        if not request.data['state']:
            # obtenemos admins
            admins = grupoPersona.objects.get_values_empresa(request.data['idCE'], 11)
            # envio mails
            for admin in admins:
                print(admin["empresa_id"])
                admin = persona.objects.get(id=admin["empresa_id"])
                message_email(
                    template_name="devolucion-cliente-externo.html",
                    context={"Admin": admin.name,
                             "CentroCostos": CEInstance.name,
                             "Estado": "Devuelto"},
                    title="Notificacion Cliente externo",
                    body="referencia",
                    email=admin.email
                )
        succ = MyHtppSuccess(message="tu operacion se realizo satisfactoriamente", extra_data=data)
        log.json_response(succ.standard_success_responses())
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

    def list(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.query_params)
        queryset = get_Object_orList_err(persona, id=request.query_params['idCE'])
        page = self.paginate_queryset([queryset])
        serializer = self.serializer_class_get(page, many=True)
        log.json_response(serializer.data)
        return self.get_paginated_response(serializer.data)


class RequestDataVerifyClienteExternoFisico:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_list_documents(self) -> List[Dict[str, Any]]:
        return self._request_data.get('Documents')

    @property
    def get_status_is_correct(self) -> List[str]:
        return [i for i in get_values_list('Status', self.get_list_documents) if i == 'C']


class ComponentVerifyDocumentsClienteExternoFisico:
    _serializer_class: ClassVar[SerializerVerifyDocumentsClienteExterno] = SerializerVerifyDocumentsClienteExterno

    def __init__(self, request_data: RequestDataVerifyClienteExternoFisico, admin: persona):
        self._request_data = request_data
        self._admin = admin.get_only_id()
        self._create()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "user_auth": self._admin
        }

    @staticmethod
    def _data(**kwargs) -> Dict[str, Any]:
        return {
            "document_id": kwargs.get('DocumentId'),
            "status": kwargs.get('Status'),
            "comment": kwargs.get('Comment')
        }

    def _create(self):
        for document in self._request_data.get_list_documents:
            serializer = self._serializer_class(data=self._data(**document), context=self._context)
            serializer.is_valid(raise_exception=True)
            serializer.update()


class ComponentChangeStatusSolicitudClienteExterno:
    _status_devuelto: ClassVar[int] = 2
    _status_autorizada: ClassVar[int] = 4
    _info_cliente: ClassVar[Dict[str, Any]]
    _info_cliente_dom: ClassVar[Dict[str, Any]]

    def __init__(
            self,
            request_data: RequestDataVerifyClienteExternoFisico,
            solicitud_id: int,
            admin: persona,
            cliente_externo_id: int
    ):
        self._request_data = request_data
        self._solicitud_id = solicitud_id
        self._admin = admin
        self._cliente_externo_id = cliente_externo_id
        self._info_cliente = self._get_solicitud_info_cliente
        self._info_cliente_dom = self._get_solicitud_info_cliente_dom
        self._change_status()

    @property
    def _get_solicitud_info_cliente(self) -> Dict[str, Any]:
        data = Solicitudes.objects.filter(id=self._solicitud_id).values('dato_json').first()
        return json.loads(data.get('dato_json'))['person_info']

    @property
    def _get_solicitud_info_cliente_dom(self) -> Dict[str, Any]:
        data = Solicitudes.objects.filter(id=self._solicitud_id).values('dato_json').first()
        return json.loads(data.get('dato_json'))['person_dom']

    #

    def _update(self, status_id: int) -> NoReturn:
        Solicitudes.objects.filter(id=self._solicitud_id).update(
            estado_id=status_id,
            fechaChange=datetime.datetime.now(),
            personChange_id=self._admin.get_only_id()
        )

    def _update_cliente_externo(self, status_id: int) -> NoReturn:
        persona.objects.filter(id=self._cliente_externo_id).update(**self._info_cliente)

    def _update_cliente_externo_domicilio(self, status_id: int) -> NoReturn:
        domicilio.objects.filter(domicilioPersona_id=self._cliente_externo_id).update(**self._info_cliente_dom)

    def _change_status(self):
        if len(self._request_data.get_status_is_correct) == len(self._request_data.get_list_documents):
            self._update(self._status_autorizada)
            self._update_cliente_externo(self._status_autorizada)
            self._update_cliente_externo_domicilio(self._status_autorizada)

        if len(self._request_data.get_status_is_correct) != len(self._request_data.get_list_documents):
            self._update(self._status_devuelto)
            self._update_cliente_externo(self._status_devuelto)
            self._update_cliente_externo_domicilio(self._status_devuelto)


# (ManuelCalixtro) Verifica los documentos de un cliente externo fisico para activarlo o rechazarlo
class VerifyDocumentsClienteExternoFisico(GenericViewSet):

    def create(self, request):
        pass

    def put(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            admin: persona = persona.objects.get(id=6)
            solicitud_id: int = self.request.query_params['solicitud_id']
            cliente_externo_fisico_id: int = self.request.query_params['cliente_externo_fisico_id']
            log.json_request(request.data)

            with atomic():
                request_data = RequestDataVerifyClienteExternoFisico(request.data)
                ComponentVerifyDocumentsClienteExternoFisico(request_data, admin)
                ComponentChangeStatusSolicitudClienteExterno(request_data, solicitud_id, admin,
                                                             cliente_externo_fisico_id)

                success = MyHtppSuccess('Tu operacion se realizo de manera satisfactoria')
                log.json_response(success.standard_success_responses())
                return Response(success.standard_success_responses(), status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            msg = 'Ocurrio un error durante el proceso'
            err = MyHttpError(msg, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)


# (ManuelCalixtro) Asignar tarjetas a un cliente externo fisico
class AsignarTarjetasClienteExterno(UpdateAPIView):
    permission_classes = ()
    serializer_class = SerializerAsignarTarjetaClienteExterno

    def update(self, request, *args, **kwargs):
        try:
            account_number = request.query_params["cuenta"]
            company_id = request.query_params['company']
            cost_center = request.query_params["cost_center_id"]
            type = request.query_params['type']

            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)

            instance_cuenta = cuenta.objects.get(cuenta=account_number)
            serializer.validate_tarjeta(data=request.data["Tarjeta"], company_id=company_id, cost_center_id=cost_center,
                                        account_number=account_number)

            with atomic():
                instance_persona = persona.objects.get(id=instance_cuenta.persona_cuenta_id)
                serializer.update(instance_cuenta, instance_persona, type)
                success = MyHtppSuccess('Tu operacion se realizo de manera satisfactoria')
                return Response(success.standard_success_responses(), status=status.HTTP_200_OK)

        except (ObjectDoesNotExist, IntegrityError, ValueError, KeyError) as e:
            err = MyHttpError(message='Ocurrio un error inesperado al momento de asignar las tarjetas',
                              real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


# (ManuelCalixtro) Lista movimientos de una tarjeta de cliente externo fisico
class MovimientosTarjetaClienteExterno(ListAPIView):
    permission_classes = ()

    @staticmethod
    def render_json(**kwargs) -> Dict[str, Any]:
        name = kwargs.get("persona_cuenta__name")
        last_name = kwargs.get("persona_cuenta__last_name")
        return {
            "id": kwargs.get('persona_cuenta_id'),
            "Nombre": f"{name} {last_name}",
            "Email": kwargs.get('persona_cuenta__email'),
            "Monto": kwargs.get('monto'),
            "Cuenta": int(kwargs.get('cuenta')),
            "CuentaClabe": int(kwargs.get('cuentaclave'))
        }

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)

        size = self.request.query_params['size']
        NumeroTarjeta = request.query_params["card_number"]
        FechaDesde = request.query_params["start_date"]
        FechaHasta = request.query_params["end_date"]
        tipo_inntec = request.query_params["type"]
        cliente_externo = request.query_params['extern_client_id']

        log.json_request(request.query_params)
        pagination.PageNumberPagination.page_size = size

        gp = grupoPersona.objects.filter(person_id=cliente_externo, relacion_grupo_id=9).values('person_id').first()
        acoount = cuenta.objects.filter(persona_cuenta_id=gp['person_id']).values('persona_cuenta_id',
                                                                                  'persona_cuenta__name',
                                                                                  'persona_cuenta__last_name',
                                                                                  'cuenta',
                                                                                  'cuentaclave',
                                                                                  'monto')

        queryMovimientosTarjetaInntec = MovimientosTarjetaInntecClienteExterno(NumeroTarjeta, FechaDesde,
                                                                               FechaHasta, tipo_inntec)
        ordenada = sorted(queryMovimientosTarjetaInntec, key=itemgetter('Fecha'), reverse=True)
        log.json_response(queryMovimientosTarjetaInntec)
        lista = [self.render_json(**i) for i in acoount]
        page = self.paginate_queryset(ordenada)
        return self.get_paginated_response({"Info_cliente_externo": lista, "Movimientos": page})


# (ManuelCalixtro) Lista movimientos de una cuenta de cliente externo fisico
class MovimientosCuentaClienteExterno(ListAPIView):
    permission_classes = ()

    @staticmethod
    def render_json(**kwargs) -> Dict[str, Any]:
        name = kwargs.get("persona_cuenta__name")
        last_name = kwargs.get("persona_cuenta__last_name")
        return {
            "id": kwargs.get('persona_cuenta_id'),
            "Nombre": f"{name} {last_name}",
            "Email": kwargs.get('persona_cuenta__email'),
            "Monto": kwargs.get('monto'),
            "Cuenta": int(kwargs.get('cuenta')),
            "CuentaClabe": int(kwargs.get('cuentaclave'))
        }

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        NumeroCuenta = request.query_params["account_number"]
        FechaDesde = request.query_params["start_date"]
        FechaHasta = request.query_params["end_date"]
        cliente_externo = request.query_params['extern_client_id']
        log.json_request(request.query_params)
        FechaDesde, FechaHasta = MovimientosCuentaClienteExternoFisico(NumeroCuenta, FechaDesde, FechaHasta)

        gp = grupoPersona.objects.filter(person_id=cliente_externo, relacion_grupo_id=9).values('person_id').first()
        acoount = cuenta.objects.filter(persona_cuenta_id=gp['person_id']).values('persona_cuenta_id',
                                                                                  'persona_cuenta__name',
                                                                                  'persona_cuenta__last_name',
                                                                                  'persona_cuenta__email',
                                                                                  'cuenta',
                                                                                  'cuentaclave',
                                                                                  'monto')

        queryEgresos: List[Dict] = transferencia.objects.filter(
            cuenta_emisor=NumeroCuenta,
            fecha_creacion__gte=FechaDesde,
            fecha_creacion__lte=FechaHasta
        ).values("id", "concepto_pago", "monto", "fecha_creacion").order_by(
            "-fecha_creacion")

        listEgre = []
        listIng = []

        for query in queryEgresos:
            query["monto"] = "-$" + str(query["monto"])
            listEgre.append(query)

        queryIngresos = transferencia.objects.filter(
            cta_beneficiario=NumeroCuenta,
            fecha_creacion__gte=FechaDesde,
            fecha_creacion__lte=FechaHasta
        ).values("id", "concepto_pago", "monto", "fecha_creacion").order_by(
            "-fecha_creacion")

        for query in queryIngresos:
            query["monto"] = "$" + str(query["monto"])
            listIng.append(query)

        listEgre.extend(listIng)
        lista_ordenada = sorted(listEgre, key=itemgetter('id'), reverse=True)
        lista = [self.render_json(**i) for i in acoount]
        succ = {"Info_cliente_externo": lista, "Movimientos": lista_ordenada}
        log.json_response(succ)
        return Response(succ, status=status.HTTP_200_OK)


# (ManuelCalixtro 22-06-2022) Listar tarjetas asignadas a una cuenta y mostrar a quien le corresponden
class ListCardCompany(ListAPIView):
    permission_classes = ()

    @staticmethod
    def render_json(**kwargs) -> Dict[str, Any]:
        return {
            "card_id": kwargs.get('TarjetaId'),
            "number_card": int(kwargs.get('tarjeta')),
            "assignment_date": kwargs.get('fecha_register'),
            # "inntec_status": get_actual_state({"TarjetaID": kwargs.get('TarjetaId')})[0].get("Detalle"),
            "polipay_status": kwargs.get('statusInterno__nombreStatus'),
            "owner_email": kwargs.get('cuenta__persona_cuenta__email')
        }

    def list(self, request, *args, **kwargs):
        company_id = self.request.query_params['company_id']
        num_tarjeta = self.request.query_params['num_tarjeta']
        email = self.request.query_params['email']
        size = self.request.query_params['size']

        pagination.PageNumberPagination.page_size = size
        list_cards = tarjeta.objects.list_cards_company(company_id, num_tarjeta, email)

        lista = [self.render_json(**i) for i in list_cards]

        page = self.paginate_queryset(lista)
        return self.get_paginated_response(page)


# (ManuelCalixtro 22-06-2022) Listar tarjetas de todas las cuentas eje
class ListCardsAllCompanys(ListAPIView):
    permission_classes = ()

    @staticmethod
    def render_json(**kwargs) -> Dict[str, Any]:
        return {
            "card_id": kwargs.get('TarjetaId'),
            "number_card": int(kwargs.get('tarjeta')),
            "assignment_date": kwargs.get('fecha_register'),
            # "inntec_status": get_actual_state({"TarjetaID": kwargs.get('TarjetaId')})[0].get("Detalle"),
            "polipay_status": kwargs.get('statusInterno__nombreStatus'),
            "owner_company_name": kwargs.get('clientePrincipal__name')
        }

    def list(self, request, *args, **kwargs):
        num_tarjeta = self.request.query_params['num_tarjeta']
        name_company = self.request.query_params['name_company']
        size = self.request.query_params['size']

        pagination.PageNumberPagination.page_size = size

        get_all_companys = grupoPersona.objects.filter(relacion_grupo_id=1).values_list('empresa_id', flat=True)
        list_cards = tarjeta.objects.list_cards_all_company(get_all_companys, num_tarjeta, name_company)

        lista = [self.render_json(**i) for i in list_cards]

        page = self.paginate_queryset(lista)
        return self.get_paginated_response(page)


# (ManuelCalixtro) Muestra los detalles de las transacciones recibidas
class DetailsMovementsExternClient(viewsets.GenericViewSet):
    serializer_class = SerializerMovimentDetailsExternClient

    def list(self, request, *args, **kwargs):
        id = self.request.query_params['moviment_id']
        queryset = transferencia.objects.filter(id=id)

        context = {"instance_cta_benef": queryset}

        serializer = self.serializer_class(instance=queryset, many=True, context=context)
        return Response(serializer.data, status=status.HTTP_200_OK)