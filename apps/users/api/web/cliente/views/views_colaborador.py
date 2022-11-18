import binascii
import json
import mimetypes

from django.db.transaction import atomic
from django.http.response import HttpResponse, FileResponse
from django.db import transaction, IntegrityError
# from apps import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response
from rest_framework import status, pagination
from rest_framework.viewsets import *
from rest_framework.generics import ListAPIView, UpdateAPIView, RetrieveUpdateAPIView
from rest_framework.pagination import PageNumberPagination

from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from operator import itemgetter

from MANAGEMENT.Utils.utils import remove_equal_items
from apps.permision.permisions import BlocklistPermissionV2
from apps.users.api.web.cliente.serializers.serializer_colaborador import *
# from apps.users.management import GenerarPDFSaldos
from apps.users.models import *
from polipaynewConfig.exceptions import MensajeError, NumInt, GetObjectOrError


class RequestDataColaborator:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_name(self) -> str:
        return self._request_data.get('name')

    @property
    def get_email(self) -> str:
        return self._request_data.get('email')

    @property
    def get_birth_day(self) -> str:
        return self._request_data.get('fecha_nacimiento')

    @property
    def get_phone(self) -> str:
        return self._request_data.get('phone')

    @property
    def get_cost_center_list(self) -> List[int]:
        return self._request_data.get('CenCost')

    @property
    def get_group_id(self) -> int:
        return self._request_data.get('GroupP')

    @property
    def get_documents_list(self) -> List[Dict[str, Any]]:
        return self._request_data.get('DocumentsColaborator')


class ComponentCreateColaborator:
    _serializer_class: ClassVar[SerializerAltaColaborador] = SerializerAltaColaborador
    person_id: ClassVar[int]

    def __init__(self, request_data: RequestDataColaborator):
        self._request_data = request_data
        self.person_id = self._create()
        self._assing_group()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "name": self._request_data.get_name,
            "email": self._request_data.get_email,
            "fecha_nacimiento": self._request_data.get_birth_day,
            "phone": self._request_data.get_phone,
        }

    def _create(self) -> int:
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.create()
        return instance.get_only_id()

    def _assing_group(self) -> NoReturn:
        add_group_permission(self._request_data.get_group_id, self.person_id)


# (ChrGil 2021-12-08) Crea apartir de un listado de documentos cualquier tipo de documento en formato PDF
# (ChrGil 2021-12-08) Actualmente es utilizado en alta centros de costos y alta cliente Moral
@dataclass
class ComponentCreateDocuments:
    _serializer_class: ClassVar[SerializerDocuments] = SerializerDocuments

    def __init__(self, request_data: RequestDataColaborator, colaborador: ComponentCreateColaborator):
        self._request_data = request_data
        self._colaborador = colaborador
        self._create()

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "tipo": kwargs.get('tdocumento_id'),
            "owner": self._colaborador.person_id,
            "base64_file": kwargs.get('documento')
        }

    def _create(self):
        for document in self._request_data.get_documents_list:
            serializer = self._serializer_class(data=self._data(**document))
            serializer.is_valid(raise_exception=True)
            serializer.create()


class ComponentAssingCostCenter:
    _type_group: ClassVar[int] = 8
    _nombre_grupo: ClassVar[str] = "Colaborador"
    _serializer_class: ClassVar[SerializerCostCenterColaborator] = SerializerCostCenterColaborator

    def __init__(self, request_data: RequestDataColaborator, colaborador: ComponentCreateColaborator):
        self._request_data = request_data
        self._colaborador = colaborador
        self.create()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "person_id": self._colaborador.person_id,
            "type_group": self._type_group,
            "nombre_grupo": self._nombre_grupo
        }

    @property
    def _data(self) -> Dict[str, List[int]]:
        return {
            "cost_center_list": self._request_data.get_cost_center_list
        }

    def create(self):
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.create()


class ComponentEnviaSolicitud:
    _apertura_colaborador: ClassVar[int] = 11

    def __init__(self, cuenta_eje_id: int, colaborador: ComponentCreateColaborator):
        self._cuenta_eje_id = cuenta_eje_id
        self._colaborador = colaborador
        self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "person_id": self._colaborador.person_id,
            "name": self._get_info_colaborador.get('name'),
        }

    @property
    def _get_info_colaborador(self) -> Dict[str, Any]:
        return persona.objects.filter(id=self._colaborador.person_id).values('id', 'name').first()

    def _create(self):
        Solicitudes.objects.create_solicitud(
            person_id=self._cuenta_eje_id,
            description="Apertura Colaborador",
            extra_data=json.dumps(self._data),
            tipo_solicitud=self._apertura_colaborador
        )


