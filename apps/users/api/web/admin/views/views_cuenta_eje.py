from abc import ABC, abstractmethod
from typing import Any, List, Union, ClassVar, NoReturn

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import FilteredRelation
from django.db.transaction import atomic
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import status, pagination
from rest_framework.pagination import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.authtoken.models import Token

from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.Utils.utils import get_values_list, to_dict_params, remove_equal_items
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from MANAGEMENT.Standard.errors_responses import MyHttpError
from apps.commissions.models import Cat_commission, Commission
from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from apps.productos.models import servicios, rel_prod_serv
from apps.users.api.web.serializers.documentos_serializer import SerializerUpDocumentIn
from apps.users.api.web.admin.serializers.serializer_cuenta_eje import *
from apps.users.exc import UserAdminException
from apps.users.management import filter_all_data_or_return_none
from polipaynewConfig.exceptions import NumInt
from MANAGEMENT.Standard.errors_responses import MyHttpError
from apps.users.serializers import *
from apps.users.models import *


# - - - - - - - - - - V i s t a s   p r i n c i p a l e s - - - - - - - - - -

class CreateCuentaEje:
    serializer_class = SerializerGeneral
    serializer = None
    data: dict
    context: dict

    def __init__(self, data, context):
        self.data = data
        self.context = context

    def validate_data(self):
        self.serializer = self.serializer_class(data=self.data, context=self.context)
        self.serializer.is_valid(raise_exception=True)
        return self.serializer.data

    def create(self, validate_data):
        #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
        validate_data["type_ce_ccc"]        = int(self.data["type_ce_ccc"])
        serializer_data = validate_data
        instance_rs, instance_rl, is_admin  = self.serializer.create(serializer_data)
        return instance_rs, instance_rl, is_admin


class ValidateSerializerDocument:
    serializer_class = SerializerUpDocumentIn
    serializer = None

    def __init__(self, list_document):
        self.list_document = list_document

    def validate_data(self):
        list_all = []

        for document in self.list_document:
            self.serializer = self.serializer_class(data=document)
            self.serializer.is_valid(raise_exception=True)
            list_all.append(self.serializer.data)

        return list_all

    def create(self, instance=None, validated_data=None):
        list_doc = validated_data
        for validated_data in list_doc:
            self.serializer.create(validated_data=validated_data, id=instance.get_only_id())

    def create_document_admin(self, list_admin, admin_id_list):
        for i in range(0, len(list_admin)):
            self.serializer.create(validated_data=[i], id=admin_id_list[i])


class ValidateSerializerAdmin:
    serializer_class_admin = SerializerAdministrators
    serializer_class_add_admin = SerializerAddAdministrators
    admin_id_list = []
    list_all_admin = []
    serializer = None

    def __init__(self, list_admin, log: RegisterLog):
        self.list_admin = list_admin
        self.log = log

    def validate_data(self):
        self.list_all_admin = []
        context = {'log': self.log}
        for admin in self.list_admin:
            self.serializer = self.serializer_class_admin(data=admin, context=context)
            self.serializer.is_valid(raise_exception=True)
            self.list_all_admin.append(self.serializer.data)

        return self.list_all_admin

    def create(self, instance, validated_data):
        admin_id_list = []
        for validate_data in validated_data:
            admin_id = self.serializer.create(validate_data)
            context = {'instance': admin_id, 'persona_moral_id': instance.get_only_id()}

            serializer = self.serializer_class_add_admin(data=validate_data, context=context)
            serializer.is_valid(raise_exception=True)
            serializer.create()

            admin_id_list.append(admin_id)

        return admin_id_list


class General:
    documents_rl: dict
    representante_legal: dict
    razon_social: dict
    documents_rs: dict
    documents_admin: dict
    list_admin: dict

    def set_data(self):
        self.razon_social = self.request.data['razon_social']
        self.representante_legal = self.request.data['representante_legal']
        self.list_admin = self.request.data['admins']
        self.documents_rs = self.request.data['documents_razon_social']
        self.documents_rl = self.request.data['documents_representante_legal']
        self.documents_admin = self.request.data['documents_admin']

    def __init__(self, request, log: RegisterLog):
        self.request = request
        self.log = log
        self.set_data()

    def context(self):
        return {
            'method': self.request.method,
            'num_admin': len(self.list_admin),
            'is_admin_rl': self.representante_legal['is_admin'],
            'len_doc_rl': len(self.documents_rl),
            'log': self.log
        }


