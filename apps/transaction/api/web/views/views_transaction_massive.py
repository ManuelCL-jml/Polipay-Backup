import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, ClassVar, NoReturn, Union

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.transaction import atomic
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.serializers import Serializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView

from MANAGEMENT.AlgSTP.GenerarFirmaSTP import RegistraOrdenDataSTP, GetPriKey, GeneraFirma, SignatureCertSTP
from MANAGEMENT.Utils.utils import get_values_list, remove_asterisk
from apps.api_dynamic_token.api.web.views.views_dynamic_token import ValidateTokenDynamic
from apps.api_dynamic_token.exc import JwtDynamicTokenException
from apps.api_stp.client import CosumeAPISTP
from apps.api_stp.exc import StpmexException
from apps.api_stp.interface import EmisorTransaction, ChangeStatusTransactionMassive, Transaction, \
    CreateTransactionMassive, CreateTransactionIndividualMassive
from apps.api_stp.management import SetFolioOpetacionSTP
from apps.api_stp.signature import SignatureMassiveTestAPIStp
from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from apps.transaction.constants import ConstantsTransaction
from apps.users.management import get_data_empresa
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from apps.transaction.management import to_dict_query_params
from apps.users.models import grupoPersona, cuenta, persona
from apps.transaction.models import transferencia, transmasivaprod, TransMasivaProg, detalleTransferencia
from apps.transaction.api.web.serializers.serialize_transaction import (
    SerializerMassTransfer,
    SerializerTransMasivaProg,
    SerializerAuthorizateTransaction,
    SerializerCancelTransaction,
    SerializerIndividualTransaction
)


class RequestDataTransactionMassive:
    info_account_cost_center: ClassVar[Dict[str, Any]]
    info_cost_center: ClassVar[Dict[str, Any]]
    _request_data: ClassVar[Dict[str, Any]]

    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data
        self.info_account_cost_center = self._get_info_account_cost_center
        self.info_cost_center = self._get_info_cost_center

    @property
    def get_observation(self) -> str:
        return self._request_data.get('observations')

    @property
    def get_layout_file(self) -> str:
        return self._request_data.get('LayoutFile')

    @property
    def get_cost_center_id(self) -> int:
        return int(self._request_data.get('CostCenter'))

    @property
    def get_transfer_list(self) -> List[Dict]:
        return self._request_data.get('TransferList')

    @property
    def is_shedule(self):
        return self._request_data.get('programada')

    @property
    def get_fecha_programada(self) -> str:
        return f"{self._request_data.get('fechaProgramada')} 00:00:00"

    @property
    def get_monto_total(self) -> float:
        return sum(get_values_list('monto', self.get_transfer_list))

    @property
    def _get_info_account_cost_center(self) -> Dict[str, Any]:
        return cuenta.objects.filter(
            persona_cuenta_id=self.get_cost_center_id).values('id', 'monto', 'is_active', 'cuentaclave').first()

    @property
    def _get_info_cost_center(self) -> Dict[str, Any]:
        return persona.objects.filter(id=self.get_cost_center_id).values('id', 'name', 'rfc').first()

    @property
    def get_dynamic_token(self) -> str:
        return self._request_data.get('auth').get('token')


