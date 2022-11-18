import datetime
import json
from dataclasses import dataclass
from typing import Any, Dict, ClassVar, Union, List

from django.db.models import Q
from django.db.transaction import atomic
from django.utils.datastructures import MultiValueDictKeyError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import IntegrityError, OperationalError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status, pagination
from rest_framework.generics import ListAPIView, UpdateAPIView, DestroyAPIView, RetrieveUpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView

from MANAGEMENT.Utils.utils import get_homoclave
from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from apps.solicitudes.api.web.serializers.centro_costos_serializers import SerializerCreateSol
from apps.solicitudes.management import Sumarsolicitud, ValidaSolicitud
from apps.users.api.web.cliente.serializers.serializer_centro_costo import *
from apps.users.management import get_id_cuenta_eje, filter_data_or_return_none
from apps.solicitudes.models import *
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from apps.users.messages import sendNotificationCreateCostCenter
from apps.users.models import cuenta
from apps.users.serializers import SerializerRepresentanteLegal, SerializerRazonSocial
from apps.users.ManagementClass import (
    CreateAddress,
    CreateDocuments,
    CreateAccountClienteMoral,
    CreateGrupoPersona,
    CrearSolicitud,
    RequestData)
from MANAGEMENT.Language.LanguageUnregisteredUser import LanguageUnregisteredUser
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.EndPoint.EndPointInfo import get_info


class ComponentEnviaSolicitud:
    _apertura_cost_center: ClassVar[int] = 15

    def __init__(self, cost_center_id: Dict[str, Any], cuenta_eje_id: int):
        self._cost_center_info = cost_center_id
        self._cuenta_eje_id = cuenta_eje_id
        self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "cost_center_id": self._cost_center_info.get('id'),
            "name": self._cost_center_info.get('name'),
        }

    def _create(self):
        Solicitudes.objects.create_solicitud(
            person_id=self._cuenta_eje_id,
            description="Apertura Centro de costos",
            extra_data=json.dumps(self._data),
            tipo_solicitud=self._apertura_cost_center
        )


@dataclass
class CreateRazonSocial:
    data: Dict[str, Any]
    _serializer_class: ClassVar[SerializerRazonSocial] = SerializerRazonSocial
    _razon_social_data: ClassVar[Dict[str, Any]] = {}
    _create_address: ClassVar[CreateAddress] = CreateAddress
    _create_documents: ClassVar[CreateDocuments] = CreateDocuments

    @property
    def execute(self) -> Dict[str, Any]:
        self._create()
        self._create_address(self.data.get('DomicilioFiscal'), self._razon_social_data.get('id')).execute()
        self._create_documents(self._razon_social_data.get('id'), self.data.get('Documentos')).execute()
        return self._razon_social_data

    @property
    def _data(self) -> Dict[str, Any]:
        data = self.data.get('data')

        return {
            "razon_social": data.get("RazonSocial"),
            "centro_costos_name": data.get("CentroCosto"),
            "rfc": data.get("rfc"),
        }

    def _create(self) -> None:
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        self._razon_social_data = serializer.create()


@dataclass
class CreateRepresentanteLegal:
    data: Dict[str, Any]
    _serializer_class: ClassVar[SerializerRepresentanteLegal] = SerializerRepresentanteLegal
    _representante_legal_id: ClassVar[int] = 0
    _create_address: ClassVar[CreateAddress] = CreateAddress
    _create_documents: ClassVar[CreateDocuments] = CreateDocuments

    @property
    def execute(self) -> int:
        self._create()
        self._create_address(self.data.get('DomicilioFiscal'), self._representante_legal_id).execute()
        self._create_documents(self._representante_legal_id, self.data.get('Documentos')).execute()
        return self._representante_legal_id

    @property
    def _data(self) -> Dict[str, Any]:
        data = self.data.get("data")

        return {
            "nombre": data.get("Nombre"),
            "paterno": data.get("ApellidoPaterno"),
            "materno": data.get("ApellidoMaterno"),
            "nacimiento": data.get("FechaNacimiento"),
            "rfc": data.get("rfc"),
            "homoclave": data.get("HomoClave"),
            "email": data.get("CorreoElectronico"),
            "telefono": data.get("NumeroTelefonico")
        }

    def _create(self):
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        self._representante_legal_id = serializer.create()


@dataclass
class CreateClienteMoralController:
    request_data: RequestData
    cuenta_eje_id: int
    _razon_social: ClassVar[CreateRazonSocial] = CreateRazonSocial
    _representante_legal: ClassVar[CreateRepresentanteLegal] = CreateRepresentanteLegal
    _create_account: ClassVar[CreateAccountClienteMoral] = CreateAccountClienteMoral
    _create_grupo_persona: ClassVar[CreateGrupoPersona] = CreateGrupoPersona

    def execute(self) -> None:
        razon_social: Dict[str, Any] = self._razon_social(self.request_data.get_razon_social).execute
        representante_legal_id: int = self._representante_legal(self.request_data.get_representante_legal).execute
        self._create_account(razon_social.get('id'), self.cuenta_eje_id).execute()

        # (ChrGil 2021-12-07) Se crea relación del centro de costos y un cliente Moral
        self._create_grupo_persona(razon_social['id'], representante_legal_id, 4, razon_social['name']).execute()
        self._create_grupo_persona(self.cuenta_eje_id, razon_social.get('id'), 5, razon_social['name']).execute()
        ComponentEnviaSolicitud(cost_center_id=razon_social, cuenta_eje_id=self.cuenta_eje_id)


