import datetime
import json
from typing import Dict, Any, List, ClassVar, NoReturn

from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import pagination, status
# from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.generics import ListAPIView, UpdateAPIView, RetrieveUpdateAPIView

from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from MANAGEMENT.Utils.utils import random_password, get_values_list
from MANAGEMENT.mails.messages import EmailWelcomeColaborador
from apps.logspolipay.manager import RegisterLog
from apps.permision.manager import update_group_permission
from apps.permision.permisions import BlocklistPermissionV2
from apps.solicitudes.management import AceptarSolicitud, ValidaSolicitud, DevolverSolicitud
from apps.solicitudes.message import message_email
from apps.solicitudes.models import Solicitudes
from apps.users.api.web.admin.serializers.serializer_centro_costo import DocumentsUpdate
from apps.users.api.web.admin.serializers.serializer_colaborator import SerializerDocumentosOut, SerListColaboratorAct, \
    SerializerListSolColaborator, SerializerVerifyDocuments, SerializerEditColaborador
from apps.users.models import documentos, persona, grupoPersona


# # (AAF 2021-12-10) se añade id persona autorizacion al autorizar documentos
# class AuthorizeColab(GenericViewSet):
#     # permission_classes = (BlocklistPermissionV2,)
#     # permisos = ["Autorizar Colaborador", "Autorizar baja de Colaborador"]
#     permission_classes = ()
#     serializer_class = DocumentsUpdate
#
#     def create(self, request):
#         data = request.data
#         print(data)
#         listaResponse = []
#         flag = {}
#         estado = "Correcto"
#         listaFlag = []
#         solicitud = ValidaSolicitud(data[0]['idSol'])
#         idauth = data[0]['userAuth']
#         idColaborador = data[0]['ColaboradorDetail']['id']
#         if 'documento_colaborador' in data[0]:
#             for docto in data[0]['documento_colaborador']:
#                 serializer = self.serializer_class(data=docto)
#                 if serializer.is_valid():
#                     if docto["status"] != 'C':
#                         flag['idDocto'] = docto['id']
#                         flag['status'] = docto["status"]
#                         listaFlag.append(flag)
#                         estado = docto["status"]
#                     docto = documentos.objects.get_documento_instance(docto['id'])
#                     docto = serializer.update(docto, serializer.validated_data, idauth)
#                     listaResponse.append("Documento " + str(docto.id) + " actualizado")
#                 else:
#                     print(serializer.errors)
#                     listaResponse.append("Datos Faltantes para los documentos " )
#                     err = MyHttpError(message=listaResponse, real_error="Documentos no Modificados")
#                     return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
#         # # envio mail
#         # message_email(
#         #     template_name="notificacion-colaborador.html",
#         #     context={"Admin": objColaborator.name,
#         #              "Colaborador": data[0]['ColaboradorDetail']['name'],
#         #              "Estado": estado},
#         #     title="Notificacion Centro de costos",
#         #     body="referencia",
#         #     email=objColaborator.email
#         # )
#         # Validamos que la bandera este blanca
#         print(listaFlag != [])
#         if listaFlag != []:
#             print(listaFlag != [])
#             # err = MyHttpError(message=listaFlag, real_error="Documentos no Autorizados")
#             succ = MyHtppSuccess(message="Documentos no Autorizados", extra_data=listaFlag)
#         else:
#             # activamos Colaborador
#             AceptarSolicitud(data[0]['idSol'])
#             objColaborator = persona.objects.get(id=idColaborador)
#             objColaborator.state = True
#             password = random_password()
#             message_email(
#                 template_name="colab_email.html",
#                 context={"full_name": objColaborator.name,
#                          "Usuario": objColaborator.email,
#                          "pass": password},
#                 title="Notificacion Colaborador",
#                 body="referencia",
#                 email=objColaborator.email
#             )
#             objColaborator.set_password(password)
#             objColaborator.save()
#             succ = MyHtppSuccess(message="tu operacion se realizo satisfactoriamente", extra_data=listaResponse)
#         return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


