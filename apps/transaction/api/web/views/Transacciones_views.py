from abc import ABC, abstractmethod
from typing import NoReturn
import pandas as pd
from datetime import timedelta, datetime
import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, get_object_or_404
from django.db import connection
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets, status, pagination
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.viewsets import GenericViewSet

from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.AlgSTP.GenerarFirmaSTP import RegistraOrdenDataSTP, GetPriKey, GeneraFirma, SignatureCertSTP
from MANAGEMENT.Utils.utils import remove_asterisk
from apps.api_dynamic_token.api.web.views.views_dynamic_token import ValidateTokenDynamic
from apps.api_dynamic_token.exc import JwtDynamicTokenException
from apps.api_stp.client import CosumeAPISTP
from apps.api_stp.exc import StpmexException
from apps.api_stp.interface import EmisorTransaction
from apps.api_stp.management import SetFolioOpetacionSTP
from apps.api_stp.signature import SignatureTestAPIStpIndividual
from apps.logspolipay.manager import RegisterLog
from apps.transaction.exc import CostCenterIsNotActivate, CostCenterStatusAccount, InsufficientBalance, \
    CostCenterException, TransactionDoestNotExists, TransactionException
from polipaynewConfig.exceptions import *
from apps.permision.permisions import BlocklistPermissionV2
from apps.transaction.api.movil.serializers.TransMasivaProd_serializer import *
from apps.transaction.api.web.serializers.Transacciones_serializer import *
from apps.transaction.management import createExcelData, transaction_status_change, to_dict_query_params
from apps.transaction.models import *
from apps.users.management import get_Object_orList_error
from apps.transaction.messages import *
from apps.users.models import *
# from apps.transaction.management import preparingNotification
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess


#__POSIBLE__OBSOLETO
class Transacciones(viewsets.GenericViewSet):
    permission_classes = ()

    def list(self, request):
        dateNow = datetime.datetime.now()
        dateEnd = dateNow - timedelta(days=30)
        fecha = request.data["fecha"]
        try:
            if fecha != None:
                dateNow = datetime.datetime.strptime(fecha, "%Y-%m-%d")
                dateEnd = dateNow - timedelta(days=30)
            querydate = transferencia.objects.filter(fecha_creacion__lte=dateNow, fecha_creacion__gte=dateEnd)
            serializer = serializerTransaccionesOut(querydate, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response({"status": "Fecha no identificada"}, status=status.HTTP_400_BAD_REQUEST)


#__POSIBLE__OBSOLETO
class transaccionesMasivasExcel(viewsets.GenericViewSet):
    serializer_class = serializerTransMasivaProdIn
    queryset = transmasivaprod.objects.all()
    pagination_class = PageNumberPagination

    def create(self, request):
        createExcelData(request.data['file'])
        serializer = self.serializer_class(data=request.data)
        print("1")
        IdPersona = get_Object_orList_error(persona, id=request.data["idPerson"])
        print("2")
        IdStatus = get_Object_orList_error(Status, id=request.data["idStatus"])
        print("3")
        Id_account = get_Object_orList_error(cuenta, id=request.data["idCuenta"])
        print("4")
        if serializer.is_valid(raise_exception=True):
            serializer.createMasive(IdPersona, IdStatus, Id_account)
            return Response({"status": "Se a realizado la transferencia masiva"}, status=status.HTTP_200_OK)

    def list(self, request):
        size = self.request.query_params["size"]
        size = NumInt(size=size)
        pagination.PageNumberPagination.page_size = size
        pk_account = self.request.query_params['id']
        if pk_account:
            instanceC = get_Object_Or_Error(cuenta, id=pk_account)
            df = pd.read_excel('Files/file.xlsx', sheet_name="Layout2021")
            df.fillna('', inplace=True)
            print(df)
            queryset = transmasivaprod.objects.raw(
                'SELECT masivo_trans_id AS id FROM polipaynew.transaction_transferencia WHERE cuentatransferencia_id= %s',
                [instanceC.id])
            page = self.paginate_queryset(queryset)
            serializer = serializerTransmasivaprodOut(page, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"status": "Se esperaba una id de cuenta"}, status=status.HTTP_400_BAD_REQUEST)