# (ChrGil 2021-11-03) Clase que se encarga de crear el registro de una transferencia masiva programada
class TransMasivaProgClass(Transaction):
    _serializer_class: ClassVar[SerializerTransMasivaProg] = SerializerTransMasivaProg

    def __init__(self, transaction: CreateTransactionMassive, request_data: RequestDataTransactionMassive):
        self._transaction = transaction
        self._request_data = request_data

        if transaction.is_shedule:
            self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "masivaReferida_id": self._transaction.massive_id,
            "fechaProgramada": self._request_data.get_fecha_programada,
            "fechaEjecucion": self._request_data.get_fecha_programada,
        }

    @property
    def _context(self) -> None:
        return None

    def _create(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.create()


# (ChrGil 2021-11-01) Clase que se encarga de crear una el identificador de una transacción masiva
@dataclass
class MassTransfer(CreateTransactionMassive):
    _status: ClassVar[int] = 2
    _serializer_class: ClassVar[SerializerMassTransfer] = SerializerMassTransfer

    def __init__(self, request_data: RequestDataTransactionMassive, admin: persona):
        self._request_data = request_data
        self._admin = admin
        self.is_shedule = request_data.is_shedule
        self._create()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "cost_center_id": self._request_data.get_cost_center_id
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "observations": self._request_data.get_observation,
            "status": self._status,
            "layout_file": self._request_data.get_layout_file,
            "user_admin_id": self._admin.get_only_id()
        }

    def _create(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        self.massive_id = serializer.create()


class CreateIndividualTransaction(Transaction):
    _serializer_class: ClassVar[SerializerIndividualTransaction] = SerializerIndividualTransaction
    obj_transaction: ClassVar[transferencia]

    def __init__(self, transaction_individual: Dict[str, Any], context_data: Dict[str, Any]):
        self._transaction_individual = transaction_individual
        self._context_data = context_data
        self._create()

    @property
    def _context(self) -> Dict[str, Any]:
        return self._context_data

    @property
    def _data(self) -> Dict[str, Any]:
        return self._transaction_individual

    def _create(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        self.obj_transaction = serializer.create()


# (ChrGil 2021-11-02) Clase que se encargara de crear una transacción individual de manera masiva
class TransactionIndividualMassive(CreateTransactionIndividualMassive):
    _tipo_pago: ClassVar[List[int]]
    _create_individual_transaction: ClassVar[CreateIndividualTransaction] = CreateIndividualTransaction

    def __init__(
            self,
            request_data: RequestDataTransactionMassive,
            massive_trans: CreateTransactionMassive,
            persona_emisor_id: int,
            constans: ConstantsTransaction
    ):
        self._request_data = request_data
        self._massive_trans = massive_trans
        self._persona_emisor_id = persona_emisor_id
        self._banks_in_db = constans.all_bancks
        self._tipo_pago = constans.get_list_tipo_transferencia_id()
        self._create()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "nombre_emisor": self._request_data.info_cost_center.get('name'),
            "cuenta_emisor": self._request_data.info_account_cost_center.get('cuentaclave'),
            "rfc_emisor": self._request_data.info_cost_center.get('rfc'),
            "cuentatransferencia_id": self._request_data.info_account_cost_center.get('id'),
            "monto_cuenta_emisor": self._request_data.info_account_cost_center.get('monto'),
            "emisor_empresa_id": self._persona_emisor_id,
            "monto_total": self._request_data.get_monto_total,
            "massive_trans_id": self._massive_trans.massive_id,
            "tipo_pago_id": self._tipo_pago,
            "programada": self._request_data.is_shedule,
            "banks": self._banks_in_db
        }

    @property
    def _data(self) -> List[Dict[str, Any]]:
        return self._request_data.get_transfer_list

    def _create(self) -> NoReturn:
        _list_objs: List[transferencia] = []

        for data in self._data:
            obj = self._create_individual_transaction(data, self._context)
            _list_objs.append(obj.obj_transaction)

        self._bulk_create_transaction(_list_objs)

    # (ChrGil 2021-11-03) Metodo que crea masivamente las transferencias
    def _bulk_create_transaction(self, objs: List[transferencia]) -> NoReturn:
        transferencia.objects.bulk_create(objs)


# (ChrGil 2021-11-01) Creación de una transferencia masiva
# Endpoint: http://127.0.0.1:8000/transaction/web/v3/MasTra/create/
class MassTransferGenericViewSet(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear transacción masiva a terceros"]

    def create(self, request):
        log = RegisterLog(request.user, request)
        try:
            person_instance: persona = request.user
            person_id = person_instance.get_only_id()

            with atomic():
                log.json_request(request.data)
                constans = ConstantsTransaction()
                request_data = RequestDataTransactionMassive(request.data)
                ValidateTokenDynamic(request_data.get_dynamic_token, person_instance)

                massive_trans = MassTransfer(request_data, person_instance)
                TransMasivaProgClass(massive_trans, request_data)
                TransactionIndividualMassive(request_data, massive_trans, person_id, constans)

        except (IntegrityError, TypeError, JwtDynamicTokenException) as e:
            message = "Ocurrio un error durante el proceso de creación de una transacción masiva"
            err = MyHttpError(message=message, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            message = "No se encontro el identificador del centro de costos en nuestro sistema"
            err = MyHttpError(message=message, real_error=str(e), code=400)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        succ = MyHtppSuccess(message="Tu operación se realizó satisfactoriamente")
        log.json_response(succ.standard_success_responses())
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


# (ChrGil 2021-11-07) Listado y filtrado de transferencias masivas
class ListTransMassiveStatus(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver transacciones masivas a terceros pendientes",
                "Ver transacciones masivas a terceros canceladas",
                "Ver transacciones masivas a terceros en proceso",
                "Ver transacciones masivas a terceros procesadas"]
    pagination_class = PageNumberPagination

    # (ChrGil 2021-11-07) Parametros URL (size, cost_center_id, status_id, start_date, end_date, observations)from django.utils.decorators import method_decorator
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.query_params)
            self.pagination_class.page_size = request.query_params['size']

            data = to_dict_query_params(request.query_params)
            cost_center_id: int = data.pop('cost_center_id')

            id: int = cuenta.objects.select_related('persona_cuenta').get(
                persona_cuenta_id=cost_center_id).get_only_id()
            list_masivo_trans_id: List[int] = transferencia.filter_transaction.list_only_massive_id(cuenta_id=id)
            queryset = transmasivaprod.objects.list_massive(list_masivo_trans_id, **data)

            page = self.paginate_queryset(queryset)
            return self.get_paginated_response(page)

        except MultiValueDictKeyError as e:
            err = MyHttpError("Asegurese de haber ingresado todos los parametros", real_error=str(e))
            log.json_response(err.multi_value_dict_key_error())
            return Response(err.multi_value_dict_key_error(), status=status.HTTP_400_BAD_REQUEST)

        except TypeError as e:
            err = MyHttpError("Los parametros de filtrado no coinciden con los esperados", str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            message = "El centro de costos que usted ingreso no existe"
            err = MyHttpError(message=message, real_error=str(e), code=404)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)


# (ChrGil 2021-11-07) Detallar transacciones masivas
class DetailTransactionMassive(ListAPIView):
    pagination_class = PageNumberPagination

    # (ChrGil 2021-11-07) Parametros URL (massive_id, size)
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.query_params)
            self.pagination_class.page_size = request.query_params['size']

            data = to_dict_query_params(request.query_params)
            queryset = transferencia.filter_transaction.detail_massive_transaction(**data)

            page = self.paginate_queryset(queryset)
            return self.get_paginated_response(page)

        except MultiValueDictKeyError as e:
            err = MyHttpError("Asegurese de haber ingresado todos los parametros", real_error=str(e))
            log.json_response(err.multi_value_dict_key_error())
            return Response(err.multi_value_dict_key_error(), status=status.HTTP_400_BAD_REQUEST)

        except TypeError as e:
            err = MyHttpError("Los parametros de filtrado no coinciden con los esperados", str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


# (ChrGil 2021-11-08) Detallar una transacción masiva (mostrar nombre del cliente, observaciones, fecha de dispersión)
class DetailInfoTransactionMassive(RetrieveAPIView):
    def retrieve(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.query_params)
            massive_id: int = request.query_params['massive_id']
            cost_center_id: int = request.query_params['cost_center_id']
            data = transmasivaprod.objects.detail_info_transaction_massive(massive_id)
            company: str = grupoPersona.objects.select_related('empresa', 'relacion_grupo').get(
                empresa_id=cost_center_id, relacion_grupo_id=4).get_name_comany()
            data['cost_center'] = company

            log.json_response(data)
            return Response(data, status=status.HTTP_200_OK)

        except MultiValueDictKeyError as e:
            err = MyHttpError("Asegurese de haber ingresado todos los parametros", real_error=str(e))
            log.json_response(err.multi_value_dict_key_error())
            return Response(err.multi_value_dict_key_error(), status=status.HTTP_400_BAD_REQUEST)

        except TypeError as e:
            err = MyHttpError("Los parametros de filtrado no coinciden con los esperados", str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            message = "El centro de costos que usted ingreso no existe"
            err = MyHttpError(message=message, real_error=str(e), code=404)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)


@dataclass
class RequestDataChangeStatus:
    request_data: Dict[str, Any]

    @property
    def get_token_dynamic(self):
        return self.request_data.get('auth').get('token')


# (ChrGil 2022-01-15) Cancela o autoriza una transacción masiva
class ChangeStatus(ChangeStatusTransactionMassive):
    def __init__(
            self, request_data:
            RequestDataChangeStatus,
            serializer_class: Serializer(),
            massive_instance: transmasivaprod,
            admin_person: persona,
            is_shedule: bool,
            cost_center_emisor: Union[cuenta, None] = None
    ):
        self._request_data = request_data
        self._serializer_class = serializer_class
        self._massive_instance = massive_instance
        self._admin_person = admin_person
        self._is_shedule = is_shedule
        self._cost_center_emisor = cost_center_emisor
        self._change_status()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "admin_id": self._admin_person.get_only_id(),
            "is_shedule": self._is_shedule,
            "current_status": self._massive_instance.get_status(),
            "administrative": self._massive_instance.get_created_to_transaction_massive,
            "observations": self._massive_instance.get_observations(),
            "cost_center_emisor": self._cost_center_emisor
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "massive_id": self._massive_instance.get_only_id()
        }

    def _change_status(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        self.status_transaction = serializer.update()


# (ChrGil 2021-11-08) Cancelar transacciones masivas
class CancelBulkTransaction(UpdateAPIView):
    def update(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            massive: transmasivaprod = transmasivaprod.objects.get(id=request.query_params['massive_id'])
            is_shedule = TransMasivaProg.objects.transaction_is_shedule(massive_id=massive.get_only_id())
            admin_person: persona = request.user

            with atomic():
                log.json_request(request.data)
                request_data = RequestDataChangeStatus(request.data)
                # ValidateTokenDynamic(request_data.get_token_dynamic, admin_person)

                serializer = SerializerCancelTransaction
                instance = ChangeStatus(request_data, serializer, massive, admin_person, is_shedule)

            msg = f"La dispersión fue {instance.status_transaction} exitosamente"
            succ = MyHtppSuccess(message=msg, extra_data=massive.get_observations())
            log.json_response(succ.standard_success_responses())
            return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

        except MultiValueDictKeyError as e:
            err = MyHttpError("Asegurese de haber ingresado todos los parametros", real_error=str(e))
            log.json_response(err.multi_value_dict_key_error())
            return Response(err.multi_value_dict_key_error(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            message = "Recurso no encontrado"
            err = MyHttpError(message=message, real_error=str(e), code=404)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except (TypeError, JwtDynamicTokenException, AttributeError) as e:
            message = "Ocurrio un error durante el proceso de cancelación de una transacción masiva"
            err = MyHttpError(message=message, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


class GetInfoEmisor:
    info_account_emisor: ClassVar[Dict[str, Any]]
    info_admin: ClassVar[Dict[str, Any]]

    def __init__(self, cost_center_id: int, admin: persona):
        self._cost_center_id = cost_center_id
        self._admin = admin
        self.info_account_emisor = self._get_info_acount_cost_center
        self.info_admin = self._get_info_admin

    @property
    def _get_info_acount_cost_center(self) -> Dict[str, Any]:
        return cuenta.objects.filter(
            persona_cuenta_id=self._cost_center_id,
            persona_cuenta__state=True,
            persona_cuenta__is_active=True,
            is_active=True
        ).values(
            'id',
            'cuentaclave',
            'monto',
            'persona_cuenta_id'
        ).first()

    @property
    def _get_info_admin(self) -> Dict[str, Any]:
        return {
            "id": self._admin.get_only_id(),
            "name": f"{self._admin.name} {remove_asterisk(self._admin.last_name)}",
            "email": self._admin.get_email()
        }


class GetInfoTransactionMassive:
    info_massive: ClassVar[Dict[str, Any]]
    is_shedule: ClassVar[bool]
    total_amount: ClassVar[float]
    list_transaction_stp: ClassVar[List[Dict[str, Any]]]

    def __init__(self, massive_id: int):
        self._massive_id = massive_id
        self.info_massive = self._get_info_massive
        self.is_shedule = self._is_shedule
        self.total_amount = self._total_amount
        self.list_transaction_stp = self._get_list_transaction_stp

    @property
    def _get_info_massive(self):
        return transmasivaprod.objects.filter(
            id=self._massive_id
        ).values(
            'id',
            'observations',
            'statusRel_id'
        ).first()

    @property
    def _is_shedule(self) -> bool:
        return TransMasivaProg.objects.transaction_is_shedule(massive_id=self._massive_id)

    @property
    def _total_amount(self) -> float:
        return transferencia.filter_transaction.get_monto_total_masiva(self._massive_id)

    @property
    def _get_list_transaction_stp(self) -> List[Dict[str, Any]]:
        return transferencia.filter_transaction.get_info_transaction_stp(self._massive_id)


# (ChrGil 2022-02-03) Retira el monto de la transacción de la cuenta del emisor
class WithdrawAmount:
    saldo_remanente: ClassVar[float]

    def __init__(self, emisor: GetInfoEmisor, massive: GetInfoTransactionMassive):
        self._emisor = emisor
        self._massive = massive
        self._update_amount()

    def _update_amount(self):
        cuenta.objects.withdraw_amount(
            owner=self._emisor.info_account_emisor.get('persona_cuenta_id'),
            amount=self._total_amount
        )

    @property
    def _total_amount(self) -> float:
        return transferencia.filter_transaction.get_monto_total_masiva(self._massive.info_massive.get('id'))


class AuthTransactionMassive:
    _serializer_class: ClassVar[SerializerAuthorizateTransaction] = SerializerAuthorizateTransaction
    status: ClassVar[str]

    def __init__(self, emisor: GetInfoEmisor, massive: GetInfoTransactionMassive):
        self._emisor = emisor
        self._massive = massive
        self._update()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "admin_id": self._emisor.info_admin.get('id'),
            "name": self._emisor.info_admin.get('name'),
            "email": self._emisor.info_admin.get('email'),
            "is_shedule": self._massive.is_shedule,
            "current_status": self._massive.info_massive.get('statusRel_id'),
            "observations": self._massive.info_massive.get('observations'),
            "account_emisor_id": self._emisor.info_account_emisor.get('id'),
            "amount_emisor": self._emisor.info_account_emisor.get('monto'),
            "total_amount": self._massive.total_amount
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "massive_id": self._massive.info_massive.get('id')
        }

    def _update(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.update()
        self.status = serializer.status


class RegistraOrdenSTP:
    def __init__(self, list_data_stp: List[Dict[str, Any]], demo_bool: bool):
        self._list_data_stp = list_data_stp
        self._demo_bool = demo_bool
        self._consume_api()

    def _consume_api(self):
        for data in self._list_data_stp:
            try:
                api = CosumeAPISTP(data, demo_bool=self._demo_bool)
                SetFolioOpetacionSTP(api.response, data.get('claveRastreo'))
            except StpmexException as e:
                transferencia.objects.filter(
                    clave_rastreo=data.get('claveRastreo')
                ).update(
                    status_trans_id=7,
                    concepto_pago=e.desc,
                    date_modify=dt.datetime.now()
                )


# (ChrGil 2021-11-26) Autotizar transacción masiva
# Endpoint: http://127.0.0.1:8000/transaction/web/v3/AutBulTra/update/?massive_id=1185&cost_center_id=1660
class AuthorizeBulkTransaction(UpdateAPIView):
    def update(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            admin: persona = request.user
            # demo_bool: bool = request.query_params['demo_bool']
            massive_id: int = request.query_params['massive_id']
            cost_center_id: int = request.query_params['cost_center_id']

            with atomic():
                log.json_request(request.data)
                request_data = RequestDataChangeStatus(request.data)
                # ValidateTokenDynamic(request_data.get_token_dynamic, admin)
                emisor = GetInfoEmisor(cost_center_id, admin)
                massive = GetInfoTransactionMassive(massive_id)
                auth = AuthTransactionMassive(emisor, massive)

                # (ChrGil 2022-02-08) Se comenta de manera temporal
                # json_stp_data = SignatureMassiveTestAPIStp(massive.list_transaction_stp)
                # RegistraOrdenSTP(json_stp_data.json_data_registra_orden, demo_bool)
                WithdrawAmount(emisor, massive)

            message = f"La dispersión fue autorizada exitosamente. El estado a cambiado a {auth.status}"
            succ = MyHtppSuccess(message=message, extra_data=massive.info_massive.get('observations'))
            log.json_response(succ.standard_success_responses())
            return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            message = "Recurso no encontrado"
            err = MyHttpError(message=message, real_error=str(e), code=404)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except (TypeError, ValueError, JwtDynamicTokenException, MultiValueDictKeyError) as e:
            message = "Ocurrio un error durante el proceso de autorización de una transacción masiva"
            err = MyHttpError(message=message, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


class ShowDetailTransaction:
    def __init__(self, transaction_id: int):
        self._transaction_id = transaction_id
        self._transaction_detail = self._detail
        self.handler_error()
        self.transaction = self._render(**self._transaction_detail)

    def handler_error(self):
        if self._transaction_detail is None:
            raise ValueError('La transacción no existe')

    @property
    def motivo_devuelta(self) -> Dict[str, Any]:
        return detalleTransferencia.objects.filter(transferReferida_id=self._transaction_id).values('detalleT').first()

    def _render(self, **kwargs) -> Dict[str, Any]:
        return {
            "ClaveRastreo": kwargs.get('clave_rastreo'),
            "NombreBeneficiario": kwargs.get('nombre_beneficiario'),
            "CuentaBeneficiario": kwargs.get('cta_beneficiario'),
            "BancoDestino": kwargs.get('receiving_bank__institucion'),
            "BancoEmisor": kwargs.get('transmitter_bank__institucion'),
            "CuentaOrigen": kwargs.get('cuenta_emisor'),
            "Ordenante": kwargs.get('nombre_emisor'),
            "Monto": kwargs.get('monto'),
            "ConceptoPago": kwargs.get('concepto_pago'),
            "Referencia": kwargs.get('referencia_numerica'),
            "FechaOperacion": kwargs.get('date_modify'),
            "FechaCreacion": kwargs.get('fecha_creacion'),
            "Pago": kwargs.get('tipo_pago__nombre_tipo'),
            "CreadoNombre": kwargs.get('emisor_empresa__name'),
            "CreadoApellido": kwargs.get('emisor_empresa__last_name'),
            "Concepto": kwargs.get('concepto_pago'),
            "Modificado": kwargs.get('user_autorizada__name'),
            "SaldoRemanente": kwargs.get('saldo_remanente'),
            "EstadoActual": kwargs.get('status_trans__nombre'),
            "MotivoDevuelta": self.motivo_devuelta.get('detalleT') if self.motivo_devuelta else None
        }

    @property
    def _detail(self) -> Dict[str, Any]:
        return transferencia.objects.select_related(
            'tipo_pago',
            'user_autorizada',
            'cuentatransferencia',
            'transmitter_bank',
            'receiving_bank',
            'emisor_empresa',
            'status_trans'
        ).filter(id=self._transaction_id).values(
            'id',
            'clave_rastreo',
            'nombre_beneficiario',
            'cta_beneficiario',
            'receiving_bank__institucion',
            'transmitter_bank__institucion',
            'cuenta_emisor',
            'nombre_emisor',
            'monto',
            'concepto_pago',
            'referencia_numerica',
            'date_modify',
            'fecha_creacion',
            'tipo_pago__nombre_tipo',
            'emisor_empresa__name',
            'emisor_empresa__last_name',
            'concepto_pago',
            'user_autorizada__name',
            'user_autorizada__last_name',
            'saldo_remanente',
            'status_trans__nombre'
        ).first()


class ShowMoreDetailTransactionMassive(RetrieveAPIView):
    def retrieve(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.query_params)
            transaction_id: int = request.query_params['id']
            queryset = ShowDetailTransaction(transaction_id)
            # queryset = transferencia.filter_transaction.detail_massive_transaction_individual(transaction_id=id)
            log.json_response(queryset.transaction)
            return Response(queryset.transaction, status=status.HTTP_200_OK)

        except MultiValueDictKeyError as e:
            err = MyHttpError("Asegurese de haber ingresado todos los parametros", real_error=str(e))
            log.json_response(err.multi_value_dict_key_error())
            return Response(err.multi_value_dict_key_error(), status=status.HTTP_400_BAD_REQUEST)

        except TypeError as e:
            err = MyHttpError("Los parametros de filtrado no coinciden con los esperados", str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except (ObjectDoesNotExist, ValueError) as e:
            err = MyHttpError(message="Recurso no encontrado", real_error=str(e), code=404)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)