# (AAF 2021-12-10) se añade id persona autorizacion al autorizar documentos
# class AuthorizeColab(GenericViewSet):
#     # permission_classes = (BlocklistPermissionV2,)
#     # permisos = ["Autorizar Colaborador", "Autorizar baja de Colaborador"]
#     permission_classes = ()
#     serializer_class = DocumentsUpdate
#
#     def create(self, request):
#         data = request.data
#         listaResponse = []
#         flag = {}
#         estado = "Correcto"
#         listaFlag = []
#
#         try:
#             with atomic():
#                 ValidaSolicitud(data[0]['idSol'])
#                 idauth = data[0]['userAuth']
#                 idColaborador = data[0]['ColaboradorDetail']['id']
#
#                 if 'documento_colaborador' in data[0]:
#                     for docto in data[0]['documento_colaborador']:
#
#                         serializer = self.serializer_class(data=docto)
#                         if serializer.is_valid():
#
#                             if docto["status"] != 'C':
#                                 flag['idDocto'] = docto['id']
#                                 flag['status'] = docto["status"]
#                                 listaFlag.append(flag)
#                                 # estado = docto["status"]
#
#                             docto = documentos.objects.get_documento_instance(docto['id'])
#                             docto = serializer.update(docto, serializer.validated_data, idauth)
#                             listaResponse.append("Documento " + str(docto.id) + " actualizado")
#
#                         else:
#                             listaResponse.append("Datos Faltantes para los documentos ")
#                             err = MyHttpError(message=listaResponse, real_error="Documentos no Modificados")
#                             return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
#
#                 # Validamos que la bandera este blanca
#                 if len(listaFlag) != 0:
#                     succ = MyHtppSuccess(message="Documentos no Autorizados", extra_data=listaFlag)
#                 else:
#                     # activamos Colaborador
#                     AceptarSolicitud(data[0]['idSol'])
#
#                     objColaborator = persona.objects.get(id=idColaborador)
#                     objColaborator.state = True
#                     objColaborator.is_active = True
#                     password = random_password()
#                     objColaborator.set_password(password)
#                     objColaborator.save()
#
#                     message_email(
#                         template_name="colab_email.html",
#                         context={"full_name": objColaborator.name,
#                                  "Usuario": objColaborator.email,
#                                  "pass": password},
#                         title="Notificacion Colaborador",
#                         body="referencia",
#                         email=objColaborator.email
#                     )
#
#         except Exception as e:
#             err = MyHttpError("Ocurrio un error al autorizar al colaborador", real_error=str(e))
#             return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
#         else:
#             succ = MyHtppSuccess(message="Su operación se realizo de manera satisfactoria", extra_data=listaResponse)
#             return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


# class NotifyColab(GenericViewSet):
#     serializer_class = DocumentsUpdate
#     permission_classes = ()
#
#     def create(self, request):
#         data = request.data
#         listaResponse = []
#         solicitud = ValidaSolicitud(data[0]['idSol'])
#         idColaborador = data[0]['ColaboradorDetail']['id']
#         # actualizando documentos
#         if 'documento_colaborador' in data[0]:
#             for docto in data[0]['documento_colaborador']:
#                 serializer = self.serializer_class(data=docto)
#                 if serializer.is_valid():
#                     docto = documentos.objects.get_documento_instance(docto['id'])
#                     docto = serializer.update(docto, serializer.validated_data,data[0]["userAuth"])
#                     listaResponse.append("Documento " + str(docto.id) + " actualizado")
#                 else:
#                     listaResponse.append("Datos Faltantes para el documento " + str(docto['id']))
#         # obtenemos cuenta eje
#         cCostos = grupoPersona.objects.get_values_empresa(idColaborador, 8)
#         ctaEje = grupoPersona.objects.get_values_empresa(cCostos[0]['empresa_id'], 5)
#         DevolverSolicitud(data[0]['idSol'],idColaborador)
#         # obtenemos admins
#         admins = grupoPersona.objects.get_list_ids_admin(ctaEje[0]['empresa_id'])
#         # envio mails
#         for admin in admins:
#             admin = persona.objects.get(id=admin)
#             message_email(
#                 template_name="notificacion-colaborador.html",
#                 context={"Admin": admin.name,
#                          "Colaborador": data[0]['ColaboradorDetail']['name'],
#                          "Estado": "Devuelto"},
#                 title="Notificacion Centro de costos",
#                 body="referencia",
#                 email=admin.email
#             )
#         succ = MyHtppSuccess(message="tu operacion se realizo satisfactoriamente", extra_data=listaResponse)
#         return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


