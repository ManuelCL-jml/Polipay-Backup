import json
from dataclasses import dataclass
from typing import Dict, Any, ClassVar, List, NoReturn
from django.db import IntegrityError, OperationalError
from django.db.models import Q
from django.db.transaction import atomic
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, FieldDoesNotExist
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status, viewsets, pagination

from MANAGEMENT.AlgSTP.algorithm_stp import GenerateNewClabeSTP
from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from apps.users.api.web.cliente.serializers.serializer_cliente_externo import *
from apps.users.messages import send_email_access_extern_client
from apps.users.models import tarjeta


class RequestDataClienteFisico:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_cliente_fisico_detail(self) -> Dict[str, Any]:
        return self._request_data.get('InfoClienteExterno')

    @property
    def get_info_client(self) -> Dict[str, Any]:
        return {
            "name": self.get_cliente_fisico_detail.get('name'),
            "apellido_paterno": self.get_cliente_fisico_detail.get('apellido_paterno'),
            "apellido_materno": self.get_cliente_fisico_detail.get('apellido_materno'),
            "last_name": self.get_cliente_fisico_detail.get('last_name'),
            "rfc": self.get_cliente_fisico_detail.get('rfc'),
            "phone": self.get_cliente_fisico_detail.get('phone'),
            "email": self.get_cliente_fisico_detail.get('email'),
        }

    @property
    def get_list_documents(self) -> List[Dict[str, Any]]:
        return self._request_data.get('documentos_cliente')


# (ManuelCalixtro 13-06-2022) Componente para registrar un cliente fisico
class CreateClienteFisico:
    _serializer_class: ClassVar[SerializerClienteExternoFisico] = SerializerClienteExternoFisico
    person_instance: ClassVar[persona]

    def __init__(self, request_data: RequestDataClienteFisico):
        self._request_data = request_data
        self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return self._request_data.get_cliente_fisico_detail

    def _create(self):
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        self.person_instance = serializer.create()


# (ManuelCalixtro 13-06-2022) Componente para la creación de la cuenta del cliente fisico
class CreateAccountClienteFisico:
    _clabe: ClassVar[str]
    _default_product_id: ClassVar[int] = 2
    _serializer_class: ClassVar[SerializerCreateAccountClienteFisico] = SerializerCreateAccountClienteFisico
    person_instance: ClassVar[persona]

    def __init__(self, request_data: RequestDataClienteFisico, client: CreateClienteFisico, cost_center_id):
        self._request_data = request_data
        self._client = client
        self._cost_center_id = cost_center_id
        self._clabe = self._generate_clabe
        self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "person_id": self._client.person_instance.get_only_id(),
            "product_id": self._default_product_id,
            "clabe": self._clabe
        }

    @property
    def _generate_clabe(self) -> str:
        return GenerateNewClabeSTP(self._cost_center_id).clabe

    def _create(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        serializer.create()


# (ManuelCalixtro 13-06-2022) Componente para la creación de los documentos del cliente físico
class CreateDocumentsClienteFisico:
    _serializer_class: ClassVar[SerializerDocumentClienteExternoFisicoIn] = SerializerDocumentClienteExternoFisicoIn

    def __init__(self, request_data: RequestDataClienteFisico, client: CreateClienteFisico, admin):
        self._request_data = request_data
        self._person_id = client.person_instance.get_only_id()
        self._admin_id = admin.id
        self._create()

    @property
    def _data(self) -> List[Dict[str, Any]]:
        return self._request_data.get_list_documents

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "person_id": self._person_id,
            "user_authorize_id": self._admin_id
        }

    def _create(self) -> NoReturn:
        for document in self._data:
            serializer = self._serializer_class(data=document, context=self._context)
            serializer.is_valid(raise_exception=True)
            serializer.create()


# (ManuelCalixtro 13-06-2022) Crear relación grupo persona
class CreateRelationCostCenter:
    _default_name: ClassVar[str] = 'Cliente Externo Físico'
    _default_relacion_grupo_id: ClassVar[int] = 9

    def __init__(self, request_data: RequestDataClienteFisico, client: CreateClienteFisico, cost_center_id):
        self._request_data = request_data
        self._client = client
        self._cost_center_id = cost_center_id
        self._create()

    def _create(self) -> NoReturn:
        grupoPersona.objects.create(
            person_id=self._client.person_instance.get_only_id(),
            empresa_id=self._cost_center_id,
            nombre_grupo=self._default_name,
            relacion_grupo_id=self._default_relacion_grupo_id,
        )


