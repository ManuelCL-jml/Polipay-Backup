from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import atomic
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.generics import ListAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework import pagination, status
from rest_framework.response import Response

from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from MANAGEMENT.Utils.utils import get_values_list, get_homoclave
from MANAGEMENT.notifications.any.GenEmail import message_email

from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from apps.solicitudes.management import ValidaSolicitud, AceptarSolicitud, DevolverSolicitud
from apps.transaction.models import transferencia
from apps.users.api.web.admin.serializers.serializer_centro_costo import *
from apps.users.api.web.admin.serializers.serializer_cuenta_eje import *
from apps.users.api.web.serializers.documentos_serializer import SerializerAuthorizeIn
from apps.users.models import grupoPersona
from apps.users.management import *
# from polipaynewConfig.exceptions import MyHttpException


""" V i s t a s   P r i n c i p a l e s """


class GeneralAutorizarDocumentos(GenericViewSet):
    serializer_class_1 = None

    def get_queryset(self, *args, **kwargs):
        return get_Object_orList_error(*args, **kwargs)

    def create(self, request):
        pass

    def put(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.data)
        user_id = self.get_queryset(persona, username=request.user).get_only_id()
        serializer = self.serializer_class(data=request.data)
        succ = {"status": "Tu operación se realizo satisfactoriamente"}

        if serializer.is_valid(raise_exception=True):
            if serializer.auth_all_documents(user_id):

                log.json_response(succ)
                return Response(succ, status=status.HTTP_200_OK)
        log.json_response(succ)
        return Response(succ, status=status.HTTP_200_OK)


class AutorizarDocumentos(GeneralAutorizarDocumentos):
    serializer_class = SerializerAuthorizeCentroCosto


class BajaCentroCostoAdmin(GeneralAutorizarDocumentos):
    serializer_class = SerializerAuthorizeBaja