class ComponentRaiseCuentaEje:
    def __init__(self, cuenta_eje_id: int):
        self._cuenta_eje_id = cuenta_eje_id
        self._raise_cuenta_eje()

    def _raise_cuenta_eje(self):
        if not grupoPersona.objects.filter(empresa_id=self._cuenta_eje_id, relacion_grupo_id=1).exists():
            raise ValueError('Cuenta eje no valida o no existe')


class ComponentAssignColaboradorCuentaEje:
    def __init__(self, cuenta_eje_id: int, colaborador: ComponentCreateColaborator):
        self._cuenta_eje_id = cuenta_eje_id
        self._colaborador = colaborador
        self._assign_group()

    def _assign_group(self):
        grupoPersona.objects.create_grupo_persona(
            empresa_id=self._cuenta_eje_id,
            person_id=self._colaborador.person_id,
            group_name='Colaborador - Cuenta eje',
            type_group=14
        ).save()


class Colaborador(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear colaborador", "Editar colaborador"]
    serializer_class = AltaColaborador
    serializer_class_update = EditarColaborador

    def create(self, request):
        try:

            cuenta_eje_id: int = self.request.query_params['cuenta_eje_id']

            with atomic():
                ComponentRaiseCuentaEje(cuenta_eje_id)
                request_data = RequestDataColaborator(request.data)

                colaborador = ComponentCreateColaborator(request_data)
                ComponentCreateDocuments(request_data, colaborador)
                ComponentAssingCostCenter(request_data, colaborador)
                ComponentEnviaSolicitud(cuenta_eje_id, colaborador)
                ComponentAssignColaboradorCuentaEje(cuenta_eje_id, colaborador)

                msg = 'Tu solicitud ha sido enviada satisfactoriamente y ha quedado en proceso de verificación'
                scc = MyHtppSuccess(msg)
                return Response(scc.standard_success_responses(), status=status.HTTP_200_OK)
        except ValueError as e:
            err = MyHttpError(message=str(e), real_error="Error")
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


class ComponentVerDetalleDevolucion:
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
            "status": "Correcto" if document.status == 'C' else 'Devuelto',
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


class ComponentGetInfoColaborador:
    def __init__(self, colaborador_id: int):
        self._colaborador_id = colaborador_id
        self._raise_colaborador()

    def _raise_colaborador(self):
        if not persona.objects.filter(id=self._colaborador_id, state=True).exist():
            raise ValueError('Colaborador ya autorizado o no existe')


class ComponentAmendColaborador:
    _serializer_class: ClassVar[SerializerAmendColaborador] = SerializerAmendColaborador

    def __init__(self, request_data: RequestDataColaborator, colaborador_id: int):
        self._request_data = request_data
        self._colaborador = colaborador_id
        self._amend()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "person_id": self._colaborador
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "name": self._request_data.get_name,
            "email": self._request_data.get_email,
            "fecha_nacimiento": self._request_data.get_birth_day,
            "phone": self._request_data.get_phone
        }

    def _amend(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.amend()


# (ChrGil 2022-03-06) Corregir Documentos
class ComponentAmendDocuments:
    _serializer_class: ClassVar[SerializerAmendDocuments] = SerializerAmendDocuments

    def __init__(self, request_data: RequestDataColaborator, colaborador_id: int):
        self._request_data = request_data
        self._colaborador_id = colaborador_id
        self._amend_documents()

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "document_id": kwargs.get('DocumentId'),
            "owner": self._colaborador_id,
            "base64_file": kwargs.get('documento')
        }

    def _amend_documents(self):
        for document in self._request_data.get_documents_list:
            print(document)
            serializer = self._serializer_class(data=self._data(**document))
            serializer.is_valid(raise_exception=True)
            serializer.amend()


class ComponentAmendCostCenter:
    def __init__(self, request_data: RequestDataColaborator, colaborador_id: int):
        self._request_data = request_data
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
        for row in self._request_data.get_cost_center_list:
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
            if row.get('empresa_id') not in self._request_data.get_cost_center_list:
                grupoPersona.objects.get(id=row.get('id')).delete()
                continue