class CreateCuentaEjeGeneric(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear cuenta eje"]
    #permission_classes = ()

    def create(self, request):
        """
        Se crea una razon social, representante, administrativos,
        y documentos


        """
        log = RegisterLog(request.user, request)
        log.json_request(request.data)

        """ Instanciamos las clases """

        general = General(request, log)
        cuenta_eje = CreateCuentaEje(data=request.data, context=general.context())
        admin = ValidateSerializerAdmin(list_admin=general.list_admin, log=general.log)
        docs_rs = ValidateSerializerDocument(list_document=general.documents_rs)
        docs_rl = ValidateSerializerDocument(list_document=general.documents_rl)
        docs_admin = ValidateSerializerDocument(list_document=general.documents_admin)

        """ Validamos todos los datos y retornamos una lista de datos validados """

        validate_data_cuenta_eje = cuenta_eje.validate_data()
        validate_data_admin = admin.validate_data()
        validate_data_docs_rs = docs_rs.validate_data()
        validate_data_docs_rl = docs_rl.validate_data()
        validate_data_docs_admin = docs_admin.validate_data()

        """ Se crea la cuenta eje y sus tablas anidadas """
        #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
        #   Para el centro de costos concentrador (ccc), recupera el id de la cuenta eje
        self.obj_ce_cc__idCE    = None
        try:
            with atomic():
                #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
                #       Despues de crear la cuenta eje con la estructura PPCE, se crea el centro de contos
                #       concentrador.
                for i in range(2):
                    #       Para la Cuenta Eje (PPCE)
                    if int(i) == 0:
                        self.request.data["type_ce_ccc"]   = 0
                    #       Para el centro de costos concentrador (ccc)
                    elif int(i) == 1:
                        self.request.data["type_ce_ccc"]   = 1

                    instance_razon_social, instance_representante, is_admin = cuenta_eje.create(validate_data_cuenta_eje)

                    #       Para la Cuenta Eje (PPCE)
                    if int(i) == 0:
                        #       Guardo datos de la Cuenta Eje para el Centro de Costos Concentrador
                        self.obj_ce_cc__idCE                            = instance_razon_social.get_razon_social()
                        self.obj_ce_cc__instance_representante_legal    = instance_representante
                        self.obj_ce_cc__is_admin                        = is_admin
                        admin_id_list = admin.create(instance=instance_razon_social, validated_data=validate_data_admin)
                        docs_rs.create(instance=instance_razon_social, validated_data=validate_data_docs_rs)
                        docs_rl.create(instance=instance_representante, validated_data=validate_data_docs_rl)
                        docs_admin.create_document_admin(list_admin=validate_data_docs_admin, admin_id_list=admin_id_list)

                    #       Para el centro de costos concentrador (ccc)
                    if int(i) == 1:
                        instance_representante  = self.obj_ce_cc__instance_representante_legal
                        is_admin                = self.obj_ce_cc__is_admin

                    context = {
                        'instance': instance_razon_social.get_razon_social(),
                        'instance_rl': instance_representante.get_only_id(),
                        'is_admin': is_admin,
                        #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
                        #       Ciclo i=0 para la Cuenta Eje, Ciclo i=1 para el centro de costos concentrador
                        'type_ce_ccc': i,
                        'idCE': self.obj_ce_cc__idCE
                    }

                    serializer_gp = SerializerGrupoPersonaIn(data=general.razon_social, context=context)
                    serializer_gp.is_valid(raise_exception=True)
                    serializer_gp.create()
                    #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06 / 06 / 2022
                    #       Relacion de la concentradora con la cuenta eje (relacion 5)
                    if int(i) == 1:
                        serializer_gp.create_relacion5()

        except Exception as e:
            error = {"status": "Ocurrio un error durante el proceso de creación de una cuenta eje"}
            log.json_response(error)
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        else:
            succ = {"status": "Tu operacion se realizo satisfactoriamente "}
            log.json_response(succ)
            return Response(status=status.HTTP_201_CREATED)


class UpdateRepresentanteLegal(GenericViewSet):
    def get_queryset(self, *args, **kwargs):
        return get_Object_orList_error(*args, **kwargs)

    def get(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.query_params)
        queryset = self.get_queryset(persona, id=self.request.query_params['id'])
        serializer_rl = SerializerRepresentanteLegalUpdateIn(instance=queryset)

        documents = documentos.objects.get(person_id=queryset.id, tdocumento="CD")
        serializer_doc = SerializerGetDocumentOut(instance=documents)

        queryset = self.get_queryset(domicilio, id=queryset.fdomicilio_id)
        serializer_d = SerializerDomicilioIn(instance=queryset)

        succ = {"representante_legal": serializer_rl.data, "domicilio": serializer_d.data,
                "documents": serializer_doc.data}
        log.json_response(succ)
        return Response(status=status.HTTP_200_OK)

    def create(self):
        pass

    def put(self, request):
        """ Actualizar Representante Legal """
        log = RegisterLog(request.user, request)
        log.json_request(request.data)
        context = {'id': self.request.query_params['id'], 'log': log}
        queryset = self.get_queryset(persona, id=context['id'])
        serializer = SerializerRepresentanteLegalUpdateIn(data=request.data, partial=True, context=context)
        serializer.is_valid(raise_exception=True)
        instance = serializer.update(queryset)

        """ Actualizar Domicilio """
        queryset = self.get_queryset(domicilio, id=instance.fdomicilio_id)
        serializer = SerializerDomicilioIn(instance=queryset, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        """ Actualizar Comprobante de Domicilio """
        pk_user = self.request.query_params["id"]
        context = {'log': log}
        instance = documentos.objects.get(person_id=pk_user, tdocumento="D")
        serializer = SerializerEditDomicilioIn(data=request.data, context=context)
        if serializer.is_valid(raise_exception=True):
            serializer.EditDomicilio(instance)
            succ = {'status': 'Tu operación se realizo satisfactoriamente'}
            log.json_response(succ)
            return Response(succ, status=status.HTTP_200_OK)


class Services(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Agregar servicios y comisiones a cuenta eje"]
    """ Se crea servicios, Solo Super-admin queda pendientes los permisos """

    serializer_class = SerializerServicesIn

    def get_queryset(self, *args, **kwargs):
        return filter_data_or_return_none(*args, **kwargs)

    def get(self, request):
        log = RegisterLog(request.user, request)
        queryset = self.get_queryset(persona, id=self.request.query_params['id'], tipo_persona_id=1)
        log.json_request(request.query_params)
        serializer = SerializerRazonSocialOut(instance=queryset)
        log.json_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.data)
        context = {'id_superuser': request.user, 'log': log}
        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.create()

        succ = {'status': 'Su operación fue realizada satisfactoriamente.'}
        log.json_response(succ)
        return Response(succ, status=status.HTTP_201_CREATED)


class GetAllAdminCuentaEje:
    admin_list: ClassVar[List[int]]

    def __init__(self, cuenta_eje_id: int):
        self._cuenta_eje_id = cuenta_eje_id
        self.admin_list = self._get_admin_cuenta_eje

        if self.validate_service:
            raise ValueError("Cuenta eje no existe o ya tiene servicios asignados")

    @property
    def _get_admin_cuenta_eje(self) -> List[int]:
        return grupoPersona.objects.select_related('person', 'relacion_grupo').filter(
            is_admin=True, relacion_grupo_id__in=[1, 3], empresa_id=self._cuenta_eje_id
        ).values_list('person_id', flat=True)

    @property
    def validate_service(self):
        return grupoPersona.objects.filter(
            empresa_id=self._cuenta_eje_id,
            empresa__state=True,
            empresa__is_active=True
        ).exists()


class RequestDataProductsServices:
    products: ClassVar[List[int]]
    comission_list: List[Dict[str, Any]]
    _service_tarjetas_prepago_default: ClassVar[Dict[str, Any]] = {
        "ServiceId": 2,
        "TypeComission": False,
        "Percentage": 0
    }

    def __init__(self, request_data: Dict[str, Any], params: Dict[str, Any]):
        self._request_data = request_data
        self._params = params
        self.products = []
        self.comission_list = self.get_comission_list
        self._raise_services()
        self.add_service_dispersa()
        self._validate_product()

    def _raise_services(self):
        if len(self.comission_list) == 0:
            raise ValueError('Debe de seleccionar por lo menos un servicio')

        if len(self.comission_list) > 2:
            raise ValueError('Debe de enviar únicamente dos servicios')

    @property
    def get_cuenta_eje_id(self) -> int:
        return self._params.get("cuenta_eje_id")

    @property
    def get_comission_list(self) -> List[Dict[str, Any]]:
        return remove_equal_items('ServiceId', self._request_data.get('comission_list'))

    @property
    def get_services_id(self) -> List[Union[int]]:
        return get_values_list('ServiceId', self.comission_list)

    @property
    def get_paycash_service(self) -> Dict[str, Any]:
        return self._request_data.get("PayCashService")

    # (ChrGil 2022-03-03) Si el cliente solo envía el servicio de transacciones, le agregamos nosotros el
    # (ChrGil 2022-03-03) servicio de tarjetas prepago por defecto
    def add_service_dispersa(self):
        if len(self.comission_list) == 1:

            # (ChrGil 2022-03-03) Si tiene le servicio de transferencias
            if self.comission_list[0].get('ServiceId') == 1:
                self.comission_list.append(self._service_tarjetas_prepago_default)

    # (ChrGil 2022-02-09) Dependiendo del serivcio agrega el producto a una lista
    def _validate_product(self):
        for i in self.get_services_id:
            if i == 2:
                # Servicio Tarjetas prepago, Producto: Polipay Dispersion
                self.products.append(1)

            if i == 1:
                # Servicio transferencias, Producto: Polipay Liberate
                self.products.append(2)


# (ChrGil 2022-03-01) Asignar permisos a administrativos de una cuenta eje
class AssignPermissionAdmin:
    _dispersa: ClassVar[PermissionDispersa] = PermissionDispersa
    _liberate: ClassVar[PermissionLiberate] = PermissionLiberate
    _empresa: ClassVar[PermissionEmpresa] = PermissionEmpresa
    _SERVICE_TARJETAS_PREPAGO_ID: ClassVar[int] = 1
    _SERVICE_TRANSFERENCIAS: ClassVar[int] = 2

    def __init__(self, request_data: RequestDataProductsServices, cuenta_eje: GetAllAdminCuentaEje):
        self._request_data = request_data
        self._cuenta_eje = cuenta_eje
        self._assing_permission()

    def _assing_permission(self):
        if len(self._request_data.products) > 1:
            self._empresa(self._cuenta_eje.admin_list)

        if len(self._request_data.products) == 1:
            for product in self._request_data.products:
                if product == self._SERVICE_TARJETAS_PREPAGO_ID:
                    self._dispersa(self._cuenta_eje.admin_list)

                if product == self._SERVICE_TRANSFERENCIAS:
                    self._empresa(self._cuenta_eje.admin_list)


class CreateCatCommission:
    _serializer_class: ClassVar[SerializerProductsServices] = SerializerProductsServices
    list_cat_comission_id: ClassVar[List[int]]

    def __init__(self, request_data: RequestDataProductsServices, cuenta_eje_id: int, super_admin: persona):
        self._request_data = request_data
        self._cuenta_eje_id = cuenta_eje_id
        self._super_admin = super_admin
        self.list_cat_comission_id = []
        self._create()

    @property
    def _context(self) -> Dict[str, int]:
        return {
            "cuenta_eje_id": self._cuenta_eje_id,
            "is_superuser": self._super_admin.get_is_superuser,
            "numero_servicios": self._request_data.products
        }

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "porcentaje": kwargs.pop('Percentage'),
            "tipo_comission": kwargs.pop('TypeComission'),
            "servicio": kwargs.pop('ServiceId'),
        }

    def _create(self) -> NoReturn:
        for comission in self._request_data.comission_list:
            try:
                serializer = self._serializer_class(data=self._data(**comission), context=self._context)
                serializer.is_valid(raise_exception=True)
                self.list_cat_comission_id.append(serializer.create())
            except ValueError as e:
                continue


class CreateComission:
    def __init__(self, cuenta_eje_id: int, comissions: CreateCatCommission):
        self._cuenta_eje_id = cuenta_eje_id
        self._comissions = comissions

        if self._exists:
            self._create()

        if not self._exists:
            raise ValueError('Cuenta eje no valida o no existe')

    def _create(self) -> NoReturn:
        for comission_id in self._comissions.list_cat_comission_id:
            Commission.objects.create_comission(
                pagador=self._cuenta_eje_id,
                deudor=self._cuenta_eje_id,
                comission_id=comission_id
            )

    @property
    def _exists(self) -> bool:
        return grupoPersona.objects.filter(empresa_id=self._cuenta_eje_id, relacion_grupo_id=1).exists()


class ActivateCuentaEje:
    def __init__(self, cuenta_eje_id: int, request_data: RequestDataProductsServices, admin: GetAllAdminCuentaEje):
        self._cuenta_eje_id = cuenta_eje_id
        self._request_data = request_data
        self._admin = admin
        self._activate()
        self._send_mail_admin()

    def _activate(self) -> NoReturn:
        if len(self._request_data.products) > 1:
            persona.objects.filter(id=self._cuenta_eje_id).update(is_active=True, state=True)
            cuenta.objects.filter(persona_cuenta_id=self._cuenta_eje_id).update(is_active=True, rel_cuenta_prod_id=3)

        if len(self._request_data.products) == 1:
            for i in self._request_data.products:
                persona.objects.filter(id=self._cuenta_eje_id).update(is_active=True, state=True)
                cuenta.objects.filter(
                    persona_cuenta_id=self._cuenta_eje_id
                ).update(is_active=True, rel_cuenta_prod_id=i)

    def _send_mail_admin(self):
        admins = persona.objects.filter(id__in=self._admin.admin_list)
        for admin in admins:
            password = random_password()
            admin.password = password
            admin.set_password(admin.password)
            admin.state = True
            createMessageWelcome(admin, password)

        persona.objects.bulk_update(admins, fields=['password', 'state'])


# (CgiGil 2022-06-15) Asignar servicio de Pago en efectivo (PayCash)
class ComponentCreateServicePayCash:
    _serializer_class: ClassVar[SerializerProductsServices] = SerializerProductsServices
    _SERVICE_PAYCASH: ClassVar[int] = 3

    def __init__(self, request_data: RequestDataProductsServices):
        self.request_data = request_data
        self.type_comission = request_data.get_paycash_service.get("TypeComission")
        self.positive_commission = 1
        self.negative_commission = 2
        self.aplicacion_mensual = 1
        self.aplicacion_inmediato = 2
        self.cat_comission_id = self.create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "porcentaje": 0.0,
            "monto": self.request_data.get_paycash_service.get("FixedAmount"),
            "descripcion": "Pago en efectivo PayCash",
            "tipo_comission": self.positive_commission if self.type_comission else self.negative_commission,
            "aplicacion": self.aplicacion_mensual if self.type_comission else self.aplicacion_inmediato,
            "servicio": self._SERVICE_PAYCASH,
        }

    def create(self):
        return Cat_commission.objects.create_cat_comission(**self._data)