# - - - - - - L i s t a r   c e n t r o   d e   c o s t o s - - - - - -
class ListarCentroCostoActivos(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver centros de costo"]

    serializer_class = SerialiazerListarCentroCostosActivos
    pagination_class = PageNumberPagination

    # (AAF 2021-12-21) se añade filtrado por cliente o empresa
    @method_decorator(cache_page(60 * 0.1))
    def get(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size
        id = request.query_params['idCliente']
        log.json_request(request.query_params)

        queryset = grupoPersona.objects.filter(relacion_grupo_id=5, empresa_id=id).filter(person__state=True,
                                                                                          person__tipo_persona_id=1).order_by(
            '-fechacreacion')
        page = self.paginate_queryset(queryset)
        serializer = self.serializer_class(page, many=True)
        log.json_response(serializer.data)
        return self.get_paginated_response(serializer.data)


class ListarSolicitudesCentroCostos(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver centros de costo"]

    serializer_class = SerializerListarSolicitudesCentroCostos
    pagination_class = PageNumberPagination

    def get_queryset(self, *args, **kwargs):
        return filter_data_or_return_none(*args, **kwargs)

    def create(self, request):
        pass

    def list(self, request):
        log = RegisterLog(request.user, request)
        id = request.query_params['idCliente']
        size = request.query_params['size']
        log.json_request(request.query_params)

        pagination.PageNumberPagination.page_size = size
        centroCostos = grupoPersona.objects.get_persona(empresa_id=[id], relacion=5).order_by('-fechacreacion')
        solicitudesCC = []
        for CC in centroCostos:
            try:
                solicitud = Solicitudes.objects.filter(personaSolicitud_id=CC['person_id'],
                                                       estado_id__in=[1, 2]).order_by('-fechaSolicitud')
                solicitudesCC.append(solicitud[0])
            except:
                True
        page = self.paginate_queryset(solicitudesCC)
        serializer = self.serializer_class(page, many=True)
        log.json_response(serializer.data)
        return self.get_paginated_response(serializer.data)


def list(self, request, *args, **kwargs):
    log = RegisterLog(request.user, request)

    size = self.request.query_params['size']
    pagination.PageNumberPagination.page_size = size
    id = request.query_params['id']
    log.json_request(request.query_params)

    queryset = select_related("empresa", grupoPersona, empresa_id=id, relacion_grupo_id=5)
    page = self.paginate_queryset(queryset)
    serializer = self.serializer_class(page, many=True)
    log.json_response(serializer.data)
    return self.get_paginated_response(serializer.data)


class SolicitudAperturaCentroCostos(GenericViewSet):
    serializer_class_get = SerializerSolicitudAperturaCentroCostosOut
    serializer_class_update = SerializerAuthorizeIn

    def list(self, request):
        log = RegisterLog(request.user, request)

        pk_Centro_Costos = self.request.query_params["id"]
        log.json_request(request.query_params)

        instanceGP = get_Object_orList_error(grupoPersona, empresa_id=pk_Centro_Costos, relacion_grupo_id=4)
        instance = persona.objects.filter(id=instanceGP.empresa_id)
        serializer = self.serializer_class_get(instance, many=True)
        log.json_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AutorizarDocumentos(GenericViewSet):
    serializer_class_put = SerializerAuthorizeManyIn

    def get_queryset(self, *args, **kwargs):
        return get_Object_orList_error(*args, **kwargs)

    def create(self, request):
        pass

    def put(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.data)

        user_id = self.get_queryset(persona, username=request.user).get_only_id()
        serializer = self.serializer_class_put(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.auth_all_documents(user_id)

        succ = {"status": "Las operaciones se realizaron con exito"}
        log.json_response(succ)
        return Response(succ, status=status.HTTP_200_OK)


class DocumentosCentroCostosYRepresentanteLegal(GenericViewSet):
    serializer_class_get = SerializerDocumentosResultadosOut

    def list(self, request):
        log = RegisterLog(request.user, request)
        id_centro_costos = self.request.query_params["id"]
        log.json_request(request.query_params)

        queryset = grupoPersona.objects.filter(empresa_id=id_centro_costos, relacion_grupo_id=4)
        serializer = self.serializer_class_get(queryset, many=True)
        log.json_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# (AAF 2021-12-10) se añade id persona autorizacion al autorizar documentos
class AutorizarCentroCostos(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Autorizar centro de costo","Autorizar baja de centro de costo"]
    serializer_class = SerializerAuthorizeCenter
    serializer_class_update = DocumentsUpdate

    def create(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.data)

        data = request.data
        listaResponse = []
        flag = {}
        listaFlag = []
        solicitud = ValidaSolicitud(data[0]['idSol'])
        idCentroCostos = data[0]['centroCostoDetail']['id']
        idauth = data[0]['userAuth']
        # actualizando documentos
        if 'documentos_centro_costos' in data[0]:
            for docto in data[0]['documentos_centro_costos']:
                serializer = self.serializer_class_update(data=docto)
                if serializer.is_valid():
                    if docto["status"] != 'C':
                        flag['idDocto'] = docto['id']
                        flag['status'] = docto["status"]
                        listaFlag.append(flag)
                    docto = documentos.objects.get_documento_instance(docto['id'])
                    # data = serializer.validated_data
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
        # activamos centro y aceptamos solicitud
        AceptarSolicitud(data[0]['idSol'])
        objCentro = persona.objects.get(id=idCentroCostos)
        objCentro.state = True
        objCentro.is_active = True
        objCentro.save()
        ActivaCuenta(idCentroCostos)
        # obtenemos clabe de centro
        try:
            clabe = cuenta.objects.values("cuentaclave").get(persona_cuenta_id=idCentroCostos)
        except:
            clabe = "SINCLAVE"
        # objtenemos cta eje
        ctaEje = grupoPersona.objects.get_values_admin(idCentroCostos)
        # obtenemos admins
        admins = grupoPersona.objects.get_list_ids_admin(ctaEje[0]['empresa_id'])
        # envio mails
        for admin in admins:
            admin = persona.objects.get(id=admin)
            message_email(
                template_name="notificacion-centro-costos.html",
                context={"Admin": admin.name,
                         "CentroCostos": data[0]['centroCostoDetail']['name'],
                         "Estado": "Activado"},
                title="Notificacion Centro de costos",
                body="referencia",
                email=admin.email
            )
        succ = MyHtppSuccess(message={"clabe": clabe}, extra_data="tu operacion se realizo satisfactoriamente")
        log.json_response(succ.standard_success_responses())
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


# (AAF 2021-12-10)
class NotificarCentroCostos(GenericViewSet):
    # enviar notificacion a adminsitradores
    serializer_class = SerializerNotificacionCentro
    serializer_class_update = DocumentsUpdate

    def create(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.data)

        data = request.data
        listaResponse = []
        ValidaSolicitud(data[0]['idSol'])
        idCentroCostos = data[0]['centroCostoDetail']['id']
        # actualizando documentos
        if 'documentos_centro_costos' in data[0]:
            for docto in data[0]['documentos_centro_costos']:
                serializer = self.serializer_class_update(data=docto)
                if serializer.is_valid():
                    docto = documentos.objects.get_documento_instance(docto['id'])
                    docto = serializer.update(docto, serializer.validated_data, data[0]['userAuth'])
                    listaResponse.append("Documento " + str(docto.id) + " actualizado")
                else:
                    listaResponse.append("Datos Faltantes para el documento " + str(docto['id']))
        if 'documento_representante' in data[0]:
            for docto in data[0]['documento_representante']:
                serializer = self.serializer_class_update(data=docto)
                if serializer.is_valid():
                    docto = documentos.objects.get_documento_instance(docto['id'])
                    # data = serializer.validated_data
                    docto = serializer.update(docto, serializer.validated_data, data[0]['userAuth'])
                    listaResponse.append("Documento " + str(docto.id) + " actualizado")
                else:
                    listaResponse.append("Datos Faltantes para el documento " + str(docto['id']))
        # obtenemos cuenta eje
        ctaEje = grupoPersona.objects.get_values_admin(idCentroCostos)
        DevolverSolicitud(data[0]['idSol'], idCentroCostos)
        # obtenemos admins
        admins = grupoPersona.objects.get_list_ids_admin(ctaEje[0]['empresa_id'])
        # envio mails
        for admin in admins:
            admin = persona.objects.get(id=admin)
            message_email(
                template_name="notificacion-centro-costos.html",
                context={"Admin": admin.name,
                         "CentroCostos": data[0]['centroCostoDetail']['name'],
                         "Estado": "Devuelto"},
                title="Notificacion Centro de costos",
                body="referencia",
                email=admin.email
            )
        succ = MyHtppSuccess(message="tu operacion se realizo satisfactoriamente", extra_data=listaResponse)
        log.json_response(succ.standard_success_responses())
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


class ListarSolicitudesCostCenter(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver colaboradores"]

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        log.json_request(request.query_params)

        cuenta_eje_id = request.query_params['idCliente']
        size = request.query_params['size']
        pagination.PageNumberPagination.page_size = size

        solicitudes = Solicitudes.objects.filter(
            personaSolicitud_id=cuenta_eje_id,
            tipoSolicitud_id__in=[15, 16, 17, 18, 19, 20, 21, 22, 23],
            estado_id__in=[1, 2, 3]
        ).values(
            'id',
            'nombre',
            'fechaSolicitud',
            'intentos',
            'dato_json',
            'tipoSolicitud_id',
            'tipoSolicitud__nombreSol',
            'estado_id',
            'estado__nombreEdo',
        ).order_by('-fechaChange')

        for row in solicitudes:
            if row.get('dato_json'):
                row.update({'dato_json': json.loads(row.get('dato_json'))})

        page = self.paginate_queryset(solicitudes)
        log.json_response(page)
        return self.get_paginated_response(page)


class RequestDataVerifyDocumentsCostCenter:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_list_documents(self) -> List[Dict[str, Any]]:
        return self._request_data.get('Documents')

    @property
    def get_status_is_correct(self) -> List[str]:
        return [i for i in get_values_list('Status', self.get_list_documents) if i == 'C']


class ComponentVerifyDocument:
    _serializer_class: ClassVar[SerializerVerifyDocumentsCostCenter] = SerializerVerifyDocumentsCostCenterNew

    def __init__(self, request_data: RequestDataVerifyDocumentsCostCenter, admin: persona):
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


class ComponentActivateCostCenter:
    def __init__(self, request_data: RequestDataVerifyDocumentsCostCenter, cost_center_id: int):
        self._cost_center_id = cost_center_id
        self._request_data = request_data
        self._raise_error()

        if len(self._request_data.get_status_is_correct) == len(self._request_data.get_list_documents):
            self._activate_person()
            self._activate_account()

    def _raise_error(self):
        if not persona.objects.filter(id=self._cost_center_id).exists():
            raise ValueError('Centro de costos no es valido o no existe')

    def _activate_person(self):
        person = persona.objects.get(id=self._cost_center_id)
        person.state = True
        person.is_active = True
        person.save()

    def _activate_account(self):
        account = cuenta.objects.get(persona_cuenta_id=self._cost_center_id)
        account.is_active = True
        account.save()


class ComponentChangeStatusSolicitud:
    _status_devuelto: ClassVar[int] = 2
    _status_autorizada: ClassVar[int] = 4
    solicitud_instance: ClassVar[Solicitudes]

    def __init__(
            self,
            request_data: RequestDataVerifyDocumentsCostCenter,
            solicitud_id: int,
            admin: persona,
            cost_center_id: int
    ):
        self._request_data = request_data
        self._solicitud_id = solicitud_id
        self._admin = admin
        self._cost_center_id = cost_center_id
        self._change_status()

    def _update(self, status_id: int) -> NoReturn:
            Solicitudes.objects.filter(id=self._solicitud_id).update(
            estado_id=status_id,
            fechaChange=datetime.datetime.now(),
            personChange_id=self._admin.get_only_id()
        )
            self.solicitud_instance = Solicitudes.objects.get(id=self._solicitud_id)

    def _change_status(self):
        if len(self._request_data.get_status_is_correct) == len(self._request_data.get_list_documents):
            self._update(self._status_autorizada)
            ComponentActivateCostCenter(self._request_data, self._cost_center_id)

        if len(self._request_data.get_status_is_correct) != len(self._request_data.get_list_documents):
            self._update(self._status_devuelto)


# (ManuelCl 09-03-2022)Endpoint para ver los detalles de un centro de costos solicitud apertura
class DetailsCostCenter(RetrieveUpdateAPIView):
    serializer_class = SerializerDetailsCostCenter

    def retrieve(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        log.json_request(request.query_params)

        cost_center_id = self.request.query_params['cost_center_id']
        gp: grupoPersona = grupoPersona.objects.get(empresa_id=cost_center_id, relacion_grupo_id=4)

        serializer = self.serializer_class(instance=gp)
        log.json_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.data)
            admin: persona = request.user
            solicitud_id: int = self.request.query_params['solicitud_id']
            cost_center_id: int = self.request.query_params['cost_center_id']
            get_cost_center = persona.objects.get(id=cost_center_id)

            with atomic():
                request_data = RequestDataVerifyDocumentsCostCenter(request.data)
                ComponentVerifyDocument(request_data, admin)
                solicitud = ComponentChangeStatusSolicitud(request_data, solicitud_id, admin, cost_center_id)

                if solicitud.solicitud_instance.estado_id == 4:
                    send_notification_auth_cost_center(admin.get_full_name(), admin.email, get_cost_center.name)

                if solicitud.solicitud_instance.estado_id == 2:
                    send_notifications_returned_cost_center(admin.get_full_name(), admin.email, get_cost_center.name)

                msg = "Tu operación se realizo satisfactoriamente."
                succ = MyHtppSuccess(msg)
                log.json_response(succ.standard_success_responses())
                return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            msg = 'Ocurrio un error durante el proceso de decreación de un centro de costos'
            err = MyHttpError(msg, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except ValueError as e:
            msg = 'Ocurrio un error durante el proceso de decreación de un centro de costos'
            err = MyHttpError(msg, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


# (ManuelCl 09-03-2022)Endpoint para consultar un centro de costos
class ConsultarCostCenter(RetrieveAPIView):
    serializer_class = SerializerConsultarCentroCostos

    def get(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        log.json_request(request.query_params)
        cost_center_id = self.request.query_params['cost_center_id']
        gp = grupoPersona.objects.get(empresa_id=cost_center_id, relacion_grupo_id=4)

        serializer = self.serializer_class(instance=gp)
        log.json_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# (ManuelCl 09-03-2022)Endpoint ver detalles de baja de un centro de costos
class BajaCostCenter(RetrieveAPIView):
    serializer_class = SerializerBajaCostCenter

    def get(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        log.json_request(request.query_params)
        cost_center_id = self.request.query_params['cost_center_id']
        gp = grupoPersona.objects.get(empresa_id=cost_center_id, relacion_grupo_id=4)

        serializer = self.serializer_class(instance=gp)
        log.json_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# (ManuelCl 09-03-2022)Endpoint ver detalles de solicitud de cambio de clave trasposo final
class ClaveTraspasoCostCenter(RetrieveAPIView):
    serializer_class = SerializerDomicilioFiscalCostCenter

    def get(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        log.json_request(request.query_params)
        cost_center_id = self.request.query_params['cost_center_id']
        gp = grupoPersona.objects.get(empresa_id=cost_center_id, relacion_grupo_id=4)

        serializer = self.serializer_class(instance=gp)
        log.json_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# (ManuelCl 09-03-2022)Endpoint ver detalles de domicilio fiscal
class DomicilioFiscalCostCenter(RetrieveAPIView):
    serializer_class = SerializerClaveTraspasoFinalCostCenter

    def get(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        log.json_request(request.query_params)
        cost_center_id = self.request.query_params['cost_center_id']
        gp = grupoPersona.objects.get(empresa_id=cost_center_id, relacion_grupo_id=4)

        serializer = self.serializer_class(instance=gp)
        log.json_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# -----------------------------------------------------------


class RequestDataVerifyDocumentsClaveTraspaso:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_list_documents(self) -> List[Dict[str, Any]]:
        return self._request_data.get('Documents')

    @property
    def get_status_is_correct(self) -> List[str]:
        return [i for i in get_values_list('Status', self.get_list_documents) if i == 'C']


class ComponentVerifyDocumentClaveTraspaso:
    _serializer_class: ClassVar[SerializerVerifyDocumentsClaveTraspaso] = SerializerVerifyDocumentsClaveTraspaso

    def __init__(self, request_data: RequestDataVerifyDocumentsClaveTraspaso, admin: persona):
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


class ComponentChangeStatusSolicitudClaveTraspaso:
    _status_devuelto: ClassVar[int] = 2
    _status_autorizada: ClassVar[int] = 4
    _info_clave: ClassVar[Dict[str, Any]]

    def __init__(
            self,
            request_data: RequestDataVerifyDocumentsClaveTraspaso,
            solicitud_id: int,
            admin: persona,
            centro_costos_id: int
    ):
        self._request_data = request_data
        self._solicitud_id = solicitud_id
        self._admin = admin
        self._centro_costo_id = centro_costos_id
        self._info_clave = self._get_solicitud_info
        self._change_status()

    @property
    def _get_solicitud_info(self) -> Dict[str, Any]:
        data = Solicitudes.objects.filter(id=self._solicitud_id).values('dato_json').first()
        return json.loads(data.get('dato_json'))

    def _update(self, status_id: int) -> NoReturn:
        Solicitudes.objects.filter(id=self._solicitud_id).update(
            estado_id=status_id,
            fechaChange=datetime.datetime.now(),
            personChange_id=self._admin.get_only_id()
        )

    def _update_clave_traspaso(self):
        self._info_clave.pop('cost_center_id')
        self._info_clave.pop('name')
        persona.objects.filter(id=self._centro_costo_id).update(**self._info_clave)

    def _change_status(self):
        if len(self._request_data.get_status_is_correct) == len(self._request_data.get_list_documents):
            self._update(self._status_autorizada)
            self._update_clave_traspaso()

        if len(self._request_data.get_status_is_correct) != len(self._request_data.get_list_documents):
            self._update(self._status_devuelto)


# (ManuelCalixtro 10-03-2022) Endpoint para verificar los documentos de la solicitud de cambio de clave traspaso
class VerifyDocumentsClaveTraspaso(GenericViewSet):

    def create(self, request):
        pass

    def put(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.data)
            admin: persona = request.user
            solicitud_id: int = self.request.query_params['solicitud_id']
            centro_costos_id: int = self.request.query_params['centro_costos_id']

            with atomic():
                request_data = RequestDataVerifyDocumentsClaveTraspaso(request.data)
                ComponentVerifyDocumentClaveTraspaso(request_data, admin)
                ComponentChangeStatusSolicitudClaveTraspaso(request_data, solicitud_id, admin, centro_costos_id)

                success = MyHtppSuccess('Tu operacion se realizo de manera satisfactoria')
                log.json_response(success.standard_success_responses())
                return Response(success.standard_success_responses(), status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            msg = 'Ocurrio un error durante el proceso de decreación de un colaborador'
            err = MyHttpError(msg, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except (IntegrityError, ValueError, TypeError) as e:
            msg = 'Ocurrio un error durante el proceso de decreación de un colaborador'
            err = MyHttpError(msg, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)


class RequestDataVerifyDomicilioFiscal:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_list_documents(self) -> List[Dict[str, Any]]:
        return self._request_data.get('Documents')

    @property
    def get_status_is_correct(self) -> List[str]:
        return [i for i in get_values_list('Status', self.get_list_documents) if i == 'C']


class ComponentVerifyDocumentDomicilioFiscal:
    _serializer_class: ClassVar[SerializerVerifyDocumentsDomicilioFiscal] = SerializerVerifyDocumentsDomicilioFiscal

    def __init__(self, request_data: RequestDataVerifyDomicilioFiscal, admin: persona):
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


class ComponentChangeStatusSolicitudDomicilioFiscal:
    _status_devuelto: ClassVar[int] = 2
    _status_autorizada: ClassVar[int] = 4
    _info_address: ClassVar[Dict[str, Any]]

    def __init__(
            self,
            request_data: RequestDataVerifyDomicilioFiscal,
            solicitud_id: int,
            admin: persona,
            centro_costos_id: int
    ):
        self._request_data = request_data
        self._solicitud_id = solicitud_id
        self._admin = admin
        self._centro_costos_id = centro_costos_id
        self._info_address = self._get_solicitud_info
        self._change_status()

    @property
    def _get_solicitud_info(self) -> Dict[str, Any]:
        data = Solicitudes.objects.filter(id=self._solicitud_id).values('dato_json').first()
        return json.loads(data.get('dato_json'))

    def _update(self, status_id: int) -> NoReturn:
        Solicitudes.objects.filter(id=self._solicitud_id).update(
            estado_id=status_id,
            fechaChange=datetime.datetime.now(),
            personChange_id=self._admin.get_only_id()
        )

    def _update_domicilio(self, status_id: int) -> NoReturn:
        self._info_address.pop('cost_center_id')
        self._info_address.pop('name')
        domicilio.objects.filter(domicilioPersona_id=self._centro_costos_id).update(**self._info_address)

    def _change_status(self):
        if len(self._request_data.get_status_is_correct) == len(self._request_data.get_list_documents):
            self._update(self._status_autorizada)
            self._update_domicilio(self._status_autorizada)

        if len(self._request_data.get_status_is_correct) != len(self._request_data.get_list_documents):
            self._update(self._status_devuelto)


# (ManuelCalixtro 10-03-2022) Endpoint para verificar los documentos de la solicitud de cambio de domicilio fiscal
class VerifyDocumentsDomicilioFiscal(GenericViewSet):

    def create(self, request):
        pass

    def put(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.data)
            admin: persona = request.user
            solicitud_id: int = self.request.query_params['solicitud_id']
            centro_costos_id: int = self.request.query_params['centro_costos_id']

            with atomic():
                request_data = RequestDataVerifyDomicilioFiscal(request.data)
                ComponentVerifyDocumentDomicilioFiscal(request_data, admin)
                ComponentChangeStatusSolicitudDomicilioFiscal(request_data, solicitud_id, admin, centro_costos_id)

                success = MyHtppSuccess('Tu operacion se realizo de manera satisfactoria')
                log.json_response(success.standard_success_responses())
                return Response(success.standard_success_responses(), status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            msg = 'Ocurrio un error durante el proceso'
            err = MyHttpError(msg, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except (IntegrityError, ValueError, TypeError) as e:
            msg = 'Ocurrio un error durante el proceso'
            err = MyHttpError(msg, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)


class ComponentListCostCenter:
    data: ClassVar[List[Dict[str, Any]]]
    defaul_size: ClassVar[int] = 5

    def __init__(self, **kwargs):
        self._cuenta_eje_id = kwargs.get("cuenta_eje_id")
        self.size = kwargs.get("size", self.defaul_size)
        self._raise_error()
        self.data = self._list

    def _raise_error(self):
        if not grupoPersona.objects.filter(empresa_id=self._cuenta_eje_id).exists():
            raise ValueError('La cuenta eje no valida o no existe')

    @staticmethod
    def _render_list(**kwargs):
        return {
            "id": kwargs.get('persona_cuenta_id'),
            "name": kwargs.get('persona_cuenta__name'),
            "last_name": kwargs.get('persona_cuenta__last_name'),
            "cuenta": kwargs.get('cuenta'),
            "clabe": kwargs.get('cuentaclave'),
            "fecha_alta": kwargs.get('persona_cuenta__date_joined')
        }

    @property
    def _get_cost_center_active(self) -> List[int]:
        return grupoPersona.objects.select_related().filter(
            empresa_id=self._cuenta_eje_id,
            relacion_grupo_id=5,
            person__state=True
        ).values_list('person_id', flat=True)

    @property
    def _get_account_cost_center(self) -> List[Dict[str, Any]]:
        return cuenta.objects.select_related().filter(
            persona_cuenta_id__in=self._get_cost_center_active,
            is_active=True
        ).values(
            'persona_cuenta_id',
            'persona_cuenta__name',
            'persona_cuenta__last_name',
            'cuenta',
            'cuentaclave',
            'persona_cuenta__date_joined'
        ).order_by('-persona_cuenta__date_joined')

    @property
    def _list(self) -> List[Dict[str, Any]]:
        return [self._render_list(**row) for row in self._get_account_cost_center]


# (ChrGil 2022-03-10) Listar centros de costos activos de lado del admin
class ListCostCenterActiveAdmin(ListAPIView):
    pagination_class = PageNumberPagination

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            cuenta_eje_id: int = request.query_params['cuenta_eje_id']
            size: int = request.query_params['size']
            log.json_request(request.query_params)

            const_center_list = ComponentListCostCenter(cuenta_eje_id=cuenta_eje_id, size=size)

            self.pagination_class.page_size = const_center_list.size
            log.json_response(self.get_paginated_response(self.paginate_queryset(const_center_list.data)))
            return self.get_paginated_response(self.paginate_queryset(const_center_list.data))
        except (ObjectDoesNotExist, ValueError) as e:
            err = MyHttpError('Ocurrio un error al listar los centros de costos', real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


class RequestDataVerifyRepresentanteLegal:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_list_documents(self) -> List[Dict[str, Any]]:
        return self._request_data.get('Documents')

    @property
    def get_status_is_correct(self) -> List[str]:
        return [i for i in get_values_list('Status', self.get_list_documents) if i == 'C']


class ComponentGetInfoSolicitud:
    info_representante: ClassVar[Dict[str, Any]]
    info_solicitud: ClassVar[Dict[str, Any]]

    def __init__(self, request_data: RequestDataVerifyRepresentanteLegal, solicitud_id: int):
        self._request_data = request_data
        self._solicitud_id = solicitud_id
        self.info_representante = json.loads(self._get_representante_legal.get('dato_json'))
        self.info_solicitud = self._get_representante_legal

    @property
    def _get_representante_legal(self) -> Dict[str, Any]:
        return Solicitudes.objects.filter(id=self._solicitud_id).values('dato_json', 'id').first()


class ComponentCreateRepresentanteLegal:
    _serializer_class: ClassVar[SerializerRepresentanteLegal] = SerializerRepresentanteLegal
    person_id: ClassVar[int]

    def __init__(self, soliciutd: ComponentGetInfoSolicitud):
        self._soliciutd = soliciutd
        self._create()

    @property
    def _get_person_info(self) -> Dict[str, Any]:
        return self._soliciutd.info_representante.get('person_info')

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "nombre": self._get_person_info.get("name"),
            "paterno": self._get_person_info.get("paterno"),
            "materno": self._get_person_info.get("materno"),
            "nacimiento": self._get_person_info.get("fecha_nacimiento"),
            "rfc": self._get_person_info.get("rfc"),
            "homoclave": get_homoclave(self._get_person_info.get('rfc')),
            "email": self._get_person_info.get("email"),
            "telefono": self._get_person_info.get("phone"),
        }

    def _create(self):
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        self.person_id = serializer.create()


class ComponentCreateAddressRepresentanteLegal:
    _serializer_class: ClassVar[SerializerDomicilioIn] = SerializerCreateAddress

    def __init__(self, soliciutd: ComponentGetInfoSolicitud, representante: ComponentCreateRepresentanteLegal):
        self._soliciutd = soliciutd
        self._representante = representante
        self._create()

    @property
    def _get_person_info(self) -> Dict[str, Any]:
        return self._soliciutd.info_representante.get('person_dom')

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "codigopostal": self._get_person_info.get("codigopostal"),
            "colonia": self._get_person_info.get("colonia"),
            "alcaldia_mpio": self._get_person_info.get("alcaldia_mpio"),
            "estado": self._get_person_info.get("estado"),
            "calle": self._get_person_info.get("calle"),
            "pais": "México",
            "no_exterior": self._get_person_info.get("no_exterior"),
            "no_interior": self._get_person_info.get("no_interior"),
            "domicilioPersona_id": self._representante.person_id,
        }

    def _create(self):
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        serializer.create()


class ComponentDeleteRepresentanteLegal:
    def __init__(self, solcitud: ComponentGetInfoSolicitud, representante: ComponentCreateRepresentanteLegal):
        self._solicitud = solcitud
        self._representante = representante
        self._delete_relationship()
        self._update_person()

    def _delete_relationship(self):
        grupoPersona.objects.filter(person_id=self._solicitud.info_representante.get('representante_legal_id')).update(
            person_id=self._representante.person_id
        )

    def _update_person(self):
        persona.objects.filter(id=self._solicitud.info_representante.get('representante_legal_id')).update(
            state=False,
            is_active=False,
            motivo='Representante Legal Elimiando'
        )


class ComponentChangeStatusSolicitudNuevoRepresentanteLegal:
    _status_devuelto: ClassVar[int] = 2
    _status_autorizada: ClassVar[int] = 4

    def __init__(
            self,
            request_data: RequestDataVerifyRepresentanteLegal,
            solicitud: ComponentGetInfoSolicitud,
            admin: persona
    ):
        self._request_data = request_data
        self._solicitud = solicitud
        self._admin = admin
        self._change_status()

    def _update(self, status_id: int) -> NoReturn:
        Solicitudes.objects.filter(id=self._solicitud.info_solicitud.get('id')).update(
            estado_id=status_id,
            fechaChange=datetime.datetime.now(),
            personChange_id=self._admin.get_only_id()
        )

    def _change_status(self):
        if len(self._request_data.get_status_is_correct) == len(self._request_data.get_list_documents):
            self._update(self._status_autorizada)
            representante = ComponentCreateRepresentanteLegal(self._solicitud)
            ComponentCreateAddressRepresentanteLegal(self._solicitud, representante)
            ComponentVerifyDocumentRepresentanteLegal(self._request_data, representante, self._admin)
            ComponentDeleteRepresentanteLegal(self._solicitud, representante)

        if len(self._request_data.get_status_is_correct) != len(self._request_data.get_list_documents):
            self._update(self._status_devuelto)


class ComponentDetailNewRepresentanteLegal:
    detail: ClassVar[Dict[str, Any]]

    def __init__(self, solicitud_id: int):
        self._solicitud_id = solicitud_id
        self._raise_error()
        self.json_data = json.loads(self._get.get('dato_json'))
        self.detail = self._render_info

    def _raise_error(self):
        if not Solicitudes.objects.filter(id=self._solicitud_id).exists():
            raise ValueError('Solicitud no valida o no existe')

    @property
    def _get(self) -> Dict[str, Any]:
        return Solicitudes.objects.filter(id=self._solicitud_id).values('dato_json').first()

    @property
    def _render_info(self):
        return {
            "RepresentanteInfo": self.json_data.get('person_info'),
            "RepresentanteAddress": self.json_data.get('person_dom'),
            "RepresentanteOld": self._get_old_representante(self.json_data.get('representante_legal_id')),
            "RepresentanteDocuments": self._get_documents_representante(self.json_data.get('documents_id'))
        }

    @staticmethod
    def _get_old_representante(person_id: int) -> Dict[str, Any]:
        return persona.objects.filter(id=person_id).values('id', 'name', 'last_name', 'email').first()

    def _get_documents_representante(self, documents_id: List[int]) -> List[Dict[str, Any]]:
        return [self._documents_data(i) for i in documentos.objects.filter(id__in=documents_id)]

    @staticmethod
    def _documents_data(instance: documentos):
        return {
            "id": instance.id,
            "status": instance.status,
            "documento": instance.get_url_aws_document(),
            "TipoDocumento": instance.tdocumento.id
        }


class ComponentVerifyDocumentRepresentanteLegal:
    _serializer_class: ClassVar[SerializerVerifyDocumentsCostCenter] = SerializerVerifyDocumentsCostCenter

    def __init__(
            self,
            request_data: RequestDataVerifyRepresentanteLegal,
            representante: ComponentCreateRepresentanteLegal,
            admin: persona
    ):
        self._request_data = request_data
        self._new_representante = representante.person_id
        self._admin = admin
        self._create()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "representante_id": self._new_representante,
            "user_auth": self._admin,
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


class VerifyDocumentsNewRepresentanteLegal(RetrieveUpdateAPIView):

    def retrieve(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            solicitud_id: int = self.request.query_params['solicitud_id']
            log.json_request(request.data)

            detail = ComponentDetailNewRepresentanteLegal(solicitud_id)
            return Response(detail.detail, status=status.HTTP_200_OK)

        except (ValueError, TypeError) as e:
            err = MyHttpError('Ocurrio un error al ver detalles de esta solicitud', real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            solicitud_id: int = self.request.query_params['solicitud_id']
            admin: persona = self.request.user
            log.json_request(request.data)
            # admin: persona = persona.objects.get(id=6)

            with atomic():
                request_data = RequestDataVerifyRepresentanteLegal(request.data)
                solicitud = ComponentGetInfoSolicitud(request_data, solicitud_id)
                ComponentChangeStatusSolicitudNuevoRepresentanteLegal(request_data, solicitud, admin)

        except (ObjectDoesNotExist, ValueError, TypeError, AttributeError) as e:
            err = MyHttpError('Ocurrio un error al verificar el representante legal', real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            success = MyHtppSuccess('Tu operacion se realizo de manera satisfactoria')
            log.json_response(success.standard_success_responses())
            return Response(success.standard_success_responses(), status=status.HTTP_200_OK)