#__POSIBLE__OBSOLETO
class changeStatusTransactions(viewsets.GenericViewSet):
    queryset = transferencia.objects.all()
    permission_classes = ()

    def create(self, request):
        query_transaction = transferencia.objects.get(id=request.data['id'])
        status_instance = Status.objects.get(id=self.request.query_params['status'])
        instance_cuenta = cuenta.objects.get(id=query_transaction.cuentatransferencia_id)
        instance_persona = query_transaction.nombre_emisor

        if status_instance.nombre == 'devuelta':
            if query_transaction.status_trans_id == 2:  # devuelta
                return Response({"status": "Esta transferencia ya ha sido devuelta anteriormente",
                                 "date": query_transaction.date_modify}, status=status.HTTP_400_BAD_REQUEST)
            if query_transaction.status_trans_id == 3:  # pediente
                return Response({"status": "Esta tranferencia ya ha sido devuelta y se encuentra pendiente"},
                                status=status.HTTP_400_BAD_REQUEST)
            if query_transaction.status_trans_id == 5:  # cancelada
                return Response({"status": "Esta transferencia ya ha sido cancelada"},
                                status=status.HTTP_400_BAD_REQUEST)
            else:
                return transaction_status_change(query_transaction, instance_cuenta, status_instance, instance_persona,
                                                 'DEVUELTA')

        if status_instance.nombre == 'pendiente':
            if query_transaction.status_trans_id == 1:  # enviada
                return Response({"status": "Esta transferencia ya ha sido enviada"}, status=status.HTTP_400_BAD_REQUEST)
            if query_transaction.status_trans_id == 3:  # pendiente
                return Response(
                    {"status": "Esta transferencia ya se encuentra pendiente", "date": query_transaction.date_modify},
                    status=status.HTTP_400_BAD_REQUEST)
            if query_transaction.status_trans_id == 5:  # cancelada
                return Response({"status": "Esta transferencia ya ha sido cancelada", },
                                status=status.HTTP_400_BAD_REQUEST)
            else:
                return transaction_status_change(query_transaction, instance_cuenta, status_instance, instance_persona,
                                                 'PENDIENTE')

        if status_instance.nombre == 'enviada':
            if query_transaction.status_trans_id == 5:  # cancelada
                return Response({"status": "Esta transferencia ya ha sido cancelada"},
                                status=status.HTTP_400_BAD_REQUEST)
            if query_transaction.status_trans_id == 1:  # enviada
                return Response({"status": "Esta transferencia ya sido enviada anteriormente",
                                 "date": query_transaction.date_modify}, status.HTTP_400_BAD_REQUEST)
            else:
                return transaction_status_change(query_transaction, instance_cuenta, status_instance, instance_persona,
                                                 'ENVIADA')

        if status_instance.nombre == 'cancelada':
            if query_transaction.status_trans_id == 1:  # enviada
                return Response({"status": "Esta tranferencia ya ha sido enviada"}, status=status.HTTP_400_BAD_REQUEST)
            if query_transaction.status_trans_id == 5:  # cancelada
                return Response({"status": "Esta transferencia ya ha sido cancelada anteriormente",
                                 "date": query_transaction.date_modify}, status.HTTP_400_BAD_REQUEST)
            else:
                return transaction_status_change(query_transaction, instance_cuenta, status_instance, instance_persona,
                                                 'CANCELADA')


# (ManuelCalixtro) Lista todos los bancos para los select
class ListAllBanks(viewsets.GenericViewSet):
    permission_classes = ()
    serializer_class = serializerListAllBanks

    def list(self, request):
        queryset = bancos.objects.all()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


#__POSIBLE__OBSOLETO
class ListMovimientoEgresos(ListAPIView):
    permission_classes = ()
    serializer_class = serializerMoviemientoEgresos
    pagination_class = PageNumberPagination

    def get_queryset(self, *args, **kwargs):
        return filter_all_data_or_return_none(*args, **kwargs)

    def list(self, request, *args, **kwargs):
        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size

        person_instance = get_Object_orList_error(persona, id=self.request.query_params['id'])
        account_instance = get_Object_orList_error(cuenta, persona_cuenta=person_instance)
        transferencia_instance = filter_all_data_or_return_none(transferencia, cuenta_emisor=account_instance.cuenta)

        page = self.paginate_queryset(transferencia_instance)
        serializer_emp = serializerPerson(instance=person_instance)
        serializer_trans = self.serializer_class(page, many=True)

        return self.get_paginated_response({
            'Empresa': serializer_emp.data,
            'Egresos': serializer_trans.data})


# (ManuelCalixtro) Lista todos los centros de costos para el select de transacciones recibidas
class GetCuentaEje(ListAPIView):

    def list(self, request, *args, **kwargs):
        get_cost_center = grupoPersona.objects.filter(relacion_grupo_id=4, empresa__is_active=True).values('empresa_id',
                                                                                                           'empresa__name')
        return Response(get_cost_center)