class ComponentSolicitudDevuelta:
    def __init__(self, request_data: RequestDataColaborator, solicitud_id: int, admin: persona, person_id: int):
        self._request_data = request_data
        self._solicitud_id = solicitud_id
        self._admin = admin
        self._person_id = person_id

        self._update_solicitud()

    @property
    def data(self):
        name = persona.objects.filter(id=self._person_id).values('name', 'last_name').first()

        return {
            "person_id": int(self._person_id),
            "name": name.get('name'),
            "phone": self._request_data.get_phone,
            "GrupoPermisoId": self._request_data.get_group_id,
            "CostCenterList": self._request_data.get_cost_center_list
        }

    def _update_solicitud(self):
        instance: Solicitudes = Solicitudes.objects.get(id=self._solicitud_id)
        instance.intentos += 1
        instance.estado_id = 1
        instance.fechaChange = datetime.datetime.now()
        instance.personChange_id = self._admin.get_only_id()
        instance.dato_json = json.dumps(self.data)
        instance.save()


class SolicitudDevueltaAltaColaborador(RetrieveUpdateAPIView):
    def retrieve(self, request, *args, **kwargs):
        solicitud_id: int = self.request.query_params['solicitud_id']
        list_documents = ComponentVerDetalleDevolucion(solicitud_id)

        if list_documents:
            return Response(list_documents.info, status=status.HTTP_200_OK)

        succ = MyHtppSuccess(message="No hay registros por mostrar")
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        try:
            admin: persona = request.user
            person_id: int = self.request.query_params['colaborador_id']
            solicitud_id: int = self.request.query_params['solicitud_id']

            with atomic():
                request_data = RequestDataColaborator(request.data)
                ComponentAmendColaborador(request_data, person_id)
                ComponentAmendDocuments(request_data, person_id)
                ComponentAmendCostCenter(request_data, person_id)
                update_group_permission(request_data.get_group_id, person_id)
                ComponentSolicitudDevuelta(request_data, solicitud_id, admin, person_id)

        except (IntegrityError, ValueError) as e:
            err = MyHttpError(message='Dirección de correo electronico no valido o ya existe', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            err = MyHttpError(message='Recurso no encontrado', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)
        else:
            msg = "Tu correción ha sido enviada satisfactoriamente y ha quedado en proceso de verificación."
            return Response(MyHtppSuccess(msg).standard_success_responses(), status=status.HTTP_200_OK)


class RequestDataEditColaborador:
    def __init__(self, reuqest_data: Dict[str, Any]):
        self._request_data = reuqest_data

    @property
    def get_cost_center_list(self) -> List[int]:
        return self._request_data.get('CostCenterList')

    @property
    def get_group_permission_id(self) -> int:
        return self._request_data.get('GrupoPermisoId')

    @property
    def get_phone(self) -> str:
        return self._request_data.get('phone')

    @property
    def get_document(self) -> Dict[str, Any]:
        return self._request_data.get('Document')


class ComponentEditColaborador:
    _serializer_class: ClassVar[SerializerEditColaborador] = SerializerEditColaborador

    def __init__(self, request_data: RequestDataEditColaborador, colaborador_id: int):
        self._request_data = request_data
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
            "phone": self._request_data.get_phone
        }

    def _create(self):
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        # serializer.update()


class ComponentEditCostCenter:
    def __init__(self, request_data: RequestDataEditColaborador, colaborador_id: int):
        self._request_data = request_data
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
        for row in self._request_data.get_cost_center_list:
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
            if row.get('empresa_id') not in self._request_data.get_cost_center_list:
                grupoPersona.objects.get(id=row.get('id')).delete()
                continue


class ComponentGetInfoColaboradorEdit:
    info: ClassVar[Dict[str, Any]]

    def __init__(self, colaborador_id: int):
        self._colaborador_id = colaborador_id
        colaborador = self._get_info_colaborador
        self.info = colaborador

        if not colaborador:
            raise ValueError('Colaborador no valido o no existe')

    @property
    def _get_info_colaborador(self) -> Union[Dict[str, Any], None]:
        return persona.objects.filter(id=self._colaborador_id).values('id', 'name').first()