# (ManuelCalixtro 13-06-2022) Crear cliente externo fisico
class CreateClienteExternoFisico(viewsets.GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear cliente externo"]

    def create(self, request):
        log = RegisterLog(request.user, request)
        cost_center_id = self.request.query_params['cost_center_id']
        try:
            with atomic():
                admin: persona = persona.objects.get(id=self.request.user.id)
                log.json_request(request.data)
                request_data = RequestDataClienteFisico(request.data)
                client = CreateClienteFisico(request_data)
                CreateDocumentsClienteFisico(request_data, client, admin)
                CreateRelationCostCenter(request_data, client, cost_center_id)
                CreateAccountClienteFisico(request_data, client, cost_center_id)
                send_email_access_extern_client(client.person_instance)

        except (ObjectDoesNotExist, IntegrityError, ValueError, TypeError) as e:
            err = MyHttpError(message="Ocurrió un error al momento de crear su cliente", real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            succ = MyHtppSuccess(message="Su operación se realizo satisfactoriamente", extra_data="")
            log.json_response(succ.standard_success_responses())
            return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


# (ManuelCalixtro 16-06-2022) Componente que solicita la informacion de  cliente externo fisico
class RequestDataUpdateClienteFisico:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_cliente_fisico_detail(self) -> Dict[str, Any]:
        return self._request_data.get('InfoClienteExterno')

    @property
    def get_info_client(self) -> Dict[str, Any]:
        return {
            "name": self.get_cliente_fisico_detail.get('name'),
            "apellido_paterno": self.get_cliente_fisico_detail.get('apellido_paterno'),
            "apellido_materno": self.get_cliente_fisico_detail.get('apellido_materno'),
            "last_name": self.get_cliente_fisico_detail.get('last_name'),
            "rfc": self.get_cliente_fisico_detail.get('rfc'),
            "phone": self.get_cliente_fisico_detail.get('phone'),
            "email": self.get_cliente_fisico_detail.get('email'),
        }

    @property
    def get_list_documents(self) -> List[Dict[str, Any]]:
        return self._request_data.get('documentos_cliente')


# (ManuelCalixtro 16-06-2022) Componente que edita la informacion de  cliente externo fisico
class ComponentUpdateClienteExterno:
    _serializer_class: ClassVar[SerializerUpdateExternoFisico] = SerializerUpdateExternoFisico
    person_instance: ClassVar[persona]

    def __init__(self, request_data: RequestDataUpdateClienteFisico, extern_client_id):
        self._request_data = request_data
        self._extern_client_id = extern_client_id
        self._person_instance = self._get_person
        self._update()

    @property
    def _data(self) -> Dict[str, Any]:
        return self._request_data.get_cliente_fisico_detail

    @property
    def _get_person(self) -> persona:
        return persona.objects.get(id=self._extern_client_id)

    def _update(self):
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        self.person_instance = serializer.update(self._person_instance)


# (ManuelCalixtro 16-06-2022) Componente que edita los documentos de  cliente externo fisico
class EditDocumentClienteExternoFisico:
    _serializer_class: ClassVar[
        SerializerEditDocumentClienteExternoFisico] = SerializerEditDocumentClienteExternoFisico

    def __init__(self, request_data: RequestDataUpdateClienteFisico, person_id: int):
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
        for document in self._request_data.get_list_documents:
            serializer = self._serializer_class(data=self._data(**document))
            serializer.is_valid(raise_exception=True)
            serializer.amend()


# (ManuelCalixtro 16-06-2022) Editar cliente externo fisico
class UpdateClienteExternoFisico(viewsets.GenericViewSet):
    permission_classes = ()

    def create(self):
        pass

    def put(self, request):
        extern_client_id = self.request.query_params['extern_client_id']
        instance = persona.objects.get(id=extern_client_id)
        try:
            with atomic():

                request_data = RequestDataUpdateClienteFisico(request.data)
                client = ComponentUpdateClienteExterno(request_data, extern_client_id)
                EditDocumentClienteExternoFisico(request_data, extern_client_id)

                if instance.email != client.person_instance.email:
                    send_email_access_extern_client(client.person_instance)

        except (ObjectDoesNotExist, IntegrityError, ValueError, TypeError) as e:
            err = MyHttpError(message="Ocurrió un error al momento de actualizar su cliente", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            succ = MyHtppSuccess(message="Su operación se realizo satisfactoriamente", extra_data="")
            return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


# (ManuelCalixtro 16-06-2022) Listar cliente externo fisico
class ListExternsClients(viewsets.GenericViewSet):
    permission_classes = ()

    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Ver clientes externos"]

    @staticmethod
    def render_json(**kwargs) -> Dict[str, Any]:
        name = kwargs.get("person__name")
        last_name = kwargs.get("person__last_name")
        return {
            "id": kwargs.get('person_id'),
            "Nombre": f"{name} {last_name}",
            "Email": kwargs.get('person__email'),
            "Cuenta": int(kwargs.get('cuenta')[0]['cuenta']),
            "Tarjetas": kwargs.get('tarjetas')
        }

    @staticmethod
    def list_all_client_extern(**kwargs):
        l = grupoPersona.objects.filter(
            empresa_id=kwargs.get('cost_center_id'),
            relacion_grupo_id=9,
            person__email__icontains=kwargs.get('correo', ''),
            person__state=True
        ).values('person_id', 'person__name', 'person__last_name', 'person__email')
        return l

    @staticmethod
    def list_cuentas(lista: list, **kwargs):
        for row in lista:
            c = cuenta.objects.filter(
                cuenta__icontains=kwargs.get('num_cuenta', ''),
                persona_cuenta_id=row.get('person_id'),
                is_active=True
            ).values('id', 'cuenta')

            row['cuenta'] = [i for i in c]

        return lista

    @staticmethod
    def list_tarjetas(lista: list, **kwargs):
        for row in lista:
            for f in row.get('cuenta'):
                cards = tarjeta.objects.filter(
                    cuenta_id=f['id'],
                    tarjeta__icontains=kwargs.get('tarjeta', ''),
                    status='00'
                ).values('id', 'tarjeta')

                if cards:
                    row['tarjetas'] = [i for i in cards]

                if not cards:
                    row['tarjetas'] = 'Sin tarjetas'

        return lista

    def list(self, request, *args, **kwargs):
        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size

        data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
        externs_clients = self.list_tarjetas(self.list_cuentas(self.list_all_client_extern(**data), **data), **data)

        lista = [self.render_json(**i) for i in externs_clients]

        page = self.paginate_queryset(lista)
        return self.get_paginated_response(page)


# (ManuelCalixtro 16-06-2022) Editar cliente externo fisico
class DeleteClienteExternoFisico(viewsets.GenericViewSet):
    permission_classes = ()
    serializer_class = SerializerDeleteClienteExterno

    def create(self):
        pass

    def delete(self, request):
        try:
            with atomic():
                extern_client_id = self.request.query_params['extern_client_id']

                cliente = persona.objects.get(id=extern_client_id)
                relacion_cliente = grupoPersona.objects.filter(person_id=cliente.id, relacion_grupo_id=9)

                serializer = SerializerDeleteClienteExterno(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.delete_extern_client(cliente, relacion_cliente)

                succ = MyHtppSuccess(message="Su operación se realizo satisfactoriamente", extra_data="")
                return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

        except (ObjectDoesNotExist, IntegrityError, ValueError, TypeError) as e:
            err = MyHttpError(message="Ocurrió un error al momento de eliminar su cliente", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


# (ManuelCalixtro 16-06-2022) Ver detalles de cliente externo fisico
class ViewDetailsExternClient(GenericViewSet):
    permission_classes = ()
    serializer_class = SerializerDetailPersonaExternaOut

    def list(self, request, *args, **kwargs):
        usuario = persona.objects.get(id=request.query_params["extern_client_id"])
        queryset = grupoPersona.objects.filter(relacion_grupo_id=9, person_id=usuario)
        serializer = self.serializer_class(instance=queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)








class clienteListFilter_C_E(viewsets.GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver clientes externos"]

    def list(self, request):
        centro_costos_id = self.request.query_params['centro_costos_id']

        get_cost_centers = grupoPersona.objects.get_centro_costos_id(centro_costos_id)
        extern_client = grupoPersona.objects.get_list_actives_clientes_externo(get_cost_centers)
        cuentas = cuenta.objects.filter_account_clientes_externos(extern_client)

        page = self.paginate_queryset(cuentas)
        return self.get_paginated_response(page)