# (ManuelCalixtro) Lista todos las personas fisicas para el select de transacciones recibidas
class GetFisicPerson(ListAPIView):
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        g = grupoPersona.objects.filter(
            relacion_grupo_id=9,
            person__state=True,
            person__tipo_persona_id=2
        ).values_list('person_id', flat=True)

        person = cuenta.objects.filter(persona_cuenta_id__in=g).values(
            'cuentaclave', 'persona_cuenta__name', 'persona_cuenta__last_name', 'persona_cuenta__id')

        lista = []

        for query in person:
            if "X" in query['cuentaclave']:
                continue
            else:
                lista.append(query)
        return Response(lista)

#__POSIBLE__OBSOLETO
# class CreateTransactionReceived(viewsets.GenericViewSet):
#     permission_classes = (BlocklistPermissionV2,)
#     permisos = ["Crear transacción recibida"]
#     serializer_class = CreateTransactionReceivedIn
#
#     def create(self, request):
#         log_dict = {
#             "params": request.query_params,
#             "body": request.data
#         }
#         RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
#                           objJsonRequest=log_dict)
#         id = self.request.query_params['cost_center_id']
#         cost_center = grupoPersona.objects.get(empresa_id=id, relacion_grupo_id=4).get_empresa()
#         instance_cuenta_beneficiaria = get_Object_orList_error(cuenta, persona_cuenta_id=cost_center['id'])
#
#         context = {
#             'cuenta_eje': cost_center['name'],
#             'nombre_beneficiario': cost_center['name'],
#             'cuenta_beneficiaria': instance_cuenta_beneficiaria,
#         }
#
#         serializer = self.serializer_class(data=request.data, context=context)
#         serializer.is_valid(raise_exception=True)
#         serializer.create()
#         RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
#                           objJsonRequest=serializer.data)
#
#         return Response({'code': 200,
#                          'status': 'success',
#                          'message': 'Tu operación se realizo de manera satisfactoria'}, status=status.HTTP_200_OK)
#
#     def list(self, request, *args, **kwargs):
#         get_cost_center = grupoPersona.objects.filter(relacion_grupo_id=4, empresa__is_active=True).values('empresa_id',
#                                                                                                            'nombre_grupo')
#         return Response(get_cost_center)


# (ManuelCalixtro) Lista todos los centros de costos para el select de transacciones recibidas
class GetCostCenter(ListAPIView):
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=request.data)

        get_cost_center = grupoPersona.objects.filter(relacion_grupo_id=4, empresa__is_active=True).values('empresa_id',
                                                                                                           'empresa__name')
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest={get_cost_center})
        return Response(get_cost_center)


# (ManuelCalixtro) Crea transacciones recibidas para personas fisicas
class CreateTransactionReceivedFisicPerson(viewsets.GenericViewSet):
    serializer_class = SerializerCreateTransactionReceivedFisicPerson

    def create(self, request):
        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)
        id = self.request.query_params['persona_fisica_id']
        persona_fisica = persona.objects.get(id=id, tipo_persona_id=2).get_fisic_person()
        instance_cuenta_beneficiaria = get_Object_orList_error(cuenta, persona_cuenta_id=persona_fisica['id'])

        context = {
            'nombre_beneficiario': persona_fisica['name'],
            'cuenta_beneficiaria': instance_cuenta_beneficiaria,
        }

        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.create()
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer.data)
        # preparingNotification(idPersona=id, opcion=2)
        return Response({'code': 200,
                         'status': 'success',
                         'message': 'Tu operación se realizo de manera satisfactoria'}, status=status.HTTP_200_OK)


# (ManuelCalixtro) Lista las transacciones recibidas de personas morales
class ListTransactionReceivedCompany(ListAPIView):
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log_dict = {
            "params": request.query_params,
            "body": request.data
        }

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=log_dict)

        size = self.request.query_params['size']
        nombre_emisor = self.request.query_params['nombre_emisor']
        start_date = self.request.query_params['date1']
        end_date = self.request.query_params['date2']
        pagination.PageNumberPagination.page_size = size

        transferencias_rec = transferencia.filter_transaction.transactions_received_moral_person(
            nombre_emisor=nombre_emisor,
            tipo_persona_id=1,
            date1=start_date,
            date2=end_date
        )

        page = self.paginate_queryset(transferencias_rec)
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=page)
        return self.get_paginated_response(page)


# (ManuelCalixtro) Lista las transacciones recibidas de personas fisicas
class ListTransactionReceivedFisicPerson(ListAPIView):
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=request.data)

        size = self.request.query_params['size']
        nombre_emisor = self.request.query_params['nombre_emisor']
        start_date = self.request.query_params['date1']
        end_date = self.request.query_params['date2']
        pagination.PageNumberPagination.page_size = size

        queryset = transferencia.filter_transaction.transactions_received_moral_person(
            nombre_emisor=nombre_emisor,
            tipo_persona_id=2,
            date1=start_date,
            date2=end_date
        )

        page = self.paginate_queryset(queryset)
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=page)
        return self.get_paginated_response(page)