class ComponentEnviaSolicitudEditarColaborador:
    _edit: ClassVar[int] = 12

    def __init__(
            self,
            request_data: RequestDataEditColaborador,
            colaborador: ComponentGetInfoColaboradorEdit,
            cuenta_eje_id: int
    ):
        self._request_data = request_data
        self._colaborador = colaborador
        self._cuenta_eje_id = cuenta_eje_id
        self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "person_id": self._colaborador.info.get('id'),
            "name": self._colaborador.info.get('name'),
            "phone": self._request_data.get_phone,
            "GrupoPermisoId": self._request_data.get_group_permission_id,
            "CostCenterList": self._request_data.get_cost_center_list
        }

    def _create(self) -> NoReturn:
        Solicitudes.objects.create_solicitud(
            person_id=self._cuenta_eje_id,
            description="Editar Colaborador",
            extra_data=json.dumps(self._data),
            tipo_solicitud=self._edit,
            status_id=3
        )


class ComponentEditDocumentColaborador:
    _type_document: ClassVar[int] = 16
    _serializer_class: ClassVar[SerializerDocuments] = SerializerDocuments

    def __init__(self, request_data: RequestDataEditColaborador, colaborador_id: int):
        self._request_data = request_data
        self._colaborador_id = colaborador_id
        self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "tipo": self._type_document,
            "owner": self._colaborador_id,
            "comment": "Carta Responsiva",
            "base64_file": self._request_data.get_document.get('documento')
        }

    def _create(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        serializer.create()


class ComponentDetailColaboradorEdit:
    info: ClassVar[Dict[str, Any]]

    def __init__(self, colaborador_id: int):
        self._colaborador_id = colaborador_id
        self.info = self._response

    @property
    def _get_info_colaborador(self) -> Dict[str, Any]:
        instance: persona = persona.objects.get(id=self._colaborador_id)
        return {
            "id": instance.id,
            "name": instance.name,
            "email": instance.email,
            "phone": instance.phone,
            "group": instance.groups.all().values('id', 'name')
        }

    @property
    def _get_info_cost_center(self):
        return grupoPersona.objects.filter(
            person_id=self._colaborador_id,
            relacion_grupo_id=8
        ).values('empresa_id', 'empresa__name')

    @staticmethod
    def _render(**kwargs):
        return {
            "id": kwargs.get('empresa_id'),
            "empresa__name": kwargs.get('empresa__name'),
        }

    @property
    def _response(self) -> Dict[str, Any]:
        return {
            "PersonInfo": self._get_info_colaborador,
            "CostCenterList": [self._render(**i) for i in self._get_info_cost_center],
        }


# (ChrGil 2022-03-09) Editar información de una colaborador
class EditarColaborador(RetrieveUpdateAPIView):
    def retrieve(self, request, *args, **kwargs):
        colaborador_id: int = self.request.query_params['colaborador_id']
        list_documents = ComponentDetailColaboradorEdit(colaborador_id)

        if list_documents:
            return Response(list_documents.info, status=status.HTTP_200_OK)

        succ = MyHtppSuccess(message="No hay registros por mostrar")
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        try:
            colaborador_id: int = self.request.query_params['colaborador_id']
            cuenta_eje_id: int = self.request.query_params['cuenta_eje_id']

            with atomic():
                request_data = RequestDataEditColaborador(request.data)
                colaborador = ComponentGetInfoColaboradorEdit(colaborador_id)
                ComponentEditColaborador(request_data, colaborador_id)
                ComponentEditDocumentColaborador(request_data, colaborador_id)
                ComponentEnviaSolicitudEditarColaborador(request_data, colaborador, cuenta_eje_id)

        except ValueError as e:
            err = MyHttpError(message="Ocurrio un error al editar tu colaborador", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            msg = "Tu solicitud ha sido enviada satisfactoriamente y ha quedado en proceso de verificación."
            return Response(MyHtppSuccess(msg).standard_success_responses(), status=status.HTTP_200_OK)


# (ChrGil 2022-03-09) Muestra el detalle de un colaborador (admin)
class ComponentVerDetalleEditColaborador:
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


class ComponentAmendEditarColaborador:
    _serializer_class: ClassVar[SerializerAmendEditColaborador] = SerializerAmendEditColaborador

    def __init__(self, request_data: RequestDataColaborator, colaborador_id: int):
        self._request_data = request_data
        self._colaborador = colaborador_id
        self._amend()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "person_id": self._colaborador
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "phone": self._request_data.get_phone
        }

    def _amend(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.amend()


class SolicitudDevueltaEditarColaborador(RetrieveUpdateAPIView):
    def retrieve(self, request, *args, **kwargs):
        solicitud_id: int = self.request.query_params['solicitud_id']
        list_documents = ComponentVerDetalleEditColaborador(solicitud_id)

        if list_documents:
            return Response(list_documents.info, status=status.HTTP_200_OK)

        succ = MyHtppSuccess(message="No hay registros por mostrar")
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        try:
            admin: persona = request.user
            person_id: int = self.request.query_params['colaborador_id']
            solicitud_id: int = self.request.query_params['solicitud_id']

            with atomic():
                request_data = RequestDataColaborator(request.data)
                ComponentAmendDocuments(request_data, person_id)
                ComponentSolicitudDevuelta(request_data, solicitud_id, admin, person_id)

        except IntegrityError as e:
            err = MyHttpError(message='Dirección de correo electronico no valido o ya existe', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            err = MyHttpError(message='Recurso no encontrado', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)
        else:
            msg = "Tu correción ha sido enviada satisfactoriamente y ha quedado en proceso de verificación."
            return Response(MyHtppSuccess(msg).standard_success_responses(), status=status.HTTP_200_OK)


# (ChrGil 2022-03-10) Listar Colaboradores cliente
class ComponentListColaboradoresClient:
    def __init__(self, cuenta_eje_id: int):
        self._cuenta_eje_id = cuenta_eje_id
        self.info = self._get_list_colaboradores

    @property
    def _get_all_colaboradores(self) -> List[Dict[str, Any]]:
        return grupoPersona.objects.filter(
            empresa_id=self._cuenta_eje_id,
            relacion_grupo_id=14,
        ).values(
            'person_id',
            'person__name',
            'person__groups',
            'person__groups__name',
        ).order_by('-person__date_joined')

    @staticmethod
    def _cost_center_count(**kwargs) -> int:
        return grupoPersona.objects.select_related(
            'relacion_grupo'
        ).filter(person_id=kwargs.get('person_id'), relacion_grupo_id=8).count()

    @property
    def get_status_solicitud(self) -> List[Dict[str, Any]]:
        return Solicitudes.objects.filter(
            personaSolicitud_id=4,
            tipoSolicitud_id__in=[11, 12, 13, 14],
        ).values('dato_json', 'id', 'estado__nombreEdo').order_by('-fechaChange')

    @property
    def _get_person_id(self):
        return remove_equal_items(
            key='person',
            list_data=[
                json.loads(
                    json.dumps(
                        {
                            "solicitud_id": i.get('id'),
                            "person": json.loads(i.get('dato_json')).get('person_id'),
                            "estado": i.get('estado__nombreEdo')
                        }
                    )
                )
                for i in self.get_status_solicitud
            ]
        )

    @property
    def _get_list_colaboradores(self):
        return [
            json.loads(
                json.dumps(
                    {
                        "data": self._get_all_colaboradores[i],
                        "cost_center": self._cost_center_count(**self._get_all_colaboradores[i]),
                        "estado": remove_equal_items(key='person', list_data=self._get_person_id)[i]
                    }
                )
            )
            for i in range(0, len(self._get_all_colaboradores))
        ]


class ListColaboradoresClient(ListAPIView):
    pagination_class = PageNumberPagination

    @staticmethod
    def _cost_center_count(**kwargs) -> int:
        return grupoPersona.objects.select_related(
            'relacion_grupo'
        ).filter(person_id=kwargs.get('person_id'), relacion_grupo_id=8).count()

    @staticmethod
    def get_grupo_permisos(**kwargs) -> Dict[str, Any]:
        instance = persona.objects.get(id=kwargs.get('person_id'))
        return instance.groups.all().values('id', 'name').last()

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        self.pagination_class.page_size = request.query_params['size']
        cuenta_eje: int = request.query_params['cuenta_eje']

        s = Solicitudes.objects.filter(
            personaSolicitud_id=cuenta_eje,
            tipoSolicitud_id__in=[11, 12, 13, 14],
        ).values(
            'id',
            'dato_json',
            'estado__nombreEdo',
            'tipoSolicitud_id',
            'tipoSolicitud__nombreSol'
        ).order_by('-fechaChange')

        for i in s:
            i["data"] = json.loads(i.pop('dato_json'))
            i["cost_center"] = self._cost_center_count(**i["data"])
            i['group'] = self.get_grupo_permisos(**i['data'])

        page = self.paginate_queryset(s)
        return self.get_paginated_response(page)


class ComponentGetInfoCuentaEje:
    def __init__(self, **kwargs):
        self._cuenta_eje_id = kwargs.get('cuenta_eje_id')

    def _raise_error(self):
        if not persona.objects.filter(id=self._cuenta_eje_id, state=True).exists():
            raise ValueError('Cuenta eje no valida o no existe')


class ComponentListColaboradoresActivos:
    queryset: ClassVar[List[Dict[str, Any]]]
    _defaul_size: ClassVar[int] = 5

    def __init__(self, **kwargs):
        self._cuenta_eje_id = kwargs.get('cuenta_eje_id')
        self._name = kwargs.get('name', '')
        self._group = kwargs.get('group', '')
        self.size = kwargs.get('size', self._defaul_size)
        self._start_date = kwargs.get('start_date', datetime.date.today() - datetime.timedelta(days=91))
        self._end_date = kwargs.get('end_date', datetime.date.today())
        self.queryset = [self._render(instance) for instance in self._list_person]

        if self._group != '':
            self.queryset = [i for i in self.queryset if i.get('group')]

    @property
    def _list(self) -> List[int]:
        return grupoPersona.objects.filter(
            empresa_id=self._cuenta_eje_id,
            relacion_grupo_id=14,
            person__state=True,
            person__tipo_persona_id=2
        ).values_list('person_id', flat=True)

    @property
    def _list_person(self) -> List[persona]:
        return persona.objects.filter(
            Q(date_joined__date__gte=self._start_date) &
            Q(date_joined__date__lte=self._end_date)
        ).filter(
            id__in=self._list, name__icontains=self._name).order_by('-date_joined')

    def _render(self, instance: persona):
        return {
            "dato_json": {
                "person_id": instance.id,
                "name": instance.name,
            },
            "email": instance.email,
            "fecha_creacion": instance.date_joined,
            "group": self._filter_group(instance, self._group),
            "cost_center": self._cost_center_count(person_id=instance.id)
        }

    @staticmethod
    def _filter_group(instance: persona, group: str) -> List[Dict[str, Any]]:
        return list(instance.groups.filter(name__icontains=group).values('id', 'name'))

    @staticmethod
    def _cost_center_count(**kwargs) -> int:
        return grupoPersona.objects.select_related(
            'relacion_grupo'
        ).filter(person_id=kwargs.get('person_id'), relacion_grupo_id=8).count()


class ListColaboradoresActivosCliente(ListAPIView):
    # permission_classes = ()
    pagination_class = PageNumberPagination

    # PARMS: cuenta_eje_id, name, group, size
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        try:

            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
            ComponentGetInfoCuentaEje(**data)
            colaboradores_activos = ComponentListColaboradoresActivos(**data)
            self.pagination_class.page_size = colaboradores_activos.size
            return self.get_paginated_response(self.paginate_queryset(colaboradores_activos.queryset))

        except ValueError as e:
            err = MyHttpError(message=str(e), real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


class ComponentListSolicitudesCliente:
    queryset: ClassVar[List[Dict[str, Any]]]
    _defaul_size: ClassVar[int] = 5
    _default_state: ClassVar[int] = [1, 2, 3]

    def __init__(self, **kwargs):
        self._cuenta_eje_id = kwargs.get('cuenta_eje_id')
        self.size = kwargs.get('size', self._defaul_size)
        self._state = kwargs.get('state_id', self._default_state)
        self._start_date = kwargs.get('start_date', datetime.date.today() - datetime.timedelta(days=91))
        self._end_date = kwargs.get('end_date', datetime.date.today())
        self.queryset = self._render

    def _list(self, **kwargs) -> Dict[str, Any]:
        return Solicitudes.objects.filter(
            Q(fechaChange__date__gte=self._start_date) &
            Q(fechaChange__date__lte=self._end_date)
        ).filter(
            personaSolicitud_id=self._cuenta_eje_id,
            tipoSolicitud_id__in=[11, 12, 13],
            **kwargs
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

    @property
    def _render(self) -> List[Dict[str, Any]]:
        list_colaboradores = []

        if isinstance(self._state, str):
            list_colaboradores = self._list(estado_id=int(self._state))

        if isinstance(self._state, list):
            list_colaboradores = self._list(estado_id__in=self._state)

        for row in list_colaboradores:
            if row.get('dato_json'):
                row.update({'dato_json': json.loads(row.get('dato_json'))})
        return list_colaboradores


class ListSolicitudesColaboradoresCliente(ListAPIView):
    pagination_class = PageNumberPagination

    # PARAMS: cuenta_eje_id, size, state_id
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        try:

            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
            ComponentGetInfoCuentaEje(**data)
            colaboradores_activos = ComponentListSolicitudesCliente(**data)
            self.pagination_class.page_size = colaboradores_activos.size
            return self.get_paginated_response(self.paginate_queryset(colaboradores_activos.queryset))

        except ValueError as e:
            err = MyHttpError(message=str(e), real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)



# class Colaborador(GenericViewSet):
#     # permission_classes = (BlocklistPermissionV2,)
#     # permisos = ["Crear colaborador", "Editar colaborador"]
#     serializer_class = AltaColaborador
#     serializer_class_update = EditarColaborador
#     permission_classes = ()
#
#     def create(self, request):
#         grupoPermiso = request.data["GroupP"]
#         serializer = self.serializer_class(data=request.data)
#         pk_user = request.data["CuentaEjeId"]
#         GetObjectOrError(persona, id=pk_user)
#         if serializer.is_valid(raise_exception=True):
#             instance = serializer.create(serializer.validated_data, grupoPermiso, pk_user)
#             return Response(
#                 {"status": {"message": "Se creo colaborador", "id": instance.id}},
#                 status=status.HTTP_200_OK)
#
#     def put(self, request):
#         groupId = request.data["GroupP"]
#         colaborador = self.request.query_params["id"]
#         serializer = self.serializer_class_update(data=request.data)
#         if serializer.is_valid(raise_exception=True):
#             serializer.update(colaborador, groupId)
#         return Response({"status": "Colaborador actualizado"}, status=status.HTTP_200_OK)


class CentroCostos(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver centros de costo"]
    serializer_class = CentroCostosSerializer

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        ceje = self.request.query_params["CuentaEje"]
        queryset = grupoPersona.objects.filter(empresa_id=ceje, relacion_grupo_id=5)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CargarDocumentos(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear colaborador", "Editar colaborador"]
    serializer_class = CrearDocumentosColaborador
    serializer_class_update = EditarDocumentosColaborador

    def create(self, request):
        colaborador = self.request.query_params["id"]
        documentoI = request.data["Identificacion"]
        documentoR = request.data["Responsiva"]
        GetObjectOrError(persona, id=colaborador)
        pk_user = request.data["CuentaEjeId"]
        GetObjectOrError(persona, id=pk_user)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                with transaction.atomic():
                    serializer.create(colaborador, documentoR, documentoI, pk_user)
                    return Response(
                        {
                            "status": "Tu solicitud ha sido enviada satisfactoriamente y ha quedado en proceso de verificación"},
                        status=status.HTTP_200_OK)
            except Exception as e:
                message = "Ourrio un error al asignar los documentos al colaborador, Error:   " + str(e)
                error = {'field': '', "data": '', 'message': message}
                for Centros in grupoPersona.objects.filter(person_id=colaborador, relacion_grupo_id=8):
                    Centros.delete()
                instance = persona.objects.get(id=colaborador)
                instance.delete()
                MensajeError(error)

    def put(self, request):
        colaborador = self.request.query_params["id"]
        documentoR = request.data["Responsiva"]
        documentoI = request.data["Identificacion"]
        serializer = self.serializer_class_update(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(colaborador, documentoR, documentoI)
            return Response(
                {"status": "Tu solicitud ha sido enviada satisfactoriamente y ha quedado en proceso de verificación"},
                status=status.HTTP_200_OK)


def CartaResponsiva(request):
    filename = 'TMP/web/Pruebadecartaresponsiva.pdf'
    filepath = filename
    path = open(filepath, 'r')
    mime_type, _ = mimetypes.guess_type(filepath)
    response = FileResponse(open(filename, 'rb'))
    response['Content-Disposition'] = "attachment; filename=%s" % filename
    return response


# (ManuelCalixtro 28/11/2021 Se esta terminando la vista para ver detalles de un colaborador faltan los permisos asiganados)
class ColaboratorsDetails(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver detalles de colaborador"]

    def list(self, request, *args, **kwargs):
        id = request.query_params['colaborador_id']
        data_colaborador = persona.objects.filter(id=id).values('id', 'name', 'last_name', 'email', 'phone',
                                                                'is_active', 'motivo').first()
        print(request.user)
        cost_centers = grupoPersona.objects.filter(person_id=id).values('empresa__name')
        permisos = ListPermission(id)
        doc = documentos.objects.filter(person_id=id, historial=0).filter(Q(tdocumento_id=12) | Q(tdocumento_id=16))
        serializer = DetailsColaborator(instance=doc, many=True)
        return Response({'colaborador': data_colaborador,
                         'permisos': permisos,
                         'centro_costos_asigandos': cost_centers,
                         'documentos': serializer.data})


class DesactivarColaborador(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Eliminar colaborador"]
    serializer_class = DarBajaColaborador

    def create(self, request):
        try:
            with atomic():
                person_id = self.request.query_params["person_id"]
                instance: persona = persona.objects.get(id=person_id)

                instance.state = False
                instance.is_active = False
                instance.motivo = request.data['comentario']
                instance.save()

                serializer = self.serializer_class(data=request.data)
                serializer.is_valid(raise_exception=True)
                documento = request.data["documento"]
                serializer.create(documento, instance)

        except (ObjectDoesNotExist, ValueError, binascii.Error, TypeError) as e:
            err = MyHttpError(message="Ocurrio un error al descativar el colaborador", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            scc = MyHtppSuccess(message="Tu operación se realizó satisfactoriamente")
            return Response(scc.standard_success_responses(), status=status.HTTP_200_OK)


class VerColaborador(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver colaboradores"]
    # pagination_class = PageNumberPagination

    def list(self, request):
        size = self.request.query_params["size"]
        nombre = self.request.query_params["Nombre"]
        numcencos = self.request.query_params["CentroCostos"]
        estado = self.request.query_params["Estado"]
        nombrepermisos = self.request.query_params["Permiso"]
        size = NumInt(size=size)
        pagination.PageNumberPagination.page_size = size
        pkcuen = self.request.query_params["CueId"]
        cuecen = grupoPersona.objects.filter(empresa_id=pkcuen, relacion_grupo_id=5)
        colaboradores = []
        colabSinRepetir = []
        usuario = []
        for personId in cuecen:
            colab = grupoPersona.objects.filter(relacion_grupo_id=8, empresa_id=personId.person_id)
            for i in colab:
                colaboradores.append(i.person_id)
        if colaboradores:
            for i in colaboradores:
                if i not in colabSinRepetir:
                    colabSinRepetir.append(i)
        resultado = []
        for i in colabSinRepetir:
            user = persona.objects.get(id=i)
            if nombre:
                if nombre not in user.name:
                    resultado.append(1)
            if nombrepermisos:
                nombrepermisos = pkcuen + "*" + nombrepermisos
                try:
                    namepermision = user.groups.all().values("name")
                    if str(namepermision[0]["name"]) not in str(nombrepermisos):
                        resultado.append(1)
                except:
                    resultado.append(1)
            if numcencos:
                centrocostos = grupoPersona.objects.filter(relacion_grupo_id=8, person_id=user.id).count()
                if int(numcencos) != int(centrocostos):
                    resultado.append(1)
            if nombre != "" and nombrepermisos != "" and numcencos != "":
                resultado.append(1)
            if resultado:
                resultado.clear()
            else:
                estadocol = None
                if documentos.objects.filter(person_id=user.id, tdocumento_id=19, historial=0):
                    estadocol = "Desactivado"
                else:
                    if user.is_active == True:
                        estadocol = "Activado"
                    else:
                        try:
                            document1 = documentos.objects.get(person_id=user.id, tdocumento_id=16,
                                                               historial=0)
                            document2 = documentos.objects.get(person_id=user.id, tdocumento_id=12,
                                                               historial=0)
                            if document1.status == "D" or document2.status == "D":
                                estadocol ="Devuelto"
                            if document1.status == "P" or document2.status == "P":
                                estadocol = "Pendiente"
                            if document1.status == "C" and document2.status == "C":
                                estadocol = "Activado"
                        except:
                            estadocol = "S/E"
                    if estado:
                        if str(estadocol) == str(estado):
                            dic = {"id": user.id, "name": user.name,
                                   "cencost": grupoPersona.objects.filter(relacion_grupo_id=8,
                                                                          person_id=user.id).count(),
                                   "grupo": user.groups.all().values("name"), "estado": estadocol}
                            usuario.append(dic)
                    else:
                        dic = {"id": user.id, "name": user.name,
                               "cencost": grupoPersona.objects.filter(relacion_grupo_id=8, person_id=user.id).count(),
                               "grupo": user.groups.all().values("name"), "estado": estadocol}
                        usuario.append(dic)
        lista_ordenada = sorted(usuario, key=itemgetter('id'), reverse=True)
        page = self.paginate_queryset(lista_ordenada)
        return Response(page, status=status.HTTP_200_OK)