class ComponentCreateComissionPayCash:
    def __init__(self, request_data: RequestDataProductsServices, comission: ComponentCreateServicePayCash):
        self.request_data = request_data
        self.comission_id = comission.cat_comission_id
        self._cretae()

    def _cretae(self):
        Commission.objects.create_comission(
            pagador=self.request_data.get_cuenta_eje_id,
            deudor=self.request_data.get_cuenta_eje_id,
            comission_id=self.comission_id
        )


# http://127.0.0.1:8000/users/web/admin/v3/AsiSer/create/?cuenta_eje_id=1373
class ProductsServices(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Agregar servicios y comisiones a cuenta eje"]
    #permission_classes = ()

    def create(self, request):
        log = RegisterLog(request.user, request)
        try:
            cuenta_eje_id: int = self.request.query_params['cuenta_eje_id']
            log.json_request(request.data)
            super_admin: persona = self.request.user

            with atomic():
                request_data = RequestDataProductsServices(request.data)

                #   (2022.06.23 11:00 - ChrAvaBus) CENTRO DE COSTOS CONCENTRADOR (centro de costos incial)
                #       Se agrega funcionalidad para eliminar el centro de costos concentrador si el tipo de servicio
                #       es 2 (ServiceId:2) / Dipsersa / Tarjetas Prepago
                log.json_request({"CentoDeCostosConcentrador":"Confirmando tipo de servicio para poder eliminarlo..."})
                for servicio in request.data["comission_list"]:
                    if int(servicio["ServiceId"]) == int(1) and len(request.data["comission_list"]) == 1:
                        obj_del_cc  = EliminarCentroDeCostosConcentrador(request.data, cuenta_eje_id, log)
                        obj_del_cc.delete()
                        log.json_request({"CentoDeCostosConcentrador":"¡Eliminado!"})
                        break

                request_data = RequestDataProductsServices(request.data, self.request.query_params.copy())
                admin_cuenta_eje = GetAllAdminCuentaEje(cuenta_eje_id)
                cat_comission = CreateCatCommission(request_data, cuenta_eje_id, super_admin)
                CreateComission(cuenta_eje_id, cat_comission)
                service_paycash = ComponentCreateServicePayCash(request_data)
                ComponentCreateComissionPayCash(request_data, service_paycash)
                AssignPermissionAdmin(request_data, admin_cuenta_eje)
                ActivateCuentaEje(cuenta_eje_id, request_data, admin_cuenta_eje)

        except (ValueError, TypeError, KeyError) as e:
            err = MyHttpError("Ocurrió un error al asignar servicios y comisiones a la cuenta eje", real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        except UserAdminException as e:
            msg = "Ocurrió un error al asignar servicios y comisiones a la cuenta eje"
            err = MyHttpError(msg, real_error=e.message)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            succ = MyHtppSuccess("Su operación se realizo de manera satisfactoria")
            log.json_response(succ.standard_success_responses())
            return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)



#   (2022.06.23 11:00 - ChrAvaBus) CENTRO DE COSTOS CONCENTRADOR (centro de costos incial)
class EliminarCentroDeCostosConcentrador:
    #   1.- Elimina el centro de costos concentrador y sus relaciones.
    #   2.- Establece la cuenta y CLABE STP a la cuenta eje

    def __init__(self, data:dict, cuenta_eje_id: int, log):
        self.data           = data,
        self.cuenta_eje_id  = cuenta_eje_id
        self.cuenta         = None
        self.clabe          = None
        self.log            = log

    def exist_cuenta_eje(self, ):
        existeCuentaEje = persona.objects.filter(id=self.cuenta_eje_id).exists()
        if not existeCuentaEje:
            err = MyHttpError("No existe cuenta eje", real_error="")
            self.log.json_response(err.standard_error_responses())
            raise ValueError("No existe cuenta eje")

        existeCuentaDeCE    = cuenta.objects.filter(persona_cuenta_id=self.cuenta_eje_id).exists()
        if not existeCuentaDeCE:
            err = MyHttpError("No existe cuenta de la cuenta eje", real_error="")
            self.log.json_response(err.standard_error_responses())
            raise ValueError("No existe cuenta de la cuenta eje")

    def exist_cc_concentrador(self, cc_id: int):
        existeCentroDeCostos    = persona.objects.filter(id=cc_id).exists()
        if not existeCentroDeCostos:
            err = MyHttpError("No existe centro de costos concentrador", real_error="")
            self.log.json_response(err.standard_error_responses())
            raise ValueError("No existe centro de costos concentrador")

        existeCuentaDeCC    = cuenta.objects.filter(persona_cuenta_id=cc_id).exists()
        if not existeCuentaDeCC:
            err = MyHttpError("No existe cuenta del centro de costos concentrador", real_error="")
            self.log.json_response(err.standard_error_responses())
            raise ValueError("No existe cuenta del centro de costos concentrador")
        else:
            cuentaDeCC = cuenta.objects.filter(persona_cuenta_id=cc_id).values("cuenta", "cuentaclave")
            self.cuenta = cuentaDeCC[0]["cuenta"]
            self.clabe  = cuentaDeCC[0]["cuentaclave"]

    def exist_relacion_ce_cc(self, ):
        existeRelacion  = grupoPersona.objects.filter(empresa_id=self.cuenta_eje_id, relacion_grupo_id=5).exists()
        if not existeRelacion:
            err = MyHttpError("No existe relacion del centro de costos concentrador", real_error="")
            self.log.json_response(err.standard_error_responses())
            raise ValueError("No existe relacion del centro de costos concentrador")
        else:
            relacion = grupoPersona.objects.filter(empresa_id=self.cuenta_eje_id, relacion_grupo_id=5).values("person_id")
            if len(relacion) > 1:
                err = MyHttpError("Existe mas de una relación del centro de costos concentrador con la cuenta eje", real_error="")
                self.log.json_response(err.standard_error_responses())
                raise ValueError("Existe mas de una relación del centro de costos concentrador con la cuenta eje")

    def get_cc_id(self, ):
        centroDeCostos  = grupoPersona.objects.filter(empresa_id=self.cuenta_eje_id, relacion_grupo_id=5).values("person_id")
        return centroDeCostos[0]["person_id"]

    def delete_domicilio(self, cc_id: int):
        domicilio.objects.filter(domicilioPersona_id=cc_id).delete()
        self.log.json_request({"CentoDeCostosConcentrador": "Domicilio cc_id[" + str(cc_id) + "]"})

    def delete_relacion_grupopersona(self, cc_id: int):
        grupoPersona.objects.filter(empresa_id=cc_id, relacion_grupo_id=4).delete()
        self.log.json_request({"CentoDeCostosConcentrador": "Relacion tipo 4 eliminado"})
        grupoPersona.objects.filter(empresa_id=self.cuenta_eje_id, person_id=cc_id, relacion_grupo_id=5).delete()
        self.log.json_request({"CentoDeCostosConcentrador": "Relacion tipo 5 eliminado"})

    def delete_cuenta(self, cc_id: int):
        cuenta.objects.filter(persona_cuenta_id=cc_id).delete()
        self.log.json_request({"CentoDeCostosConcentrador": "Cuenta eliminada cc_id[" + str(cc_id) + "]"})
        cuenta.objects.filter(persona_cuenta_id=self.cuenta_eje_id).update(cuenta=self.cuenta, cuentaclave=self.clabe)
        self.log.json_request({"CentoDeCostosConcentrador": "Cuenta[" + str(self.cuenta) + "]   Clabe["+str(self.clabe)+"]"})

    def delete_persona(self, cc_id: int):
        persona.objects.filter(id=cc_id).delete()
        self.log.json_request({"CentoDeCostosConcentrador": "Persona eliminada cc_id["+str(cc_id)+"]"})

    def delete(self):
        #   Valida cuenta eje
        self.exist_cuenta_eje()
        #   Valida relacion de la ce con cc
        self.exist_relacion_ce_cc()
        #   Recupera id del centro de costos
        cc_id   = self.get_cc_id()
        #   Valida centro de costos
        self.exist_cc_concentrador(cc_id)

        #   Busca para ser eliminado: domicilio
        self.delete_domicilio(cc_id)
        #   Busca para ser eliminado: relacion con cuenta eje (grupopersona id=4 y id=5)
        self.delete_relacion_grupopersona(cc_id)
        #   Busca para ser eliminado: cuenta
        self.delete_cuenta(cc_id)
        #   Busca para ser eliminado: persona (Centro de costos)
        self.delete_persona(cc_id)



# - - - - - - - - - - L i s t a d o s - - - - - - - - - -
# class ListAdministrativeStaff(GenericViewSet):
# permission_classes = (BlocklistPermissionV2,)
# serializer_class_all = serializerAdministrativeStaffOut
# serializer_class_N_E = serializerAdministrativeStaffNameEmailOut

# def list(self, request):
# try:
# query_user = persona.objects.raw(
# 'SELECT person_id AS id FROM users_grupopersona WHERE is_admin=True and empresa_id= %s',
# [self.request.query_params["id"]])
# Type = self.request.query_params["type"]
# if Type == "ALL":
#   serializer = self.serializer_class_all(query_user, many=True)
# elif Type == "N-E":
#    serializer = self.serializer_class_N_E(query_user, many=True)
# else:
#      return Response({"status": "Se esperaba un Type"}, status=status.HTTP_400_BAD_REQUEST)
#   return Response(serializer.data, status=status.HTTP_200_OK)
# except Exception as e:
# return Response({"status": f"Se esperaba id de 'Empresa' {e}"}, status=status.HTTP_400_BAD_REQUEST)


class RetrieveCuentaEje(RetrieveAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver detalles de una cuenta eje"]
    serializer_class = SerializerRetrieveCuentaEje

    def retrieve(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            gp = grupoPersona.objects.get_object_cuenta_eje(request.query_params['id'])
            log.json_request(request.query_params)
            serializer = self.serializer_class(instance=gp)
            log.json_response(serializer.data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except MultiValueDictKeyError as e:
            err = MyHttpError("Asegurese de haber ingresado todos los parametros", real_error=str(e))
            log.json_response(err.multi_value_dict_key_error())
            return Response(err.multi_value_dict_key_error(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            err = MyHttpError("Recurso no encontrado", str(e), 404)
            log.json_response(err.object_does_not_exist())
            return Response(err.object_does_not_exist(), status=status.HTTP_404_NOT_FOUND)


# class ListCuentaEje(ListAPIView):
#     permission_classes = (BlocklistPermissionV2,)
#     permisos = ["Ver cuentas eje"]
#     serializer_class = SerializerListCuentaEje
#     pagination_class = PageNumberPagination
#
#     def get_queryset(self, *args, **kwargs):
#         return filter_all_data_or_return_none(*args, **kwargs)
#
#     def list(self, request, *args, **kwargs):
#         size = request.query_params['size']
#         self.pagination_class.page_size = size
#         is_active = request.query_params['active'].title()
#
#         queryset = grupoPersona.objects.only('empresa_id', 'nombre_grupo').filter(relacion_grupo_id=1).filter(
#             empresa__is_active=is_active, empresa__tipo_persona_id=1).order_by('-empresa__date_joined')
#
#         page = self.paginate_queryset(queryset)
#
#         serializer = self.serializer_class(instance=page)
#         return self.get_paginated_response(serializer.data)


class ListCuentaEjeClass:
    list_cuenta_eje: ClassVar[List[Dict[str, Any]]]

    def __init__(self, **kwargs):
        self._active = kwargs.get('active', 1)
        self._state = kwargs.get('state', 1)
        self.default_size = kwargs.get('size', 5)

        _list_data_cuenta_eje = self._list_data_cuenta_eje
        self.list_cuenta_eje = [self.render(**i) for i in self.set_services(_list_data_cuenta_eje)]

    @property
    def _list_only_id_cuenta_eje(self) -> List[int]:
        return grupoPersona.objects.annotate(
            company=FilteredRelation(
                'empresa', condition=Q(empresa__is_active=self._active) & Q(empresa__state=self._state)
            ),
        ).filter(company__tipo_persona_id=1, relacion_grupo_id=1).values_list('empresa_id', flat=True)

    @property
    def _list_data_cuenta_eje(self) -> List[Dict[str, Any]]:
        return cuenta.objects.select_related(
            'persona_cuenta'
        ).filter(
            persona_cuenta__in=self._list_only_id_cuenta_eje
        ).values(
            'cuenta',
            'cuentaclave',
            'persona_cuenta_id',
            'persona_cuenta__name',
            'persona_cuenta__date_joined'
        ).order_by(
            '-fecha_creacion'
        )

    def _get_services(self, person_payer_id: int) -> List[str]:
        return Commission.objects.select_related(
            'person_debtor',
            'person_payer',
            'commission_rel'
        ).filter(
            Q(person_payer_id=person_payer_id) | Q(person_debtor_id=person_payer_id)
        ).values_list(
            'commission_rel__servicio__service__nombre',
            flat=True
        )

    def set_services(self, list_cuenta_eje: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for cuenta_eje in list_cuenta_eje:
            cuenta_eje['services'] = list(self._get_services(cuenta_eje.get('persona_cuenta_id')))
        return list_cuenta_eje

    def render(self, **kwargs) -> Dict[str, Any]:
        return {
            "id": kwargs.pop('persona_cuenta_id'),
            "name": kwargs.pop('persona_cuenta__name'),
            "FechaCaptura": kwargs.pop('persona_cuenta__date_joined'),
            "clabe": kwargs.pop('cuentaclave'),
            "NumeroCuenta": kwargs.pop('cuenta'),
            "services": kwargs.pop('services')
        }


# Endpoint: http://127.0.0.1:8000/users/web/admin/v3/LisCueEje/list/?size=100&active=1&state=1
class ListCuentaEje(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver cuentas eje"]

    pagination_class = PageNumberPagination

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        list_cuenta_eje = ListCuentaEjeClass(**to_dict_params(self.request.query_params.copy()))
        log.json_request(request.query_params)
        self.pagination_class.page_size = list_cuenta_eje.default_size

        for companys in list_cuenta_eje.list_cuenta_eje:
            log.json_response(companys)

        return self.get_paginated_response(self.paginate_queryset(list_cuenta_eje.list_cuenta_eje))


# (ManuelCalixtro 18/11/2021, Endpoint para agregar un administrador a una cuenta eje)
class AddAdministratives(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear Administrador", "Ver Administradores", "Editar Administrador", "Eliminar Administrador"]
    serializer_class = SerializerAddAdministrativesCompany

    def create(self, request):
        log = RegisterLog(request.user, request)
        empresa_id = self.request.query_params['empresa_id']
        log.json_request(request.data)
        get_empresa = grupoPersona.objects.get(empresa_id=empresa_id, relacion_grupo_id=1).get_only_id_empresa()

        context = {
            'empresa_id': get_empresa,
            'log': log
        }

        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.create(get_empresa)
        succ = {'code': 201, 'status': 'created', 'message': "Tu operacion se realizo de manera satisfactoria"}
        log.json_response(succ)
        return Response(succ)

    def get(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        admin = request.query_params['admin_id']
        log.json_request(request.query_params)
        query = persona.objects.filter(id=admin).values('name', 'last_name', 'phone', 'email')
        log.json_response(query.first())
        return Response(query)

    def put(self, request):
        log = RegisterLog(request.user, request)
        admin_company = get_Object_orList_error(persona, id=self.request.query_params['admin_id'])
        log.json_request(request.data)
        serializer = SerializerUpdateAdmin(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(admin_company)
        succ = {'code': 200, 'status': 'Update', 'message': 'Tu operacion se realizo de manera satisfactoria'}
        log.json_response(succ)
        return Response(succ)

    def delete(self, request):
        log = RegisterLog(request.user, request)
        admin = get_Object_orList_error(persona, id=self.request.query_params['admin_id'])
        log.json_request(request.data)
        admin_company = grupoPersona.objects.filter(
            Q(person_id=admin, relacion_grupo_id=3) | Q(person_id=admin, relacion_grupo_id=1))
        serializer = SerializerDeleteAdmin(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.delete_admin(admin, admin_company)
        succ = {'code': 200, 'status': 'Delete', 'message': 'Tu operacion se realizo satisfactoria'}
        log.json_response(succ)
        return Response(succ)


# (ChrGil 2021-11-19) Listado de administrativos de una cuenta eje
class ListAdminCuentaEje(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver Administradores"]

    # (ChrGil) Parametros de url (cuenta_eje_id)
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            cuenta_eje_id: int = request.query_params['cuenta_eje_id']
            log.json_request(request.query_params)
            list_querys_ids_admin = grupoPersona.objects.get_list_ids_admin(company_id=cuenta_eje_id)
            admins = persona.querys.list_person(list_querys_ids_admin)
            for admin in admins:
                log.json_response(admin)
            return Response(admins, status=status.HTTP_200_OK)

        except MultiValueDictKeyError as e:
            err = MyHttpError("Asegurese de haber ingresado todos los parametros", real_error=str(e))
            log.json_response(err.multi_value_dict_key_error())
            return Response(err.multi_value_dict_key_error(), status=status.HTTP_400_BAD_REQUEST)

        except TypeError as e:
            err = MyHttpError("Los parametros de filtrado no coinciden con los esperados", str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            err = MyHttpError(message="Recurso no encontrado", real_error=str(e), code=404)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)


# (ChrGil 2021-11-22) Ver detalle de un administrativo
class DetailAdminsCuentaEje(RetrieveAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver detalles de Administrador"]

    # permission_classes = [IsAuthenticated]

    # (ChrGil 2021-11-22) Parametros de URL (admin_id)
    def retrieve(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            admin_id: int = request.query_params['admin_id']
            log.json_request(request.query_params)
            data: Dict[str, Any] = persona.querys.get_person_object(person_id=admin_id)
            data['document'] = documentos.objects.get_url_aws_document_by_type(admin_id, type_document=12)
            log.json_response(data)
            return Response(data, status=status.HTTP_200_OK)

        except MultiValueDictKeyError as e:
            err = MyHttpError("Asegurese de haber ingresado todos los parametros", real_error=str(e))
            log.json_response(err.multi_value_dict_key_error())
            return Response(err.multi_value_dict_key_error(), status=status.HTTP_400_BAD_REQUEST)

        except TypeError as e:
            err = MyHttpError("Los parametros de URL no coinciden con los esperados", str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            err = MyHttpError(message="Recurso no encontrado", real_error=str(e), code=404)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except AttributeError as e:
            msg = "Esta persona no tiene registrado un archivo que compruebe su identidad"
            err = MyHttpError(message=msg, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