# (ManuelCalixtro) Muestra los detalles de las transacciones recibidas
class DetailTransactionRecieved(viewsets.GenericViewSet):
    serializer_class = serializerDetailTransactionReceived

    def list(self, request, *args, **kwargs):
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=self.request.query_params)

        id = self.request.query_params['transferencia']
        queryset = transferencia.objects.filter(id=id, tipo_pago_id=5)

        context = {
            "instance_cta_benef": queryset
        }

        serializer = self.serializer_class(instance=queryset, many=True, context=context)
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RequestDataTransactionIndividual:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_nombre_beneficiario(self) -> str:
        return self._request_data.get('nombre_beneficiario')

    @property
    def get_email(self) -> str:
        return self._request_data.get('email')

    @property
    def get_rfc_curp_beneficiario(self) -> str:
        return self._request_data.get('rfc_curp_beneficiario')

    @property
    def get_cuenta_beneficiario(self) -> str:
        return self._request_data.get('cuenta_beneficiario')

    @property
    def get_monto(self) -> float:
        return self._request_data.get('monto')

    @property
    def get_banco_beneficiario_id(self) -> str:
        return self._request_data.get('banco_beneficiario_id')

    @property
    def get_referencia_numerica(self) -> str:
        return self._request_data.get('referencia_numerica')

    @property
    def get_concepto_pago(self) -> str:
        return self._request_data.get('concepto_pago')

    @property
    def is_frecuent(self) -> bool:
        return self._request_data.get('is_frecuent')

    @property
    def get_alias(self) -> str:
        return self._request_data.get('alias')

    @property
    def get_token_dynamic(self) -> str:
        return self._request_data.get('auth').get('token')


class GetInfoEmisorCostCenter:
    info_account: ClassVar[Dict[str, Any]]
    info_cost_center: ClassVar[Dict[str, Any]]
    info_admin: ClassVar[Dict[str, Any]]

    def __init__(self, cost_center_id: int, admin: persona):
        self._cost_center_id = cost_center_id
        self._admin = admin
        self.info_cost_center = self._get_info_cost_center
        self.info_account = self._get_info_account
        self.info_admin = self._get_info_admin

        if not self.info_cost_center:
            raise CostCenterIsNotActivate("Centro de costos no activo o dado de baja")

        if not self.info_account:
            raise CostCenterStatusAccount("Estado de la cuenta no activo")

    @property
    def _get_info_account(self) -> Dict[str, Any]:
        return cuenta.objects.select_related(
            'persona_cuenta'
        ).filter(
            persona_cuenta_id=self._cost_center_id,
            is_active=True
        ).values(
            'id',
            'cuentaclave',
            'monto'
        ).first()

    @property
    def _get_info_cost_center(self) -> Dict[str, Any]:
        return persona.objects.filter(
            id=self._cost_center_id,
            state=True,
            is_active=True
        ).values('id', 'name', 'rfc').first()

    @property
    def _get_info_admin(self) -> Dict[str, Any]:
        return {
            "id": self._admin.get_only_id(),
            "name": f"{self._admin.get_full_name()}",
            "email": self._admin.get_email()
        }


class CreateTransaction:
    _serializer_class: ClassVar[SerializerTransactionToThirdPerson] = SerializerTransactionToThirdPerson

    def __init__(
            self,
            request_data: RequestDataTransactionIndividual,
            emisor: GetInfoEmisorCostCenter,
            cuenta_eje: grupoPersona
    ):
        self._request_data = request_data
        self._emisor = emisor
        self._cuenta_eje = cuenta_eje
        self._create()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
            "empresa": self._cuenta_eje.company_details.get('name_stp'),
            "cuenta_emisor": self._emisor.info_account.get('cuentaclave'),
            "nombre_emisor": self._emisor.info_cost_center.get('name'),
            "cuenta_id": self._emisor.info_account.get('id'),
            "emisor_empresa_id": self._emisor.info_admin.get('id'),
            "monto_emisor": self._emisor.info_account.get('monto')
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "nombre_beneficiario": self._request_data.get_nombre_beneficiario,
            "email": self._request_data.get_email,
            "rfc_curp_beneficiario": self._request_data.get_rfc_curp_beneficiario,
            "cuenta_beneficiario": self._request_data.get_cuenta_beneficiario,
            "monto": self._request_data.get_monto,
            "banco_beneficiario_id": self._request_data.get_banco_beneficiario_id,
            "referencia_numerica": self._request_data.get_referencia_numerica,
            "concepto_pago": self._request_data.get_concepto_pago
        }

    def _create(self) -> NoReturn:
        print(self._context)
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.create()