# (ChrGil 2021-12-08) Creación de un centro de costos
class CreateCostCenter(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear centro de costo"]

    # permission_classes = ()

    def create(self, request):
        try:
            user: persona = request.user
            cuenta_eje_id: int = get_id_cuenta_eje(user.get_only_id())

            with atomic():
                CreateClienteMoralController(RequestData(request.data), cuenta_eje_id).execute()
                sendNotificationCreateCostCenter(user.get_full_name(), user.email, request.data.copy())

        except (
                ObjectDoesNotExist, MultipleObjectsReturned, ValueError, IntegrityError, OperationalError,
                AttributeError) as e:
            err = MyHttpError("Ocurrio un error durante el proceso de creación de un cliente moral", str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            succ = MyHtppSuccess("Tu solicitud se envio de manera satisfactoria y se encuentra en estado pendiente")
            return Response(succ.standard_success_responses(), status=status.HTTP_201_CREATED)


class RequestDataAmendNewRepresentanteLegal:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_data(self) -> Dict[str, Any]:
        return self._request_data.get('RepresentanteLegal').get('data')

    @property
    def get_address(self) -> Dict[str, Any]:
        return self._request_data.get('RepresentanteLegal').get('DomicilioFiscal')

    @property
    def get_documents(self) -> List[Dict[str, Any]]:
        return self._request_data.get('RepresentanteLegal').get('Documentos')


class ComponentGetInfoSolicitud:
    def __init__(self, solicitud_id: int):
        self._solicitud_id = solicitud_id
        self.solicitud_info = self._get_solicitud

    def _raise_error(self):
        ...

    @property
    def _get_solicitud(self) -> Dict[str, Any]:
        queryset = Solicitudes.objects.filter(id=self._solicitud_id).values('dato_json').first()
        return json.loads(queryset.get('dato_json'))


# (ChrGil 2022-03-25) Corregir información de un nuevo representante legal
class ComponentCorregirNuevoRepresentanteLegal:
    _serializer_class: ClassVar[SerializerAmendRepresentanteLegal] = SerializerAmendRepresentanteLegal

    def __init__(self, request_data: RequestDataAmendNewRepresentanteLegal, solicitudes: ComponentGetInfoSolicitud):
        self._request_data = request_data
        self._solicitudes = solicitudes.solicitud_info
        self._amend()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "representate_id": self._solicitudes.get('representante_legal_id')
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return self._request_data.get_data

    @staticmethod
    def _render_data(**kwargs):
        return {
            "nombre": kwargs.get('Nombre'),
            "paterno": kwargs.get('ApellidoPaterno'),
            "materno": kwargs.get('ApellidoMaterno'),
            "nacimiento": kwargs.get('FechaNacimiento'),
            "rfc": kwargs.get('rfc'),
            "homoclave": kwargs.get('HomoClave'),
            "email": kwargs.get('CorreoElectronico'),
            "telefono": kwargs.get('NumeroTelefonico'),
        }

    def _amend(self):
        serializer = self._serializer_class(data=self._render_data(**self._data), context=self._context)
        serializer.is_valid(raise_exception=True)


# (ChrGil 2022-03-25) Corregir domicilio de un nuevo representante legal
class ComponentCorregirDomicilioFiscalNuevoRepresentanteLegal:
    _serializer_class: ClassVar[SerializerCorregirAddress] = SerializerCorregirAddress

    def __init__(self, request_data: RequestDataAmendNewRepresentanteLegal, solicitudes: ComponentGetInfoSolicitud):
        self._request_data = request_data
        self._solicitudes = solicitudes.solicitud_info
        self._amend()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "person_id": self._solicitudes.get('representante_legal_id')
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return self._request_data.get_address

    @staticmethod
    def _render_data(**kwargs):
        return {
            "codigopostal": kwargs.get("CodigoPostal"),
            "colonia": kwargs.get("Colonia"),
            "alcaldia_mpio": kwargs.get("Municipio"),
            "estado": kwargs.get("Estado"),
            "calle": kwargs.get("Calle"),
            "pais": kwargs.get("Pais"),
            "no_exterior": kwargs.get("NoExterior"),
            "no_interior": kwargs.get("NoInterior"),
        }

    def _amend(self):
        serializer = self._serializer_class(data=self._render_data(**self._data), context=self._context)
        serializer.is_valid(raise_exception=True)


# (ChrGil 2022-03-25) Mostrar detalles al corregir un representante legal, lado del cliente
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
            "TipoDocumento": instance.tdocumento.id,
            "Comentario": instance.comentario
        }


# (ChrGil 2022-03-06) Corregir Documentos representante legal
class ComponentAmendDocumentsNewRepresentanteLegal:
    _serializer_class: ClassVar[SerializerAmendDocumentsCostCenter] = SerializerAmendDocumentsCostCenter

    def __init__(self, request_data: RequestDataAmendNewRepresentanteLegal, solicitudes: ComponentGetInfoSolicitud):
        self._request_data = request_data
        self._solicitudes = solicitudes.solicitud_info
        self._amend_documents()

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "document_id": kwargs.get('DocumentId'),
            "owner": self._solicitudes.get('representante_legal_id'),
            "base64_file": kwargs.get('Documento')
        }

    def _amend_documents(self):
        for document in self._request_data.get_documents:
            serializer = self._serializer_class(data=self._data(**document))
            serializer.is_valid(raise_exception=True)
            serializer.amend()


class ComponentSolicitudDevueltaNuevoRepresentante:
    def __init__(
            self,
            admin: persona,
            solicitud_id: int,
            solicitud: ComponentGetInfoSolicitud,
            request_data: RequestDataAmendNewRepresentanteLegal
    ):
        self._solicitud = solicitud.solicitud_info
        self._solicitud_id = solicitud_id
        self._request_data = request_data
        self._admin = admin
        self._amend_representante()
        self._update_solicitud()

    @staticmethod
    def _render_data(**kwargs):
        return {
            "name": kwargs.get('Nombre'),
            "paterno": kwargs.get('ApellidoPaterno'),
            "materno": kwargs.get('ApellidoMaterno'),
            "fecha_nacimiento": kwargs.get('FechaNacimiento'),
            "rfc": kwargs.get('rfc'),
            "email": kwargs.get('CorreoElectronico'),
            "phone": kwargs.get('NumeroTelefonico'),
        }

    @staticmethod
    def _render_address(**kwargs):
        return {
            "codigopostal": kwargs.get('CodigoPostal'),
            "colonia": kwargs.get('Colonia'),
            "alcaldia_mpio": kwargs.get('Municipio'),
            "estado": kwargs.get('Estado'),
            "calle": kwargs.get('Calle'),
            "no_exterior": kwargs.get('NoExterior'),
            "no_interior": kwargs.get('NoInterior'),
        }

    def _amend_representante(self):
        self._solicitud.update(
            {
                "person_info": self._render_data(**self._request_data.get_data),
                "person_dom": self._render_address(**self._request_data.get_address)
            }
        )

    def _update_solicitud(self):
        instance: Solicitudes = Solicitudes.objects.get(id=self._solicitud_id)
        instance.intentos += 1
        instance.estado_id = 1
        instance.fechaChange = datetime.datetime.now()
        instance.personChange_id = self._admin.get_only_id()
        instance.tipoSolicitud_id = 23
        instance.dato_json = json.dumps(self._solicitud)
        instance.save()