# AAF (2021-12-27) DETALLES DE COLABORADORES
# class ColaboratorDetail(GenericViewSet):
#     permission_classes = (BlocklistPermissionV2,)
#     permisos = ["Ver detalles de colaborador"]
#     serializer_class_get = SerializerDocumentosOut
#
#     def list(self, request):
#         log = RegisterLog(request.user, request)
#         id_cc = self.request.query_params["id"]
#         log.json_request(request.query_params)
#         queryset = grupoPersona.objects.filter(person_id=id_cc, relacion_grupo_id=8)
#         serializer = self.serializer_class_get(queryset, many=True)
#         log.json_response(serializer.data)
#         return Response(serializer.data, status=status.HTTP_200_OK)


# AAF(2021-12-27) LISTAR COLABORADORES
class ListarColaboradoresActivos(ListAPIView):
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Ver colaboradores"]
    serializer_class = SerListColaboratorAct

    def _render(self, **kwargs):
        p = kwargs.get('person__groups__name').split('*')[1]

        return {
            "id": kwargs.get('person_id'),
            "fechaAlta": kwargs.get('person__date_joined'),
            "permisos": p,
            "name": kwargs.get('person__name'),
            "correo": kwargs.get('person__email'),
        }

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        log.json_request(request.query_params)
        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size
        cuenta_eje_id = request.query_params['cuenta_eje_id']
        queryset = grupoPersona.objects.filter(
            relacion_grupo_id=14,
            empresa_id=cuenta_eje_id,
            person__state=True,
            person__tipo_persona_id=2
        ).values(
            'person_id',
            'person__name',
            'person__email',
            'person__groups',
            'person__groups__name',
            'person__date_joined'
        ).order_by('-person__date_joined')

        query = [self._render(**i) for i in queryset]

        page = self.paginate_queryset(query)
        log.json_response(page)
        return self.get_paginated_response(page)