class CreateContact:
    def __init__(self, request_data: RequestDataTransactionIndividual, emisor: GetInfoEmisorCostCenter):
        self._request_data = request_data
        self._emisor = emisor

        contacto = contactos.objects.filter(person_id=self._emisor.info_cost_center.get('id'), cuenta=self._request_data.get_cuenta_beneficiario, tipo_contacto_id=2)

        if request_data.is_frecuent:
            if contacto:
                err = MyHttpError('Ya existe un contacto frecuente registrado con esta cuenta', real_error=None)
                raise ValidationError(err.standard_error_responses())

            self._create()
            self._create_historico_contacto()

    def _create(self) -> NoReturn:
        contactos.objects.create_contact(
            clabe=self._request_data.get_cuenta_beneficiario,
            alias=self._request_data.get_alias,
            nombre=self._request_data.get_nombre_beneficiario,
            banco_id=self._request_data.get_banco_beneficiario_id,
            persona_id=self._emisor.info_cost_center.get('id'),
            email=self._request_data.get_email,
            rfc_beneficiario=self._request_data.get_rfc_curp_beneficiario,
            tipo_contacto_id=2
        )

    def _create_historico_contacto(self) -> NoReturn:
        contacto = contactos.objects.last()
        HistoricoContactos.objects.create(
            fechaRegistro=datetime.datetime.now(),
            contactoRel_id=contacto.id,
            operacion_id=1,
            usuario_id=self._emisor.info_cost_center.get('id')
        )


# (ChrGil 2022-02-02) Crear una transacción a terceros individual
# Endpoint: http://127.0.0.1:8000/transaction/web/v2/TraPolThi/Create/
class CreateTransactionToThirdPerson(viewsets.GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear transacción individual a terceros"]

    def create(self, request):
        try:
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                              objJsonRequest=self.request.data)

            admin: persona = request.user
            cost_center_id: int = self.request.query_params['cost_center_id']
            cuenta_eje: grupoPersona = get_instance_grupo_persona(admin.get_only_id())

            with atomic():
                request_data = RequestDataTransactionIndividual(request.data)
                # ValidateTokenDynamic(request_data.get_token_dynamic, admin)
                emisor = GetInfoEmisorCostCenter(cost_center_id, admin)
                CreateTransaction(request_data, emisor, cuenta_eje)
                CreateContact(request_data, emisor)

        except (CostCenterException, JwtDynamicTokenException) as e:
            err = MyHttpError('Oucrrio un error en tu operación actual', real_error=e.message)
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=err)
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except (ValueError, IntegrityError, ObjectDoesNotExist, TypeError) as e:
            err = MyHttpError('Oucrrio un error en tu operación actual', real_error=str(e))
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=err)
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        else:
            succ = MyHtppSuccess("Tu operación se realizo de manera satisfactoria", code=str(201))
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=succ)
            return Response(succ.standard_success_responses(), status=status.HTTP_201_CREATED)


@dataclass
class ResquestDataAuthTransactionIndividual:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_token_dynamic(self) -> str:
        return self._request_data.get('auth').get('token')


class GetInfoEmisorTransaction(EmisorTransaction):
    def __init__(self, transaction_id: int, admin: persona):
        self._transaction_id = transaction_id
        self._admin = admin

        self.info_transaction = self._get_info_transaction
        self.info_transaction_stp = self._get_info_transaction_stp
        self.info_admin = self._get_info_admin

        if not self.info_transaction:
            raise TransactionDoestNotExists('No existe una transacción asociada a ese id')

    @property
    def _get_info_transaction(self) -> Dict[str, Any]:
        return transferencia.objects.select_related(
            'cuentatransferencia',
            'status_trans',
            'emisor_empresa'
        ).filter(id=self._transaction_id).values(
            'id',
            'monto',
            'concepto_pago',
            'status_trans_id',
            'emisor_empresa__email',
            'cuentatransferencia_id',
            'cuentatransferencia__persona_cuenta_id',
            'cuentatransferencia__monto',
            'emisor_empresa__email',
            'emisor_empresa__name',
            'concepto_pago',
            'user_autorizada_id'
        ).first()

    @property
    def _get_info_admin(self) -> Dict[str, Any]:
        return {
            "id": self._admin.get_only_id(),
            "name": f"{self._admin.name} {remove_asterisk(self._admin.last_name)}",
            "email": self._admin.get_email()
        }

    @property
    def _get_info_transaction_stp(self) -> Dict[str, Any]:
        return transferencia.objects.select_related(
            'receiving_bank',
            'transmitter_bank',
            'cuentatransferencia'
        ).filter(
            id=self._transaction_id
        ).values(
            'id',
            'clave_rastreo',
            'concepto_pago',
            'cta_beneficiario',
            'cuenta_emisor',
            'empresa',
            'receiving_bank__participante',
            'transmitter_bank__participante',
            'monto',
            'nombre_beneficiario',
            'nombre_emisor',
            'referencia_numerica',
            'rfc_curp_beneficiario',
            't_ctaBeneficiario',
            't_ctaEmisor',
            'cuentatransferencia__persona_cuenta__rfc',
            'tipo_pago',
        ).first()