# (ChrGil 2022-03-25) Corregir información de un nuevo representante legal
class CorregirNuevoRepresentanteLegal(RetrieveUpdateAPIView):
    def retrieve(self, request, *args, **kwargs):
        try:
            solicitud_id: int = self.request.query_params['solicitud_id']

            detail = ComponentDetailNewRepresentanteLegal(solicitud_id)
            return Response(detail.detail, status=status.HTTP_200_OK)

        except ValueError as e:
            err = MyHttpError('Ocurrio un error al ver detalles de esta solicitud', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            admin: persona = request.user
            solicitud_id: int = self.request.query_params['solicitud_id']

            with atomic():
                request_data = RequestDataAmendNewRepresentanteLegal(request.data)
                solicitud = ComponentGetInfoSolicitud(solicitud_id)

                ComponentCorregirNuevoRepresentanteLegal(request_data, solicitud)
                ComponentCorregirDomicilioFiscalNuevoRepresentanteLegal(request_data, solicitud)
                ComponentAmendDocumentsNewRepresentanteLegal(request_data, solicitud)

                ComponentSolicitudDevueltaNuevoRepresentante(admin, solicitud_id, solicitud, request_data)

        except (TypeError, ValueError, TypeError) as e:
            message = 'Ocurrio un error durante el proceso de corrección de su centro de costos'
            err = MyHttpError(message=message, real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            err = MyHttpError(message='Recurso no encontrado', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)
        else:
            msg = "Tu correción ha sido enviada satisfactoriamente y ha quedado en proceso de verificación."
            return Response(MyHtppSuccess(msg).standard_success_responses(), status=status.HTTP_200_OK)


class RequestDataCostCenter:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_razon_social(self) -> Dict[str, Any]:
        return self._request_data.get('RazonSocial').get('data')

    @property
    def get_razon_social_domicilio(self) -> Dict[str, Any]:
        return self._request_data.get('RazonSocial').get('DomicilioFiscal')

    @property
    def get_razon_social_documents(self) -> List[Dict[str, Any]]:
        return self._request_data.get('RazonSocial').get('Documentos')

    @property
    def get_representante_legal(self) -> Dict[str, Any]:
        return self._request_data.get('RepresentanteLegal').get('data')

    @property
    def get_representante_legal_domicilio(self) -> Dict[str, Any]:
        return self._request_data.get('RepresentanteLegal').get('DomicilioFiscal')

    @property
    def get_representante_legal_documents(self) -> List[Dict[str, Any]]:
        return self._request_data.get('RepresentanteLegal').get('Documentos')


class ComponentGetInfoCostCenter:
    info: ClassVar[Dict[str, Any]]

    def __init__(self, cost_center_id: int):
        self._cost_center_id = cost_center_id
        self.info = self._get_info_cost_center
        self._raise_error()

    def _raise_error(self):
        if self.info is None:
            raise ValidationError('Este centro de costos ya fue autorizado')

    @property
    def _get_info_cost_center(self) -> Union[Dict[str, Any], None]:
        return grupoPersona.objects.filter(
            empresa_id=self._cost_center_id,
            relacion_grupo_id=4,
            empresa__state=False,
        ).values(
            'empresa_id',
            'empresa__name',
            'person_id',
            'person__name'
        ).first()


class ComponentCorregirRazonSocial:
    _serializer_class: ClassVar[SerializerAmendRazonSocial] = SerializerAmendRazonSocial

    def __init__(self, request_data: RequestDataCostCenter, cost_center: ComponentGetInfoCostCenter):
        self._request_data = request_data
        self._cost_center = cost_center
        self._amend()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "cost_center_id": self._cost_center.info.get('empresa_id')
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return self._request_data.get_razon_social

    @staticmethod
    def _render_data(**kwargs):
        return {
            "cost_center_name": kwargs.get('CentroCosto'),
            "cost_center_razon_social": kwargs.get('RazonSocial'),
            "rfc": kwargs.get('rfc'),
            # "banco": kwargs.get('Banco'),
            # "clave_traspaso": kwargs.get('ClaveTraspaso'),
        }

    def _amend(self):
        serializer = self._serializer_class(data=self._render_data(**self._data), context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.amend()


class ComponentCorregirDomicilioFiscalRazonSocial:
    _serializer_class: ClassVar[SerializerCorregirAddress] = SerializerCorregirAddress

    def __init__(self, request_data: RequestDataCostCenter, cost_center: ComponentGetInfoCostCenter):
        self._request_data = request_data
        self._cost_center = cost_center
        self._amend()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "person_id": self._cost_center.info.get('empresa_id')
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return self._request_data.get_razon_social_domicilio

    @staticmethod
    def _render_data(**kwargs):
        return {
            "codigopostal": kwargs.get("CodigoPostal"),
            "colonia": kwargs.get("Colonia"),
            "alcaldia_mpio": kwargs.get("Municipio"),
            "estado": kwargs.get("Estado"),
            "calle": kwargs.get("Calle"),
            "pais": kwargs.get("Pais"),
            "no_exterior": kwargs.get("NoExterior"),
            "no_interior": kwargs.get("NoInterior"),
        }

    def _amend(self):
        serializer = self._serializer_class(data=self._render_data(**self._data), context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.amend()


class ComponentCorregirDomicilioFiscalRepresentanteLegal:
    _serializer_class: ClassVar[SerializerCorregirAddress] = SerializerCorregirAddress

    def __init__(self, request_data: RequestDataCostCenter, cost_center: ComponentGetInfoCostCenter):
        self._request_data = request_data
        self._cost_center = cost_center
        self._amend()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "person_id": self._cost_center.info.get('person_id')
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return self._request_data.get_representante_legal_domicilio

    @staticmethod
    def _render_data(**kwargs):
        return {
            "codigopostal": kwargs.get("CodigoPostal"),
            "colonia": kwargs.get("Colonia"),
            "alcaldia_mpio": kwargs.get("Municipio"),
            "estado": kwargs.get("Estado"),
            "calle": kwargs.get("Calle"),
            "pais": kwargs.get("Pais"),
            "no_exterior": kwargs.get("NoExterior"),
            "no_interior": kwargs.get("NoInterior"),
        }

    def _amend(self):
        serializer = self._serializer_class(data=self._render_data(**self._data), context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.amend()


class ComponentCorregirRepresentanteLegal:
    _serializer_class: ClassVar[SerializerAmendRepresentanteLegal] = SerializerAmendRepresentanteLegal

    def __init__(self, request_data: RequestDataCostCenter, cost_center: ComponentGetInfoCostCenter):
        self._request_data = request_data
        self._cost_center = cost_center
        self._amend()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "representate_id": self._cost_center.info.get('person_id')
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return self._request_data.get_representante_legal

    @staticmethod
    def _render_data(**kwargs):
        return {
            "nombre": kwargs.get('Nombre'),
            "paterno": kwargs.get('ApellidoPaterno'),
            "materno": kwargs.get('ApellidoMaterno'),
            "nacimiento": kwargs.get('FechaNacimiento'),
            "rfc": kwargs.get('rfc'),
            "homoclave": get_homoclave(kwargs.get('rfc')),
            "email": kwargs.get('CorreoElectronico'),
            "telefono": kwargs.get('NumeroTelefonico'),
        }

    def _amend(self):
        serializer = self._serializer_class(data=self._render_data(**self._data), context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.amend()


class ComponentSolicitudDevuelta:
    def __init__(
            self,
            request_data: RequestDataCostCenter,
            cost_center: ComponentGetInfoCostCenter,
            solicitud_id: int,
            admin: persona
    ):
        self._request_data = request_data
        self._cost_center = cost_center
        self._solicitud_id = solicitud_id
        self._admin = admin
        self._update_solicitud()

    @property
    def _payload(self):
        return {
            "cost_center_id": self._cost_center.info.get('empresa_id'),
            "name": self._cost_center.info.get('empresa__name'),
        }

    def _update_solicitud(self):
        instance: Solicitudes = Solicitudes.objects.get(id=self._solicitud_id)
        instance.intentos += 1
        instance.estado_id = 1
        instance.dato_json = json.dumps(self._payload)
        instance.fechaChange = datetime.datetime.now()
        instance.personChange_id = self._admin.get_only_id()
        instance.tipoSolicitud_id = 15
        instance.save()


# (ChrGil 2022-03-06) Corregir Documentos razon social
class ComponentAmendDocumentsRazonSocial:
    _serializer_class: ClassVar[SerializerAmendDocumentsCostCenter] = SerializerAmendDocumentsCostCenter

    def __init__(self, request_data: RequestDataCostCenter, cost_center: ComponentGetInfoCostCenter):
        self._request_data = request_data
        self._cost_center = cost_center
        self._amend_documents()

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "document_id": kwargs.get('DocumentId'),
            "owner": self._cost_center.info.get('empresa_id'),
            "base64_file": kwargs.get('Documento')
        }

    def _amend_documents(self):
        for document in self._request_data.get_razon_social_documents:
            serializer = self._serializer_class(data=self._data(**document))
            serializer.is_valid(raise_exception=True)
            serializer.amend()


# (ChrGil 2022-03-06) Corregir Documentos representante legal
class ComponentAmendDocumentsRepresentanteLegal:
    _serializer_class: ClassVar[SerializerAmendDocumentsCostCenter] = SerializerAmendDocumentsCostCenter

    def __init__(self, request_data: RequestDataCostCenter, cost_center: ComponentGetInfoCostCenter):
        self._request_data = request_data
        self._cost_center = cost_center
        self._amend_documents()

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "document_id": kwargs.get('DocumentId'),
            "owner": self._cost_center.info.get('person_id'),
            "base64_file": kwargs.get('Documento')
        }

    def _amend_documents(self):
        for document in self._request_data.get_representante_legal_documents:
            serializer = self._serializer_class(data=self._data(**document))
            serializer.is_valid(raise_exception=True)
            serializer.amend()


class CorregirAperturaCostCenter(UpdateAPIView):

    def update(self, request, *args, **kwargs):
        try:
            admin: persona = request.user
            cost_center_id: int = self.request.query_params['cost_center_id']
            solicitud_id: int = self.request.query_params['solicitud_id']

            with atomic():
                request_data = RequestDataCostCenter(request.data)
                cost_center = ComponentGetInfoCostCenter(cost_center_id)

                ComponentCorregirRazonSocial(request_data, cost_center)
                ComponentCorregirDomicilioFiscalRazonSocial(request_data, cost_center)
                ComponentAmendDocumentsRazonSocial(request_data, cost_center)

                ComponentCorregirRepresentanteLegal(request_data, cost_center)
                ComponentCorregirDomicilioFiscalRepresentanteLegal(request_data, cost_center)
                ComponentAmendDocumentsRepresentanteLegal(request_data, cost_center)

                ComponentSolicitudDevuelta(request_data, cost_center, solicitud_id, admin)

        except (ValueError, IntegrityError) as e:
            message = 'Ocurrio un error durante el proceso de corrección de su centro de costos'
            err = MyHttpError(message=message, real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            err = MyHttpError(message='Recurso no encontrado', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)
        else:
            msg = "Tu correción ha sido enviada satisfactoriamente y ha quedado en proceso de verificación."
            return Response(MyHtppSuccess(msg).standard_success_responses(), status=status.HTTP_200_OK)


class RequestDataDeleteCostCenter:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_motivo(self) -> str:
        return self._request_data.get('motivo')

    @property
    def get_documento(self) -> List[Dict[str, Any]]:
        return self._request_data.get('ComprobanteDocumento')


class ComponentDeleteCostCenter:
    _serializer_class: ClassVar[SerializerBajaCostCenter] = SerializerBajaCostCenter
    _create_documents: ClassVar[CreateDocuments] = CreateDocuments

    def __init__(self, cost_center_id: int, request_data: RequestDataDeleteCostCenter, cuenta_eje_id: int):
        self._cost_center_id = cost_center_id
        self._request_data = request_data
        self._cuenta_eje_id = cuenta_eje_id
        self._raise_error()
        self._delete_account()
        self._delete_person()
        self._delete_documents()
        self._delete_address()
        self._motivo()

    def _raise_error(self):
        if not persona.objects.filter(id=self._cost_center_id, state=True).exists():
            raise ValueError('No es posible eliminar este centro de costos')

        if not grupoPersona.objects.filter(empresa_id=self._cuenta_eje_id, relacion_grupo_id=5,
                                           person_id=self._cost_center_id).exists():
            raise ValueError('No fue posible eliminar el centro de costos')

    def _delete_account(self):
        cuenta.objects.filter(persona_cuenta_id=self._cost_center_id).update(is_active=False)

    def _delete_person(self):
        persona.objects.filter(
            id=self._cost_center_id).update(state=False, is_active=False, date_modify=datetime.datetime.now())

    def _delete_documents(self):
        documentos.objects.filter(
            person_id=self._cost_center_id).update(historial=True, dateupdate=datetime.datetime.now())

    def _delete_address(self):
        domicilio.objects.filter(domicilioPersona_id=self._cost_center_id).update(
            historial=True, dateUpdate=datetime.datetime.now())

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "cost_center_id": self._cost_center_id
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "motivo": self._request_data.get_motivo
        }

    def _motivo(self):
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.update()

    def upload_document(self):
        self._create_documents(self._cost_center_id, self._request_data.get_documento)


class DeleteCostCenter(UpdateAPIView):
    def update(self, request, *args, **kwargs):
        admin: persona = request.user
        cuenta_eje: int = get_id_cuenta_eje(admin.get_only_id())
        cost_center_id: int = request.query_params['cost_center_id']
        # admin: persona = persona.objects.get(id=6)

        try:
            with atomic():
                request_data = RequestDataDeleteCostCenter(request.data)
                ComponentDeleteCostCenter(cost_center_id, request_data, cuenta_eje)
        except (ValueError, ObjectDoesNotExist) as e:
            err = MyHttpError(message="Ocurrio un error al momento de elimiar un centro de costos", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            scc = MyHtppSuccess(message='Su operación se realizo de manera satisfactoria')
            return Response(scc.standard_success_responses(), status=status.HTTP_200_OK)


# (ChrGil 2021-12-08) Se comenta de manera temporal
# class UpdateCentroCostoDomicilioFiscalCC(GenericViewSet):
#     """ Actualiza domicilio fiscal """
#     permission_classes = (BlocklistPermissionV2,)
#     permisos = ["Editar centro de costo"]
#
#     serializer_class = SerializerDomicilioIn
#     serializer_class_solicitud = SerializerCrearSolicitudIn
#
#     def get_queryset(self, *args, **kwargs):
#         return get_Object_orList_error(*args, **kwargs)
#
#     def get(self, request):
#         """ Detallar domicilio fiscal, documentos """
#
#         instance_cc = self.get_queryset(persona, id=request.data['id'])
#         serializer = SerializerDetailCentroCostoOut(instance=instance_cc)
#         return Response(serializer.data, status=status.HTTP_200_OK)
#
#     def create(self):
#         pass
#
#     def put(self, request):
#         """
#         Creación de solicitud de cambio de domicilio fiscal
#
#         """
#
#         centro_costos_id = request.query_params['id']  # 504
#         get_centro_costos = get_Object_orList_error(grupoPersona, empresa_id=centro_costos_id)
#
#         querys = domicilio.objects.select_related('domicilioPersona').filter(
#             domicilioPersona_id=get_centro_costos.empresa_id)
#         for i in querys:
#             querys.update(historial=True, dateUpdate=datetime.datetime.now())
#
#         context = {'empresa_id': get_centro_costos.empresa_id}
#         serializer = self.serializer_class(data=request.data, context=context)
#         serializer.is_valid(raise_exception=True)
#         serializer.create()
#
#         context = {
#             'centro_costos_id': get_centro_costos.empresa_id,
#             'tipo_solicitud': 4,
#             'nombre': 'Cambio domicilio fiscal'
#         }
#
#         serializer = self.serializer_class_solicitud(data=request.data, context=context)
#         serializer.is_valid(raise_exception=True)
#         serializer.create()
#
#         return Response(
#             {'status': 'Tu solicitud ha sido enviada satisfactoriamente y ha quedado en proceso de verificación'},
#             status=status.HTTP_201_CREATED)

# (ChrGil 2021-12-08) Se comenta de manera temporal
# class BajaCentroCostoCliente(GenericViewSet):
#     """
#     Crear solicitud para Baja de centro de costo de lado del cliente
#
#     """
#
#     permission_classes = (BlocklistPermissionV2,)
#     permisos = ["Eliminar centro de costo"]
#
#     serializer_class = SerializerCrearSolicitudIn
#
#     def create(self, request):
#         """ Enviar solicitud de baja Cliente """
#
#         context = {
#             'centro_costos_id': request.query_params['id'],
#             'tipo_solicitud': 2,
#             'nombre': 'Baja de Centro de Costos'
#         }
#
#         serializer = self.serializer_class(data=request.data, context=context)
#         serializer.is_valid(raise_exception=True)
#         serializer.create()
#
#         return Response(
#             {'status': 'Tu solicitud ha sido enviada satisfactoriamente y ha quedado en proceso de verificación'},
#             status=status.HTTP_201_CREATED)


""" - - - - - - L i s t a r   c e n t r o   d e   c o s t o s - - - - - - """


# (ManuelCalixtro 29-11-2021) lista centros de costos con filtro por nombre y estado de solicitud por apertura}


class ListCostCenterFilter(ListAPIView):
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Ver centros de costo"]
    permission_classes = ()

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        empresa = self.request.query_params['empresa_id']
        nombre = self.request.query_params['nombre']
        estado = self.request.query_params['estado']
        date1 = self.request.query_params['start_date']
        date2 = self.request.query_params['end_date']

        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size

        s = Solicitudes.objects.filter(
            personaSolicitud_id=empresa,
            tipoSolicitud_id__in=[15, 16, 17, 18, 19, 20, 21, 22, 23],
            # estado_id=estado
        ).values(
            'id',
            'dato_json',
            'estado__nombreEdo',
            'tipoSolicitud_id',
            'tipoSolicitud__nombreSol',
            'intentos',
            'fechaSolicitud'
        ).order_by('-fechaChange')

        for i in s:
            i["data"] = json.loads(i.pop('dato_json'))

        page = self.paginate_queryset(s)
        return self.get_paginated_response(page)


class ListarCentroCosto(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver centros de costo"]
    serializer_class = SerialiazerListarCentroCostos
    pagination_class = PageNumberPagination

    def get_queryset(self, *args, **kwargs):
        return filter_data_or_return_none(*args, **kwargs)

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size

        queryset = grupoPersona.objects.filter(empresa_id=self.request.query_params['id'], relacion_grupo_id=3)
        page = self.paginate_queryset(queryset)

        serializer = self.serializer_class(page, many=True)
        return self.get_paginated_response(serializer.data)


class GetCentroCostos(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver detalles de centro de costo", "Editar centro de costo"]

    serializer_class = SerializerListCentroCostosOut
    serializer_class_update = SerializerGetCenterCostOut

    def list(self, request):
        pk_centro_costos = self.request.query_params["id"]
        instance_grupo_persona = filter_Object_Or_Error(grupoPersona, empresa_id=pk_centro_costos,
                                                        relacion_grupo_id=4).last()
        instance = persona.objects.filter(id=instance_grupo_persona.empresa_id)
        # serializer = self.serializer_class(instance,many=True,context=instance_grupo_persona)
        serializer = self.serializer_class(instance, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        pk_Centro_Costos = self.request.query_params["id"]
        instance_grupo_persona = get_Object_orList_error(grupoPersona, empresa_id=pk_Centro_Costos, relacion_grupo_id=4)
        instance = get_Object_orList_error(persona, id=instance_grupo_persona.empresa_id)
        serializer = self.serializer_class_update(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update_centroCostos(instance)
            return Response({"status": "Centro de costo actualizado"}, status=status.HTTP_200_OK)


# P0l1m3nt3s#B4ck3ndXYZ.20210101_
# P0l1m3nt3s#M0v1l3sXYZA.20210101_
# P0l1m3nt3s#B4ck3ndXYZ.20210101_

### editar centro de costos # (AAF 2021-12-08)

class updateCentroCostos(GenericViewSet):
    # permission_classes = ()
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Editar centro de costo"]
    serializer_class = SerializerCC
    serializer_RL = CCRepresentanteLegalIn
    serializer_document = SerializerDocumentIn

    # solo administrador polipay, administrativos y colaboradores

    def create(self, request):
        pass

    def put(self, request):
        listaResponse = []
        # token = verificar_token()
        # if token != True:
        #     return Response({"status": "Centro de costo actualizado"}, status=status.HTTP_200_OK)
        # print(request.data)
        if 'centroCostoDetail' in request.data:  # si envia detalles del centro de costo los actualizamos
            serializer = self.serializer_class(data=request.data['centroCostoDetail'])
            if serializer.is_valid():
                instanceCC = persona.objects.get(id=serializer.validated_data['id'])
                instanceCC = serializer.update(instanceCC, serializer.validated_data)
                listaResponse.append(instanceCC.name + " actualizado")
            else:
                listaResponse.append(" No actualizado centro de costos")
        if 'documentos_centro_costos' in request.data:
            for documento in request.data['documentos_centro_costos']:
                serializer = self.serializer_document(data=documento)
                if serializer.is_valid():
                    instanceD = serializer.update(serializer.validated_data)
                    listaResponse.append("documento actualizado " + str(instanceD.id))
                else:
                    listaResponse.append(
                        "problema al actualizar documento " + request.data['documentos_centro_costos']['id'])
        if 'representanteDetail' in request.data:
            serializer = self.serializer_RL(data=request.data['representanteDetail'])
            if serializer.is_valid():
                instanceRL = serializer.update(serializer.validated_data)
                listaResponse.append(instanceRL.name + " actualizado")
            else:
                listaResponse.append("Representante Legal no actualizado")
        if 'documento_representante' in request.data:
            for documento in request.data['documento_representante']:
                serializer = self.serializer_document(data=documento)
                if serializer.is_valid():
                    instanceD = serializer.update((serializer.validated_data))
                    listaResponse.append("documento actualizado " + str(instanceD.id))
                else:
                    listaResponse.append(
                        "problema al actualizar documento " + request.data['documentos_centro_costos']['id'])
        solIntento = Sumarsolicitud(instanceCC.id, 1)  # modificar la solicitud enviada previamente
        succ = MyHtppSuccess(message="solicitud recibida", extra_data=listaResponse)
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


## (AAF 2021-12-13) baja de centro de costos [PERMISOS: only access token ]
class SolDismissCC(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Eliminar centro de costo"]
    serializer_class = SerializerCreateSol
    serializer_document = SerializerDocumentIn

    # permission_classes = ()

    # usado por admin cliente y colaborador

    def create(self, request):
        listaResponse = []
        # verificarPersona
        try:
            CC = persona.objects.get(id=self.request.data['idCC']).get_id_and_name()
            personaSol = persona.objects.get(id=self.request.data['idPersonaSol']).get_id_and_name()
        except Exception as ex:
            err = MyHttpError(message="Persona o Centro de Costos no existe", real_error=str(ex))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        # guardar documento
        request.data['person_id'] = CC['id']
        serializer = self.serializer_document(data=request.data)
        if serializer.is_valid():
            doctoIns = serializer.create(serializer.validated_data, CC['id'])
            listaResponse.append(str(doctoIns.id) + " documento registrado")
        else:
            listaResponse.append("documento no registrado")
        # generarSolicitud
        solicitudData = {
            'nombre': request.data['comentario'],
            'tipoSolicitud_id': 1,
            'personaSolicitud_id': CC['id'],
            'referencia': {"solicita": personaSol['id']}
        }
        serializer = self.serializer_class(data=solicitudData)
        if serializer.is_valid():
            solInstance = serializer.create(serializer.validated_data, CC['id'])
            listaResponse.append(str(solInstance.id) + " solicitud de baja registrada")
        else:
            listaResponse.append("solicitud no registrada")
        # devolverSolicitud
        succ = MyHtppSuccess(message="solicitud recibida", extra_data=listaResponse)
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


# Manuel_CL(27/12/2021, se creo listado para obtener el numero de cuenta de un centro de costos de una cuenta eje)
class GetCostCenter(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver centros de costo"]

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        empresa_id = self.request.query_params['cuenta_eje']
        get_cost_center = grupoPersona.objects.get_list_actives_cost_centers_id(empresa_id)
        get_request_cost_center = cuenta.objects.filter_account_cost_center(get_cost_center)
        return Response(get_request_cost_center)


class RequestDataUpdateDocumentsDomicilioFiscal:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_documents_list(self) -> List[Dict[str, Any]]:
        return self._request_data.get('DocumentsDomicilioFiscal')


class ComponentCreateDocuments:
    _serializer_class: ClassVar[SerializerCreateDocumentSolicitud] = SerializerCreateDocumentSolicitud

    def __init__(self, request_data: RequestDataUpdateDocumentsDomicilioFiscal, person_id: int):
        self._request_data = request_data
        self._cost_center_id = person_id
        self._create()

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "tipo": kwargs.get('TipoDocumentoId'),
            "owner": self._cost_center_id,
            "base64_file": kwargs.get('documento')
        }

    def _create(self):
        for document in self._request_data.get_documents_list:
            serializer = self._serializer_class(data=self._data(**document))
            serializer.is_valid(raise_exception=True)
            serializer.create()


# (ManuelCalixtro 2022-10-03) Se creo endpoint para la solicitud de cambio de domicilio fiscal
class SolicitudEditarDomicilioFiscal(GenericViewSet):
    serializer_class = SerializerSolicitudEditarDomicilioFiscal

    def create(self, request):
        cost_center_id = self.request.query_params['cost_center_id']
        user: persona = self.request.user
        cuenta_eje_id: int = get_id_cuenta_eje(user.get_only_id())
        cost_center = grupoPersona.objects.filter(empresa_id=cost_center_id, relacion_grupo_id=4).values('empresa_id',
                                                                                                         'empresa__name').first()

        request_data = RequestDataUpdateDocumentsDomicilioFiscal(request.data)
        ComponentCreateDocuments(request_data, cost_center_id)

        context = {
            'PersonaSolicitudId': cuenta_eje_id,
            'cost_center_info': cost_center,
            'admin': user
        }

        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.create(serializer.validated_data)
        success = MyHtppSuccess(
            'Tu solicitud ha sido enviada satisfactoriamente y ha quedado en proceso de verificacion')
        return Response(success.standard_success_responses(), status=status.HTTP_200_OK)


class RequestDataEditClabeTraspaso:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_documents_list(self) -> List[Dict[str, Any]]:
        return self._request_data.get('DocumentsClaveTraspasoFinal')


class ComponentCreateDocumentsClabeTraspaso:
    _serializer_class: ClassVar[SerializerCreateDocumentSolicitud] = SerializerCreateDocumentSolicitud

    def __init__(self, request_data: RequestDataEditClabeTraspaso, person_id: int):
        self._request_data = request_data
        self._cost_center_id = person_id
        self._create()

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "tipo": kwargs.get('TipoDocumentoId'),
            "owner": self._cost_center_id,
            "base64_file": kwargs.get('documento')
        }

    def _create(self):
        for document in self._request_data.get_documents_list:
            serializer = self._serializer_class(data=self._data(**document))
            serializer.is_valid(raise_exception=True)
            serializer.create()


# (ManuelCalixtro 2022-10-03) Se creo endpoint para la solicitud de cambio de traspaso final
class SolicitudEditarClaveTraspasoFinal(GenericViewSet):
    serializer_class = SerializerEditarClaveTraspasoFinal

    def create(self, request):
        try:
            cost_center_id = self.request.query_params['cost_center_id']
            user: persona = self.request.user
            cuenta_eje_id: int = get_id_cuenta_eje(user.get_only_id())
            centro_costos = grupoPersona.objects.filter(empresa_id=cost_center_id, relacion_grupo_id=4).values(
                'empresa_id', 'empresa__name').first()

            with atomic():
                request_data = RequestDataEditClabeTraspaso(request.data)
                ComponentCreateDocumentsClabeTraspaso(request_data, cost_center_id)

                context = {
                    'PersonaSolicitudId': cuenta_eje_id,
                    'cost_center_info': centro_costos,
                    'admin':user
                }

                serializer = self.serializer_class(data=request.data, context=context)
                serializer.is_valid(raise_exception=True)
                serializer.create(serializer.validated_data)
                success = MyHtppSuccess(
                    'Tu solicitud ha sido enviada satisfactoriamente y ha quedado en proceso de verificacion')
                return Response(success.standard_success_responses(), status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            err = MyHttpError(message='Recurso no encontrado', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)


class RequestDataAmentClabeTraspaso:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_documents_list(self) -> List[Dict[str, Any]]:
        return self._request_data.get('DocumentsClaveTraspasoFinal')


class AmentDocumentsClaveTraspaso:
    _serializer_class: ClassVar[SerializerAmentDocumentsClaveTraspaso] = SerializerAmentDocumentsClaveTraspaso

    def __init__(self, request_data: RequestDataAmentClabeTraspaso, person_id: int):
        self._request_data = request_data
        self._person_id = person_id
        self._amend_documents()

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "document_id": kwargs.get('DocumentId'),
            "owner": self._person_id,
            "base64_file": kwargs.get('documento')
        }

    def _amend_documents(self):
        for document in self._request_data.get_documents_list:
            serializer = self._serializer_class(data=self._data(**document))
            serializer.is_valid(raise_exception=True)
            serializer.amend()


# (ManuelCalixtro 2022-10-03) Endpoint para corregir clave traspaso final
class AmendClaveTraspasoFinal(GenericViewSet):
    serializer_class = SerializerAmentClaveTraspasoFinal

    def create(self, request):
        pass

    def put(self, request, *args, **kwargs):
        try:
            cost_center_id = self.request.query_params['cost_center_id']
            solicitud_id = self.request.query_params['solicitud_id']
            user: persona = self.request.user
            cuenta_eje_id: int = get_id_cuenta_eje(user.get_only_id())
            centro_costos = grupoPersona.objects.filter(empresa_id=cost_center_id, relacion_grupo_id=4).values(
                'empresa_id', 'empresa__name').first()

            instance: Solicitudes = Solicitudes.objects.get(id=solicitud_id, tipoSolicitud_id=21)

            with atomic():

                request_data = RequestDataAmentClabeTraspaso(request.data)
                AmentDocumentsClaveTraspaso(request_data, cost_center_id)

                context = {
                    'PersonaSolicitudId': cuenta_eje_id,
                    'CostCenterInfo': centro_costos,
                    'EstadoSolicitudId': instance.estado.id

                }
                serializer = self.serializer_class(data=request.data, context=context)
                serializer.is_valid(raise_exception=True)
                serializer.update(instance, serializer.validated_data)
                success = MyHtppSuccess(
                    'Tu solicitud ha sido enviada satisfactoriamente y ha quedado en proceso de verificacion')
                return Response(success.standard_success_responses(), status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            err = MyHttpError(message='Recurso no encontrado', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except ObjectDoesNotExist as e:
            err = MyHttpError(message='Recurso no encontrado', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)


class RequestDataAmentDocumentsDomicilioFiscal:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_documents_list(self) -> List[Dict[str, Any]]:
        return self._request_data.get('DocumentsDomicilioFiscal')


class AmentDocumentsDomicilioFiscal:
    _serializer_class: ClassVar[SerializerAmentDocumentsDomicilioFiscal] = SerializerAmentDocumentsDomicilioFiscal

    def __init__(self, request_data: RequestDataAmentDocumentsDomicilioFiscal, person_id: int):
        self._request_data = request_data
        self._person_id = person_id
        self._amend_documents()

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "document_id": kwargs.get('DocumentId'),
            "owner": self._person_id,
            "base64_file": kwargs.get('documento')
        }

    def _amend_documents(self):
        for document in self._request_data.get_documents_list:
            serializer = self._serializer_class(data=self._data(**document))
            serializer.is_valid(raise_exception=True)
            serializer.amend()


class AmendDomicilioFiscal(GenericViewSet):
    # permission_classes = ()
    serializer_class = SerializerAmentDomFiscal

    def create(self, request):
        pass

    def put(self, request, *args, **kwargs):
        try:
            cost_center_id = self.request.query_params['cost_center_id']
            solicitud_id = self.request.query_params['solicitud_id']
            user: persona = self.request.user
            # user: persona = persona.objects.get(id=6)
            cuenta_eje_id: int = get_id_cuenta_eje(user.get_only_id())
            centro_costos = grupoPersona.objects.filter(empresa_id=cost_center_id, relacion_grupo_id=4).values(
                'empresa_id', 'empresa__name').first()

            instance: Solicitudes = Solicitudes.objects.get(id=solicitud_id, tipoSolicitud_id=19)

            with atomic():

                request_data = RequestDataAmentDocumentsDomicilioFiscal(request.data)
                AmentDocumentsDomicilioFiscal(request_data, cost_center_id)

                context = {
                    'PersonaSolicitudId': cuenta_eje_id,
                    'CostCenterInfo': centro_costos,
                    'EstadoSolicitudId': instance.estado.id

                }
                serializer = self.serializer_class(data=request.data, context=context)
                serializer.is_valid(raise_exception=True)
                serializer.update(instance, serializer.validated_data)

                msg = 'Tu solicitud ha sido enviada satisfactoriamente y ha quedado en proceso de verificacion'
                return Response(MyHtppSuccess(msg).standard_success_responses(), status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            err = MyHttpError(message='Recurso no encontrado', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except ValueError as e:
            err = MyHttpError(message='Ocurrio un error al corregir su información', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


class ComponentGetInfoRepresentanteLegal:
    def __init__(self, cost_center_id: int):
        self._cost_center_id = cost_center_id
        self.representante_legal_id = self._get_info_representante_legal.get('person_id')
        self.cost_center = self._get_info_representante_legal

        if self.representante_legal_id is None:
            raise ValueError('Centro de costos no valido o no existe')

    @property
    def _get_info_representante_legal(self) -> Dict[str, Any]:
        return grupoPersona.objects.filter(
            empresa_id=self._cost_center_id
        ).values('person_id', 'empresa_id', 'empresa__name').first()


class RequestDataRepresentanteLegal:
    info_cliente: ClassVar[Dict[str, Any]]
    info_cost_center: ClassVar[Dict[str, Any]]

    def __init__(self, request_data: Dict[str, Any], representante: ComponentGetInfoRepresentanteLegal):
        self._request_data = request_data
        self._representante = representante
        self.info_cliente = self.get_cliente_and_domicilio()

    def get_cliente_and_domicilio(self) -> Dict[str, Any]:
        return {
            "cost_center_id": self._representante.cost_center.get('empresa_id'),
            "name": self._representante.cost_center.get('empresa__name'),
            "person_info": self.get_info_client,
            "person_dom": self.get_domicilio,
            "representante_legal_id": self._representante.representante_legal_id
        }

    @property
    def get_info_representante_legal(self) -> Dict[str, Any]:
        return self._request_data.get('representante_legal')

    @property
    def get_info_client(self) -> Dict[str, Any]:
        return {
            "name": self.get_info_representante_legal.get('name'),
            "paterno": self.get_info_representante_legal.get('first_last_name'),
            "materno": self.get_info_representante_legal.get('second_last_name'),
            "fecha_nacimiento": self.get_info_representante_legal.get('fecha_nacimiento'),
            "rfc": self.get_info_representante_legal.get('rfc'),
            "email": self.get_info_representante_legal.get('email'),
            "phone": self.get_info_representante_legal.get('phone'),
        }

    @property
    def get_domicilio_representante_legal(self) -> Dict[str, Any]:
        return self._request_data.get('domicilio_representante_legal')

    @property
    def get_domicilio(self) -> Dict[str, Any]:
        return {
            "codigopostal": self.get_domicilio_representante_legal.get('codigopostal'),
            "colonia": self.get_domicilio_representante_legal.get('colonia'),
            "alcaldia_mpio": self.get_domicilio_representante_legal.get('alcaldia_mpio'),
            "estado": self.get_domicilio_representante_legal.get('estado'),
            "calle": self.get_domicilio_representante_legal.get('calle'),
            "no_exterior": self.get_domicilio_representante_legal.get('no_exterior'),
            "no_interior": self.get_domicilio_representante_legal.get('no_interior'),
        }

    @property
    def get_documents_list(self) -> List[Dict[str, Any]]:
        return self._request_data.get('DocumentsRepresentanteLegal')


class ComponentCreateDocumentsRepresentanteLegal:
    _serializer_class: ClassVar[SerializerCreateDocumentRepresentanteLegal] = SerializerCreateDocumentRepresentanteLegal
    documents_list_id: ClassVar[List[int]]

    def __init__(self, request_data: RequestDataRepresentanteLegal, person_id: int):
        self._request_data = request_data
        self._cost_center_id = person_id
        self.documents_list_id = []
        self._create()

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "tipo": kwargs.get('TipoDocumentoId'),
            "owner": self._cost_center_id,
            "base64_file": kwargs.get('documento')
        }

    def _create(self):
        for document in self._request_data.get_documents_list:
            serializer = self._serializer_class(data=self._data(**document))
            serializer.is_valid(raise_exception=True)
            self.documents_list_id.append(serializer.create())


class AltaRepresentanteLegal(GenericViewSet):
    serializer_class = SerializerAltaRepresentanteLegal

    def create(self, request):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.data)
            centro_costos_id = self.request.query_params['centro_costos_id']
            user: persona = self.request.user
            cuenta_eje_id: int = get_id_cuenta_eje(user.get_only_id())

            with atomic():
                representante_legal = ComponentGetInfoRepresentanteLegal(centro_costos_id)
                request_data = RequestDataRepresentanteLegal(request.data, representante_legal)
                documents = ComponentCreateDocumentsRepresentanteLegal(request_data, centro_costos_id)

                context = {
                    'PersonaSolicitudId': cuenta_eje_id,
                    'info_representante_legal': request_data.info_cliente,
                    "documents_list": documents.documents_list_id
                }

                data = request.data
                serializer = self.serializer_class(data=request.data, context=context)
                serializer.validate_email(data['representante_legal']['email'])
                serializer.is_valid(raise_exception=True)
                serializer.create(serializer.data)

                msg = "Tu solicitud ha sido enviada satisfactoriamente y ha quedado en proceso de verificacion"
                log.json_response(MyHtppSuccess(message=msg).standard_success_responses())
                return Response(MyHtppSuccess(message=msg).standard_success_responses(), status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            err = MyHttpError(message='Recurso no encontrado', real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except ValueError as e:
            err = MyHttpError(message='Ocurrio un error al enviar la solicitud', real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


class ComponentListCostCenter:
    data: ClassVar[List[Dict[str, Any]]]
    defaul_size: ClassVar[int] = 5

    def __init__(self, **kwargs):
        self._cuenta_eje_id = kwargs.get("cuenta_eje_id")
        self._name = kwargs.get("name", '')
        self.size = kwargs.get("size", self.defaul_size)
        self._start_date = kwargs.get('start_date', datetime.date.today() - datetime.timedelta(days=91))
        self._end_date = kwargs.get('end_date', datetime.date.today())
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
            Q(persona_cuenta__date_joined__date__gte=self._start_date) &
            Q(persona_cuenta__date_joined__date__lte=self._end_date)
        ).filter(
            persona_cuenta_id__in=self._get_cost_center_active,
            is_active=True,
            persona_cuenta__name__icontains=self._name
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
class ListCostCenterActiveClient(ListAPIView):
    pagination_class = PageNumberPagination

    # PARAMS: cuenta_eje, size, name, start_date, end_date
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.query_params)
            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
            const_center_list = ComponentListCostCenter(**data)

            for query in const_center_list.data:
                log.json_response(query)

            self.pagination_class.page_size = const_center_list.size
            return self.get_paginated_response(self.paginate_queryset(const_center_list.data))

        except (ObjectDoesNotExist, ValueError) as e:
            err = MyHttpError('Ocurrio un error al listar los centros de costos', real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


class ComponentListCostCenterSolicitudes:
    _default_size: ClassVar[int] = 5
    _default_state: ClassVar[int] = [1, 2, 3]
    queryset: ClassVar[List[Dict[str, Any]]]

    def __init__(self, **kwargs):
        self._cuenta_eje_id = kwargs.get('cuenta_eje_id')
        self.size = kwargs.get('size', self._default_size)
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
            tipoSolicitud_id__in=[15, 16, 17, 18, 19, 20, 21, 22, 23],
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
        list_cost_center = []

        if isinstance(self._state, str):
            list_cost_center = self._list(estado_id=self._state)

        if isinstance(self._state, list):
            list_cost_center = self._list(estado_id__in=self._state)

        for row in list_cost_center:
            if row.get('dato_json'):
                row.update({'dato_json': json.loads(row.get('dato_json'))})
        return list_cost_center


# (ChrGil 2022-03-10) Listar centros de costos activos de lado del admin
class ListSolicitudesCostCenterClient(ListAPIView):
    pagination_class = PageNumberPagination

    # PARAMS: cuenta_eje, size, state_id, start_date, end_date
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.query_params)
            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
            const_center_list = ComponentListCostCenterSolicitudes(**data)

            self.pagination_class.page_size = const_center_list.size
            return self.get_paginated_response(self.paginate_queryset(const_center_list.queryset))

        except (ObjectDoesNotExist, ValueError) as e:
            err = MyHttpError('Ocurrio un error al listar los centros de costos', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


# (ChrGil 2022-03-25) Solo se crea el archivo y se agrega el motivo
class ComponentDeleteRepresentanteLegal:
    _serializer_class: ClassVar[SerializerBajaCostCenter] = SerializerBajaCostCenter
    _create_documents: ClassVar[CreateDocuments] = CreateDocuments

    def __init__(self, cost_center_id: int, request_data: RequestDataDeleteCostCenter):
        self._cost_center_id = cost_center_id
        self._request_data = request_data
        self._raise_error()
        self._motivo()

    def _raise_error(self):
        if not persona.objects.filter(id=self._cost_center_id, state=True).exists():
            raise ValueError('No es posible eliminar este centro de costos')

        if not grupoPersona.objects.filter(empresa_id=self._cost_center_id, relacion_grupo_id=4).exists():
            raise ValueError('No fue posible eliminar el centro de costos')

    @property
    def _get_cost_center(self) -> Dict[str, Any]:
        return grupoPersona.objects.filter(
            empresa_id=self._cost_center_id, relacion_grupo_id=4).values('person_id').first()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "cost_center_id": self._get_cost_center.get('person_id')
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "motivo": self._request_data.get_motivo
        }

    def _motivo(self):
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.update()

    def upload_document(self):
        self._create_documents(self._cost_center_id, self._request_data.get_documento)


class DeleteRepresentanteLegal(UpdateAPIView):
    def update(self, request, *args, **kwargs):
        admin: persona = request.user
        cost_center_id: int = request.query_params['cost_center_id']
        log = RegisterLog(request.user, request)

        try:
            with atomic():
                log.json_request(request.data)
                request_data = RequestDataDeleteCostCenter(request.data)
                ComponentDeleteRepresentanteLegal(cost_center_id, request_data)
        except (ValueError, ObjectDoesNotExist) as e:
            err = MyHttpError(message="Ocurrio un error al momento de elimiar un centro de costos", real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            scc = MyHtppSuccess(message='Su operación se realizo de manera satisfactoria')
            log.json_response(scc.standard_success_responses())
            return Response(scc.standard_success_responses(), status=status.HTTP_200_OK)