# AAF (2021-12-27) LISTAR  SOLICITUDES COLABORADORES
class ListarSolicitudesColaborator(ListAPIView):
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Ver colaboradores"]
    serializer_class = SerializerListSolColaborator
    permission_classes = ()

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        log.json_request(request.query_params)
        cuenta_eje_id = request.query_params['idCliente']
        size = request.query_params['size']
        pagination.PageNumberPagination.page_size = size

        solicitudes = Solicitudes.objects.filter(
            nombre__in=['Apertura Colaborador', 'Editar Colaborador'],
            personaSolicitud_id=cuenta_eje_id,
            tipoSolicitud_id__in=[11, 12, 13],
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


class RequestDataVerifyDocumentsColaborador:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_list_documents(self) -> List[Dict[str, Any]]:
        return self._request_data.get('Documents')

    @property
    def get_status_is_correct(self) -> List[str]:
        return [i for i in get_values_list('Status', self.get_list_documents) if i == 'C']


class ComponentVerifyDocument:
    _serializer_class: ClassVar[SerializerVerifyDocuments] = SerializerVerifyDocuments

    def __init__(self, request_data: RequestDataVerifyDocumentsColaborador, admin: persona):
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


class ComponentActivateColaborador:
    _defaul_pass: ClassVar[str] = "Temporal123.$"

    def __init__(self, request_data: RequestDataVerifyDocumentsColaborador, colaborador_id: int):
        self._colaborador_id = colaborador_id
        self._request_data = request_data
        self._raise_error()

        if len(self._request_data.get_status_is_correct) == len(self._request_data.get_list_documents):
            self._activate()

    def _raise_error(self):
        if not persona.objects.filter(id=self._colaborador_id).exists():
            raise ValueError('El colaborador no es valido o no existe')

    def _activate(self):
        person = persona.objects.get(id=self._colaborador_id)
        person.state = True
        person.password = self._defaul_pass
        person.set_password(person.password)
        person.save()

        EmailWelcomeColaborador(to=person.email, name=person.name, password=self._defaul_pass, email=person.email)


class ComponentChangeStatusSolicitud:
    _status_devuelto: ClassVar[int] = 2
    _status_autorizada: ClassVar[int] = 4

    def __init__(
            self,
            request_data: RequestDataVerifyDocumentsColaborador,
            solicitud_id: int,
            admin: persona,
            colaborador_id: int
    ):
        self._request_data = request_data
        self._solicitud_id = solicitud_id
        self._admin = admin
        self._colaborador_id = colaborador_id
        self._change_status()

    def _update(self, status_id: int) -> NoReturn:
        Solicitudes.objects.filter(id=self._solicitud_id).update(
            estado_id=status_id,
            fechaChange=datetime.datetime.now(),
            personChange_id=self._admin.get_only_id()
        )

    def _change_status(self):
        if len(self._request_data.get_status_is_correct) == len(self._request_data.get_list_documents):
            self._update(self._status_autorizada)
            print(self._status_autorizada)

        if len(self._request_data.get_status_is_correct) != len(self._request_data.get_list_documents):
            self._update(self._status_devuelto)


# (ChrGil 2022-03-09) Muestra el detalle de un colaborador (admin)
class ComponentVerDetalleColaboradorAdmin:
    info: ClassVar[List[Dict[str, Any]]]

    def __init__(self, solicitud_id: int):
        self._solicitud_id = solicitud_id
        self._colaborador = self._get_solicitud_info
        self.info = self._response

    @property
    def _get_solicitud_info(self) -> int:
        data = Solicitudes.objects.filter(id=self._solicitud_id).values('dato_json').first()
        return json.loads(data.get('dato_json')).get('person_id')

    @staticmethod
    def _documents(document: documentos) -> Dict[str, Any]:
        return {
            "id": document.id,
            "comentario": document.comentario,
            "tipo": document.get_tipo_documento,
            "status": document.status,
            "name": document.get_owner,
            "file": document.get_url_aws_document()
        }

    @staticmethod
    def _person(person: persona) -> Dict[str, Any]:
        return {
            "id": person.id,
            "name": person.name,
            "email": person.email,
            "phone": person.phone,
            "birth_date": person.fecha_nacimiento,
            "group": person.groups.all().values("id", "name")
        }

    @property
    def _list_documents_status(self) -> List[Dict[str, Any]]:
        d = documentos.objects.select_related('person', 'tdocumento').filter(person_id=self._colaborador)[0:2]
        return [self._documents(i) for i in d]

    @property
    def _get_info_colaborador(self) -> List[Dict[str, Any]]:
        p = persona.objects.filter(id=self._colaborador)
        return [self._person(i) for i in p]

    @property
    def _get_cost_center_info(self) -> List[Dict[str, Any]]:
        return grupoPersona.objects.filter(
            person_id=self._colaborador, relacion_grupo_id=8).values('id', 'empresa_id', 'empresa__name')

    @property
    def _response(self) -> Dict[str, Any]:
        return {
            "PersonInfo": self._get_info_colaborador,
            "DocumentsPerson": self._list_documents_status,
            "CostCenterList": list(self._get_cost_center_info)
        }


# (ChrGil 2022-03-09) Verificar documentos colaborador
class VerifyDocumentsColaborador(RetrieveUpdateAPIView):

    def retrieve(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        solicitud_id: int = self.request.query_params['solicitud_id']
        log.json_request(request.query_params)
        list_documents = ComponentVerDetalleColaboradorAdmin(solicitud_id)

        if list_documents:
            return Response(list_documents.info, status=status.HTTP_200_OK)

        succ = MyHtppSuccess(message="No hay registros por mostrar")
        log.json_response(succ.standard_success_responses())
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            # admin: persona = persona.objects.get(id=6)
            admin: persona = request.user
            solicitud_id: int = self.request.query_params['solicitud_id']
            colaborador_id: int = self.request.query_params['colaborador_id']
            log.json_request(request.data)

            with atomic():
                request_data = RequestDataVerifyDocumentsColaborador(request.data)
                ComponentVerifyDocument(request_data, admin)
                ComponentChangeStatusSolicitud(request_data, solicitud_id, admin, colaborador_id)
                ComponentActivateColaborador(request_data, colaborador_id)

                msg = "Tu operación se realizo satisfactoriamente."
                succ = MyHtppSuccess(msg)
                log.json_response(succ.standard_success_responses())
                return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

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


# (ChrGil 2022-03-09) Muestra el detalle de un colaborador (admin)
class ComponentVerDetalleEditColaboradorAdmin:
    info: ClassVar[List[Dict[str, Any]]]

    def __init__(self, solicitud_id: int):
        self._solicitud_id = solicitud_id
        self._colaborador = self._get_solicitud_info.get('person_id')
        self.info = self._response

    @property
    def _get_solicitud_info(self) -> Dict[str, Any]:
        data = Solicitudes.objects.filter(id=self._solicitud_id).values('dato_json').first()
        return json.loads(data.get('dato_json'))

    @staticmethod
    def _documents(document: documentos) -> Dict[str, Any]:
        return {
            "id": document.id,
            "comentario": document.comentario,
            "tipo": document.get_tipo_documento,
            "status": document.status,
            "name": document.get_owner,
            "file": document.get_url_aws_document()
        }

    @staticmethod
    def _person(person: persona) -> Dict[str, Any]:
        return {
            "id": person.id,
            "name": person.name,
            "email": person.email,
            "phone": person.phone,
            "birth_date": person.fecha_nacimiento,
            "group": person.groups.all().values("id", "name")
        }

    @property
    def _list_documents_status(self) -> Dict[str, Any]:
        d = documentos.objects.select_related('person', 'tdocumento').filter(
            person_id=self._colaborador, tdocumento_id=16).last()

        return self._documents(d)

    @property
    def _get_info_colaborador(self) -> List[Dict[str, Any]]:
        p = persona.objects.filter(id=self._colaborador)
        return [self._person(i) for i in p]

    @property
    def _get_cost_center_info(self) -> List[Dict[str, Any]]:
        return grupoPersona.objects.filter(
            person_id=self._colaborador, relacion_grupo_id=8).values('id', 'empresa_id', 'empresa__name')

    @staticmethod
    def _get_news_cost_center_info(cost_center_list: List[int]) -> List[Dict[str, Any]]:
        return grupoPersona.objects.filter(
            empresa_id__in=cost_center_list,
            relacion_grupo_id=4
        ).values('empresa_id', 'empresa__name', 'relacion_grupo_id', 'person__date_joined')

    @staticmethod
    def _get_group(group_id: int) -> List[Dict[str, Any]]:
        return Group.objects.filter(id=group_id).values('id', 'name').first()

    @property
    def _response(self) -> Dict[str, Any]:
        return {
            "PersonInfo": self._get_info_colaborador,
            "DocumentsPerson": self._list_documents_status,
            "CostCenterList": list(self._get_cost_center_info),
            "SolicitudInfo": {
                "CostCenterList": self._get_news_cost_center_info(self._get_solicitud_info.get('CostCenterList')),
                "NewGroup": self._get_group(self._get_solicitud_info.get('GrupoPermisoId')),
                "NewPhone": self._get_solicitud_info.get('phone')
            }
        }


class ComponentGetInfoSolicitudes:
    def __init__(self, solicitud_id: int):
        self._solicitud_id = solicitud_id
        self.info: Dict = json.loads(self._get_info_solicitud.get('dato_json'))

    @property
    def _get_info_solicitud(self) -> Dict[str, Any]:
        return Solicitudes.objects.filter(id=self._solicitud_id).values('dato_json').first()


class ComponentEditColaborador:
    _serializer_class: ClassVar[SerializerEditColaborador] = SerializerEditColaborador

    def __init__(self, solicitud: ComponentGetInfoSolicitudes, colaborador_id: int):
        self._solicitud = solicitud
        self._colaborador_id = colaborador_id
        self._create()

    @property
    def _context(self):
        return {
            "person_id": self._colaborador_id
        }

    @property
    def _data(self):
        return {
            "phone": self._solicitud.info.get('phone')
        }

    def _create(self):
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.update()


class ComponentEditGroupPermission:
    def __init__(self, solicitud: ComponentGetInfoSolicitudes, colaborador_id: int):
        self._solicitud = solicitud
        self._colaborador_id = colaborador_id
        self._update_group_permission()

    def _update_group_permission(self) -> NoReturn:
        update_group_permission(self._solicitud.info.get('GrupoPermisoId'), self._colaborador_id)


class ComponentEditCostCenter:
    def __init__(self, solicitudes: ComponentGetInfoSolicitudes, colaborador_id: int):
        self._solicitudes = solicitudes
        self._colaborador_id = colaborador_id
        self.create_if_not_exists()
        self.delete_if_is_remove()

    def _exist_cost_center(self, cost_center_id: int) -> bool:
        return grupoPersona.objects.filter(
            empresa_id=cost_center_id,
            person_id=self._colaborador_id,
            relacion_grupo_id=8
        ).exists()

    def create_if_not_exists(self):
        for row in self._solicitudes.info.get('CostCenterList'):
            if not self._exist_cost_center(row):
                grupoPersona.objects.create(
                    empresa_id=row,
                    person_id=self._colaborador_id,
                    relacion_grupo_id=8,
                    nombre_grupo="Colaborador - Centro Costos",
                )

    def delete_if_is_remove(self):
        g = grupoPersona.objects.filter(person_id=self._colaborador_id, relacion_grupo_id=8).values('empresa_id', 'id')

        for row in g:
            if row.get('empresa_id') not in self._solicitudes.info.get('CostCenterList'):
                grupoPersona.objects.get(id=row.get('id')).delete()
                continue


class ValidateSolicitud:
    _edit_colaborador: ClassVar[ComponentEditColaborador] = ComponentEditColaborador
    _edit_cost_center: ClassVar[ComponentEditCostCenter] = ComponentEditCostCenter
    _edit_group: ClassVar[ComponentEditGroupPermission] = ComponentEditGroupPermission

    def __init__(
            self,
            request_data: RequestDataVerifyDocumentsColaborador,
            solicitud: ComponentGetInfoSolicitudes,
            colaborador_id: int
    ):
        self._request_data = request_data
        self._solicitud = solicitud
        self._colaborador_id = colaborador_id
        self._validate()

    def _validate(self):
        if len(self._request_data.get_status_is_correct) == len(self._request_data.get_list_documents):
            self._edit_cost_center(self._solicitud, self._colaborador_id)
            self._edit_colaborador(self._solicitud, self._colaborador_id)
            self._edit_group(self._solicitud, self._colaborador_id)


# (ChrGil 2022-03-09) Verificar información editada colaborador
class VerifyDocumentsEditColaborador(RetrieveUpdateAPIView):

    def retrieve(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        solicitud_id: int = self.request.query_params['solicitud_id']
        log.json_request(request.query_params)
        list_documents = ComponentVerDetalleEditColaboradorAdmin(solicitud_id)

        if list_documents:
            return Response(list_documents.info, status=status.HTTP_200_OK)

        succ = MyHtppSuccess(message="No hay registros por mostrar")
        log.json_response(succ.standard_success_responses())
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)

        try:
            # admin: persona = persona.objects.get(id=6)
            admin: persona = request.user
            solicitud_id: int = self.request.query_params['solicitud_id']
            colaborador_id: int = self.request.query_params['colaborador_id']
            log.json_request(request.data)

            with atomic():
                request_data = RequestDataVerifyDocumentsColaborador(request.data)
                solicitud = ComponentGetInfoSolicitudes(solicitud_id)
                ComponentVerifyDocument(request_data, admin)

                ValidateSolicitud(request_data, solicitud, colaborador_id)
                ComponentChangeStatusSolicitud(request_data, solicitud_id, admin, colaborador_id)

                msg = "Tu operación se realizo satisfactoriamente."
                succ = MyHtppSuccess(msg)
                log.json_response(succ.standard_success_responses())
                return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            msg = 'Ocurrio un error durante el proceso de decreación de un colaborador'
            err = MyHttpError(msg, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except TypeError as e:
            msg = 'Ocurrio un error durante el proceso de decreación de un colaborador'
            err = MyHttpError(msg, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)