# (ChrGil 2022-02-03) Retira el monto de la transacción de la cuenta del emisor
class WithdrawMoney:
    saldo_remanente: ClassVar[float]

    def __init__(self, transaction: GetInfoEmisorTransaction):
        self._transaction = transaction
        self._update_account()

    def _update_account(self):
        self.saldo_remanente = cuenta.objects.withdraw_amount(
            owner=self._transaction.info_transaction.get('cuentatransferencia__persona_cuenta_id'),
            amount=self._transaction.info_transaction.get('monto')
        )


# (ChrGil 2022-02-03) Cambia el estado de una transacción, si se autoriza o se cancela
class ChangeStatusTransactionIndividual:
    _serializer_class: ClassVar[SerializerAuthorizeTransaction] = SerializerAuthorizeTransaction

    def __init__(self, emisor: GetInfoEmisorTransaction, emisor_account: WithdrawMoney):
        self._emisor = emisor
        self._emisor_account = emisor_account
        self._update()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "admin": self._emisor.info_admin,
            "transaction_info": self._emisor.info_transaction,
            "saldo_remanente": self._emisor_account.saldo_remanente
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "status_trans_id": self._emisor.info_transaction.get('status_trans_id')
        }

    def _update(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.update()


# (ChrGil 2022-02-03) Autorizar una transacción individual
# Endpoint: http://127.0.0.1:8000/transaction/web/v3/AutTraPol/update/?demo_bool=True&transaction_id=18520
class AuthorizeTransactionPolipayToThird(UpdateAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Autorizar transacciones individuales a terceros"]

    def update(self, request, *args, **kwargs):
        try:
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                              objJsonRequest=self.request.data)
            admin: persona = request.user
            demo_bool: bool = request.query_params['demo_bool']
            transaction_id = request.query_params['transaction_id']

            with atomic():
                request_data = ResquestDataAuthTransactionIndividual(request.data)
                # ValidateTokenDynamic(request_data.get_token_dynamic, admin)

                transaction = GetInfoEmisorTransaction(transaction_id, admin)
                withdraw_money = WithdrawMoney(transaction)
                ChangeStatusTransactionIndividual(transaction, withdraw_money)

                # signature_stp = SignatureTestAPIStpIndividual(transaction)
                # api = CosumeAPISTP(signature_stp.json_data_registra_orden, demo_bool=demo_bool)
                # SetFolioOpetacionSTP(api.response, signature_stp.json_data_registra_orden.get('claveRastreo'))

                message = "La dispersión fue autorizada exitosamente. El estado a cambiado a en proceso"
                succ = MyHtppSuccess(message=message)
                RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                                  objJsonRequest=succ)
                return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

        except (TransactionException, CostCenterException, JwtDynamicTokenException) as e:
            err = MyHttpError(message="Ocurrio un error durante el proceso de autorización", real_error=e.message)
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=err)
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            message = "Recurso no encontrado"
            err = MyHttpError(message=message, real_error=str(e), code=404)
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=err)
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except (TypeError, ValueError, IntegrityError, MultiValueDictKeyError) as e:
            message = "Ocurrio un error durante el proceso de autorización de una transacción masiva"
            err = MyHttpError(message=message, real_error=str(e))
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=err)
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except StpmexException as e:
            message = "Lo Sentimos, se produjo un error. Inténtalo de nuevo más tarde"
            err = MyHttpError(message=message, real_error=e.msg, error_desc=e.desc)
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=err)
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


class RequestDataCancelTransactionIndividual:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def get_token_dynamic(self) -> str:
        return self._request_data.get('auth').get('token')


# (ManuelCalixtro 25/11/2021 Endpoint para cancelar una transaccion individual Polipay a Terceros)
class CancelTransactionPolipayToThird(viewsets.GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Cancelar transacciones individuales a terceros"]

    def create(self):
        pass

    def put(self, request):
        log = RegisterLog(request.user, request)
        try:
            admin: persona = self.request.user
            transaction_id = self.request.query_params['transaction_id']
            get_transaction = transferencia.objects.get(id=transaction_id, tipo_pago_id=2)
            cuenta_emisor = cuenta.objects.get(cuentaclave=get_transaction.cuenta_emisor)
            persona_emisor_email = persona.objects.get(id=get_transaction.emisor_empresa_id).get_email()
            log.json_request(request.query_params)

            # request_data = RequestDataCancelTransactionIndividual(request.data)
            # ValidateTokenDynamic(request_data.get_token_dynamic, admin)

            context = {
                'user_cancelar': admin.get_full_name(),
                'person_emisor_email': persona_emisor_email,
                'status_trans': get_transaction.status_trans_id,
                'cuenta_emisor': cuenta_emisor,
                'log': log
            }

            serializer = SerializerCancelTransaction(data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
            serializer.update(get_transaction, serializer.validated_data)
            R = {'code': 201, 'status': 'success', 'message': 'Tu operación se realizo de manera satisfactoria'}
            log.json_response(R)
            return Response(R, status=status.HTTP_200_OK)

        except JwtDynamicTokenException as e:
            err = MyHttpError('Oucrrio un error en tu operación actual', real_error=e.message)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            err = MyHttpError('Oucrrio un error en tu operación actual', real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)


# (ManuelCalixtro 09/12/2021 Se creo endpoint para crear transaccion polipay a polipay falta el token dinamico)
class CreateTransactionPolipayToPolipay(viewsets.GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear transacción polipay a polipay"]
    serializer_class = SerializerCreateTransactionPolipayToPolipay

    def create(self, request):
        log = RegisterLog(request.user, request)
        try:
            cost_center_id: int = request.query_params['cost_center_id']
            cost_center = grupoPersona.objects.get(empresa_id=cost_center_id, relacion_grupo_id=4).get_empresa()
            admin_person: persona = self.request.user
            instance_cuenta_emisor = cuenta.objects.get(persona_cuenta_id=cost_center['id'])
            log.json_request(request.data)

            context = {
                'empresa': cost_center['name'],
                'nombre_emisor': cost_center['name'],
                'empresa_emisor': admin_person.get_only_id(),
                'email_emisor': admin_person.get_email(),
                'cuenta_emisor': instance_cuenta_emisor,
                'cost_center': cost_center,
                'empresa_id': cost_center['id'],
                'log': log
            }

            with atomic():
                # (ChrGil 2021-12-30) Se agrega token dinamico
                data: Dict[str, Any] = request.data
                ValidateTokenDynamic(data.get('auth').get('token'), admin_person)

                serializer = self.serializer_class(data=request.data, context=context)
                serializer.is_valid(raise_exception=True)
                serializer.create()

                succ = MyHtppSuccess(message='Tu operación se realizo de manera satisfactoria', code='201')
                log.json_response(succ.standard_success_responses())
                return Response(succ.standard_success_responses(), status=status.HTTP_201_CREATED)

        except (ObjectDoesNotExist, IntegrityError, ValueError, KeyError) as e:
            err = MyHttpError(message='Ingrese un ID de centro de costos valido', real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


# (ManuelCalixtro 09/12/2021 Endpoint para listar transacciones polipay a polipay enviadas con filtro)
class ListTransactionPolipayToPolipaySend(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver transacciones polipay a polipay enviadas"]

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)

        cost_center_id = self.request.query_params['cost_center_id']
        nombre_beneficiario = self.request.query_params['nombre_beneficiario']
        date1 = self.request.query_params['start_date']
        date2 = self.request.query_params['end_date']
        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size
        log.json_request(request.data)

        person_emisor_transaction = persona.objects.get(id=cost_center_id)
        account_instance = cuenta.objects.filter(persona_cuenta=person_emisor_transaction).first()
        transferencia_instance = transferencia.filter_transaction.transactions_polipay_to_polipay_send(
            nombre_beneficiario, date1, date2, account_instance)

        page = self.paginate_queryset(transferencia_instance)
        log.json_response(page)
        return self.get_paginated_response(page)


# (ManuelCalixtro 09/12/2021 Endpoint para listar transacciones polipay a polipay recibidas con filtro)
class ListTransactionPolipayToPolipayReceived(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver transacciones polipay a polipay recibidas"]

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)

        cost_center_id = self.request.query_params['cost_center_id']
        nombre_emisor = self.request.query_params['nombre_emisor']
        date1 = self.request.query_params['start_date']
        date2 = self.request.query_params['end_date']

        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size
        log.json_request(request.query_params)

        person_beneficario_transaction = persona.objects.get(id=cost_center_id)
        account_instance = get_Object_orList_error(cuenta, persona_cuenta=person_beneficario_transaction)

        transferencia_instance = transferencia.filter_transaction.transactions_polipay_to_polipay_received(
            nombre_emisor, date1, date2, account_instance)

        page = self.paginate_queryset(transferencia_instance)
        log.json_response(page)
        return self.get_paginated_response(page)


# (ManuelCalixtro 09/12/2021 Endpoint para ver detalles de transacciones polipay a polipay)
class DetailTransactionPolipayToPolipaySend(RetrieveAPIView):
    serializer_class = serializerDetailTransactionPolipayToPolipaySend

    def get(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)

        id = self.request.query_params['transferencia']
        queryset = transferencia.objects.filter(id=id)
        log.json_request(request.query_params)

        context = {
            "instance_cta_benef": queryset
        }

        serializer = self.serializer_class(instance=queryset, many=True, context=context)
        log.json_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# (ManuelCalixtro 04/01/2022) Endpoint para crear transacciones entre cuentas propias
class CreateTransactionBetweenOwnAccounts(viewsets.GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear transacción entre centros de costo"]

    serializer_class = SerializerCreateTransactionBetweenOwnAccounts

    def create(self, request):
        log = RegisterLog(request.user, request)

        nombre_emisor: persona = self.request.user

        context = {
            'nombre_emisor': nombre_emisor.get_full_name(),
            'request': self.request,
            'request_user': nombre_emisor.id,
            'log': log
        }

        log.json_request(request.data)
        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.create()

        succ = {'code': 201, 'status': 'success', 'message': 'Tu operación se realizo de manera satisfactoria'}
        log.json_response(succ)
        return Response(succ, status=status.HTTP_200_OK)


# (ManuelCalixtro 04/01/2022) Endpoint para listar las transacciones entre cuentas propias con filtro
class ListTransactionBeetweenOwnAccounts(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver transacciones entre centros de costo enviadas"]

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)

        cuenta_eje_id = self.request.query_params['company_id']
        empresa = self.request.query_params['origin_account']
        date1 = self.request.query_params['start_date']
        date2 = self.request.query_params['end_date']

        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size
        log.json_request(request.query_params)

        get_cost_center = grupoPersona.objects.get_list_actives_cost_centers_id(cuenta_eje_id)
        account_instance = cuenta.objects.filter_only_account_cost_centers(get_cost_center)

        list_of_account_numbers = []

        for i in account_instance:
            list_of_account_numbers.append(i['cuenta'])

        get_transactions = transferencia.filter_transaction.transactions_own_accounts(empresa, date1, date2,
                                                                                      list_of_account_numbers)

        page = self.paginate_queryset(get_transactions)
        return self.get_paginated_response(page)


# (ManuelCalixtro 04/01/2022) Endpoint para ver detalles de una transaccion entre cuentas propias
class DetailTransactionOwnAccounts(RetrieveAPIView):

    def get(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)

        transaction_id = self.request.query_params['transaction_id']
        log.json_request(request.query_params)
        get_transaction = transferencia.objects.filter(id=transaction_id, tipo_pago_id=7).values(
            'id',
            'nombre_beneficiario',
            'cta_beneficiario',
            'empresa',
            'cuenta_emisor',
            'monto',
            'concepto_pago',
            'fecha_creacion',
            'tipo_pago__nombre_tipo',
            'nombre_emisor'
        )
        return Response(get_transaction)


# (ManuelCalixtro 04/01/2022) Endpoint para listar los movientos entre cuentas propias para el dashboard
class ListTransactionOwnAccounts(ListAPIView):
    serializer_class = SerializerDashboardAdmin

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request):
        log = RegisterLog(request.user, request)
        pk = self.request.query_params["centro_costo"]
        log.json_request(request.query_params)

        serializer = self.serializer_class(data=self.request.query_params, context=request)
        serializer.is_valid(raise_exception=True)
        objJson = serializer.getTransactionSummary(serializer.validated_data)
        return Response(objJson, status=status.HTTP_200_OK)


# (ManuelCalixtro 16-05-2022) Generador de comprobante PDF para transferencias
class ComprobanteTransferPolipayToThird(GenericViewSet):
    serializer_class = SerializerDocIndIn

    def create(self, request):
        log = RegisterLog(request.user, request)
        context = {"admin_id": request.user.get_only_id()}
        log.json_request(request.data)
        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        documento = serializer.create(serializer.validated_data)
        log.json_response(documento.data)
        return Response(documento.data, status=status.HTTP_200_OK)


# (ManuelCalixtro 16-05-2022) Buscador de cuentas para transacciones de polipay a polipay
class FilterAccountsCostCenters(ListAPIView):

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        number_cuenta = self.request.query_params['cuenta']
        log.json_request(request.query_params)

        cost_centers = grupoPersona.objects.select_related(
            'empresa', 'person', 'relacion_grupo'
        ).filter(relacion_grupo_id__in=[5,9], empresa__is_active=True, empresa__state=True, person__is_active=True, person__state=True).values('person__id')
        accounts_cost_center = cuenta.objects.filter_account_transaction_cost_centers(cost_centers, number_cuenta)

        return Response(accounts_cost_center)
