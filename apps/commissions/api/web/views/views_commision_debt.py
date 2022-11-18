# Pago de comisiones adeudadas

import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, Union, List, Dict, Any, ClassVar, NoReturn
from decimal import Decimal

from django.db.models import QuerySet
from django.db.transaction import atomic

from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response

from MANAGEMENT.ComissionPay.comission import ComponentAllAdmin
from MANAGEMENT.Standard.errors_responses import MyHttpError
from apps.api_stp.client import CosumeAPISTP
from apps.api_stp.exc import StpmexException
from apps.api_stp.management import SetFolioOpetacionSTP
from apps.api_stp.signature import SignatureProductionAPIStpIndividualComissionPay
from apps.logspolipay.manager import RegisterLog
from apps.transaction.models import transferencia
from polipaynewConfig.settings import COST_CENTER_POLIPAY_COMISSION
from django.db.models import QuerySet, Q
from apps.commissions.models import Commission_detail
from MANAGEMENT.Utils.utils import obtener_dias_del_mes
from apps.users.models import grupoPersona, cuenta, persona


def to_list(queryset: QuerySet) -> List[Union[int, float, str, bool, Dict, Decimal]]:
    return list(queryset)


def get_last_month(datetime: dt.datetime) -> Tuple[dt.date, dt.date]:
    days_of_the_month = obtener_dias_del_mes(datetime.month - 1, datetime.year)
    last_month = datetime.date() - dt.timedelta(days=days_of_the_month)
    return last_month, datetime.date()


def _update_commision_detail(commision_id: int, commission: transferencia):
    Commission_detail.objects.filter(id=commision_id).update(commission_record=commission)


class PayCommisionPolipay(ABC):
    instance: ClassVar[transferencia]

    @staticmethod
    @abstractmethod
    def _saldo_remanente(monto_transaccion: float, monto_beneficiario: float) -> float:
        ...

    @staticmethod
    @abstractmethod
    def _data(**kwargs) -> Dict[str, Any]:
        ...

    @staticmethod
    @abstractmethod
    def _create(data) -> transferencia:
        ...


class RegistraOrdenSTPDispersion:
    _sing: ClassVar[SignatureProductionAPIStpIndividualComissionPay] = SignatureProductionAPIStpIndividualComissionPay
    _api: ClassVar[CosumeAPISTP] = CosumeAPISTP
    _folio_stp: ClassVar[SetFolioOpetacionSTP] = SetFolioOpetacionSTP

    def __init__(self, transaction: transferencia, demo_bool: bool = True):
        self.transaction = transaction
        self.data_email = None

        if transaction.monto > 0:
            self.transaction = transaction
            self.demo_bool = demo_bool
            self._put()

    def _put(self) -> NoReturn:
        json_stp_data = self._sing(self.transaction)
        print(json_stp_data.json_data_registra_orden)
        # api = self._api(json_stp_data.json_data_registra_orden, demo_bool=self.demo_bool)
        # self._folio_stp(api.response, json_stp_data.json_data_registra_orden.get('claveRastreo'))


# (ChrGil 2022-03-28) Lista todos los clientes
class ListAllClients:
    list_clients: ClassVar[List[int]]

    def __init__(self):
        self.list_clients = self.list_all_clients

    @property
    def list_all_clients(self) -> List[int]:
        queryset = grupoPersona.objects.select_related(
            'relacion_grupo'
        ).filter(
            relacion_grupo_id__in=[5, 9, 11],
            person__state=True,
            empresa__state=True
        ).values_list('person_id', flat=True)
        return to_list(queryset)


# (ChrGil 2022-03-28) Regresa la información de la razón social a donde se depositara la comisión
class InfoRazonSocialPolipayComission:
    _razon_social_id: ClassVar[int] = COST_CENTER_POLIPAY_COMISSION
    info: ClassVar[Dict[str, Any]]

    def __init__(self):
        self.info = self._get_info_polipay_comission

    @property
    def _get_info_polipay_comission(self) -> Dict[str, Any]:
        return cuenta.objects.get_info_polipay_comission(self._razon_social_id)


# (ChrGil 2022-03-28) Regresa la información del emisor, para realizar la transacción
class InfoEmisor:
    info: ClassVar[Dict[str, Any]]

    def __init__(self, client_id: int):
        self._client_id = client_id
        self.info = self._get_info_emisor

    @property
    def _get_info_emisor(self) -> Dict[str, Any]:
        return cuenta.objects.get_info_polipay_comission(self._client_id)


# (ChrGil 2022-03-28) Realiza los movimientos bancarios, retirando el monto de la cuenta del emisor
# (ChrGil 2022-03-28) y despositando ese mismo monto a la cuenta del beneficiario
class Movements:
    _razon_social_id: ClassVar[int] = COST_CENTER_POLIPAY_COMISSION

    def __init__(self, client_id: int, amount: Union[Decimal, float]):
        self._client_id = client_id
        self._amount = amount
        self.withdraw_amount_client()
        self.deposit_amount_comission()

    def withdraw_amount_client(self):
        cuenta.objects.withdraw_amount(self._client_id, self._amount)

    def deposit_amount_comission(self):
        cuenta.objects.deposit_amount(self._razon_social_id, self._amount)


# (ChrGil 2022-03-28) Caldula la comisión a pagar
# class CalculateComission:
#     total_amount: ClassVar[List[Decimal]]
#
#     def __init__(self, client_id: int, datetime: dt.datetime):
#         self._client = client_id
#         self.datetime = datetime
#         self.total_amount = self.sum_amount_comission(self.list_comission_client)
#
#     @staticmethod
#     def sum_amount_comission(comission_list: Union[List, QuerySet]) -> Union[float, None]:
#         if comission_list:
#             return float(sum(comission_list))
#         return None
#
#     @property
#     def list_comission_client(self) -> List[Decimal]:
#         queryset = Commission_detail.objects.select_related('status', 'transaction_rel', 'commission').filter(
#             status_id=3,
#             transaction_rel__cuentatransferencia__persona_cuenta_id=self._client
#         ).values_list("mount", flat=True)
#
#         return to_list(queryset)

# (ChrGil 2022-03-28) Caldula la comisión a pagar
class CalculateComission:
    total_amount: ClassVar[List[Decimal]]

    def __init__(self, client_id: int, datetime: dt.datetime):
        self._client = client_id
        self.datetime = datetime
        list_comission_info = self.list_comission_info

        if list_comission_info:
            self.commision_info = list_comission_info

    @property
    def list_comission_info(self) -> List[Dict]:
        _start_date, _end_date = get_last_month(self.datetime)
        queryset = Commission_detail.objects.commission_detail_list(
            status=3,
            client_id=self._client,
            start_date=_start_date,
            end_date=_end_date
        )
        return to_list(queryset)


class ChangeStatusComission:
    def __init__(self, commision_id: int, datetime: dt.datetime, status_id: int):
        self.commision_id = commision_id
        self.datetime = datetime
        self.status_id = status_id
        self.change_status_comission()

    def change_status_comission(self) -> bool:
        Commission_detail.objects.select_related('status', 'transaction_rel', 'commission').filter(
            id=self.commision_id
        ).update(
            status_id=self.status_id,
            payment_date=dt.datetime.now()
        )
        return True


# (ChrGil 2022-03-29) Realiza el movimiento del cobro de la comisión
class TransferComissionToPolipayComission:
    def __init__(self, polipay_comission: InfoRazonSocialPolipayComission, emisor: InfoEmisor, amount: float):
        self._polipay_comission = polipay_comission.info
        self._emisor = emisor.info
        self._amount_comission = amount
        self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "empresa": self._polipay_comission.get('persona_cuenta__name'),
            "monto": self._amount_comission,
            "nombre_emisor": self._emisor.get('persona_cuenta__name'),
            "cuenta_emisor": self._emisor.get('cuentaclave'),
            "rfc_curp_emisor": self._emisor.get('persona_cuenta__rfc'),
            "nombre_beneficiario": self._polipay_comission.get('persona_cuenta__name'),
            "cta_beneficiario": self._polipay_comission.get('cuentaclave'),
            "rfc_curp_beneficiario": self._polipay_comission.get('persona_cuenta__rfc'),
            "cuentatransferencia_id": self._emisor.get('id'),
            "concepto_pago": "COBRO COMISIÓN ADEUDADA",
            "saldo_remanente": self._emisor.get('monto'),
        }

    def _create(self) -> NoReturn:
        transferencia.objects.tranfer_to_polipay_comission(**self._data)


# (ChrGil 2022-03-30) Desactiva las cuentas de todos los administrativos y colaboradores
class DesactiveAccountAdmin:
    def __init__(self, client_id: int):
        self.client_id = client_id
        self.descative_admin()

    @property
    def _get_cost_center_id(self) -> Dict[str, Any]:
        return grupoPersona.objects.select_related('person', 'empresa', 'relacion_grupo').filter(
            Q(person_id=self.client_id) | Q(empresa_id=self.client_id)
        ).filter(
            relacion_grupo_id__in=[4, 9, 11],
        ).values('empresa_id', 'relacion_grupo_id').first()

    @property
    def _get_cuenta_eje_id(self) -> Dict[str, Any]:
        return grupoPersona.objects.filter(
            person_id=self._get_cost_center_id.get('empresa_id'),
            relacion_grupo_id=5
        ).values('empresa_id').first()

    @property
    def _get_all_admin(self) -> List[int]:
        return grupoPersona.objects.filter(
            empresa_id=self._get_cuenta_eje_id.get('empresa_id'),
            relacion_grupo_id__in=[1, 3, 14]
        ).values_list('person_id', flat=True)

    def descative_admin(self):
        persona.objects.filter(
            id__in=self._get_all_admin
        ).update(state=False, date_modify=dt.datetime.now(), motivo='La Comisión no ha sido pagada')


# (ChrGil 2022-03-31) activa las cuentas de todos los administrativos y colaboradores
class ActivateAccountAdmin:
    def __init__(self, client_id: int):
        self.client_id = client_id
        self.descative_admin()

    @property
    def _get_cost_center_id(self) -> Dict[str, Any]:
        return grupoPersona.objects.select_related('person', 'empresa', 'relacion_grupo').filter(
            Q(person_id=self.client_id) | Q(empresa_id=self.client_id)
        ).filter(
            relacion_grupo_id__in=[4, 9, 11],
        ).values('empresa_id', 'relacion_grupo_id').first()

    @property
    def _get_cuenta_eje_id(self) -> Dict[str, Any]:
        return grupoPersona.objects.filter(
            person_id=self._get_cost_center_id.get('empresa_id'),
            relacion_grupo_id=5
        ).values('empresa_id').first()

    @property
    def _get_all_admin(self) -> List[int]:
        return grupoPersona.objects.filter(
            empresa_id=self._get_cuenta_eje_id.get('empresa_id'),
            relacion_grupo_id__in=[1, 3, 14]
        ).values_list('person_id', flat=True)

    def descative_admin(self):
        persona.objects.filter(
            id__in=self._get_all_admin
        ).update(state=True, date_modify=dt.datetime.now(), motivo=None)


# class PositiveComission:
#     _calculate_comission: ClassVar[CalculateComission] = CalculateComission
#     _movements: ClassVar[Movements] = Movements
#     _change_status_comission: ClassVar[ChangeStatusComission] = ChangeStatusComission
#     _transaction: ClassVar[TransferComissionToPolipayComission] = TransferComissionToPolipayComission
#     _info_emisor: ClassVar[InfoEmisor] = InfoEmisor
#     _desactive_account_admin: ClassVar[DesactiveAccountAdmin] = DesactiveAccountAdmin
#     _activate_account_admin: ClassVar[ActivateAccountAdmin] = ActivateAccountAdmin
#
#     def __init__(self, clients: ListAllClients):
#         self.clients = clients.list_clients
#         self.now = dt.datetime.now()
#         self.beneficiario = InfoRazonSocialPolipayComission
#         self.comission()
#
#     @staticmethod
#     def tiempo_limite(datetime: dt.datetime) -> dt.date:
#         days = (dt.timedelta(days=obtener_dias_del_mes(datetime.month, datetime.year)).days - datetime.day) + 1
#         return datetime.date() + dt.timedelta(days=days)
#
#     @staticmethod
#     def get_info_account_client(client_id: int) -> Dict[str, Any]:
#         return cuenta.objects.filter(persona_cuenta_id=client_id).values('id', 'monto', 'persona_cuenta_id').first()
#
#     def amount_handler(self, data: Dict[str, Any], amount: float, client_id: int):
#         if amount < data.get('monto'):
#             # self._movements(client_id, amount)
#             # self._transaction(self.beneficiario(), self._info_emisor(client_id), amount)
#             # self._change_status_comission(client_id, self.now, status_id=1)
#             # self._activate_account_admin(client_id)
#             print("Cuentas activadas")
#
#         if data.get('monto') == 0.0:
#             # self._change_status_comission(client_id, self.now, status_id=3)
#             if self.tiempo_limite(dt.datetime.now()) == dt.date(2022, 4, 1):
#                 # self._desactive_account_admin(client_id)
#                 print("Cuentas Descativadas")
#
#         if amount > data.get('monto'):
#             # self._change_status_comission(client_id, self.now, status_id=3)
#             if self.tiempo_limite(dt.datetime.now()) == dt.date(2022, 4, 1):
#                 # self._desactive_account_admin(client_id)
#                 print("Cuentas Descativadas")
#
#     def comission(self):
#         clients = self.clients
#
#         for i in range(0, len(clients)):
#             client_id: int = clients[i]
#             _comission = self._calculate_comission(client_id, self.now).total_amount
#
#             if not _comission:
#                 continue
#
#             if _comission:
#                 _info_account = self.get_info_account_client(client_id)
#                 self.amount_handler(_info_account, _comission, client_id)

class TransferComissionTransactionIn(PayCommisionPolipay):
    """ Realiza el cobro de una comisión si es una transacción recibida """

    _registra_orden: ClassVar[RegistraOrdenSTPDispersion] = RegistraOrdenSTPDispersion

    def __init__(self, polipay_comission: InfoRazonSocialPolipayComission, data: Dict[str, Any]):
        self.polipay_comission = polipay_comission
        self.status_trans_id = 3
        self.instance = None
        self.data = data

        if self.data.get("transaction_rel__tipo_pago_id") == 5:
            _data_serializer = self._data(**self.data, **self.polipay_comission.info)
            instance = self._create(_data_serializer)
            self._registra_orden(instance)
            _update_commision_detail(self.data.get("id"), instance)

    @staticmethod
    def _saldo_remanente(monto_transaccion: float, monto_beneficiario: float) -> float:
        monto_beneficiario += monto_transaccion
        return monto_beneficiario

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "empresa": kwargs.get("transaction_rel__empresa", "ND"),
            "monto": float(kwargs.get("mount", "ND")),
            "nombre_emisor": kwargs.get("transaction_rel__nombre_beneficiario", "ND"),
            "cuenta_emisor": kwargs.get("transaction_rel__cta_beneficiario", "ND"),
            "rfc_curp_emisor": kwargs.get("transaction_rel__rfc_curp_beneficiario", "ND"),
            "nombre_beneficiario": kwargs.get("persona_cuenta__name", "ND"),
            "cta_beneficiario": kwargs.get("persona_cuenta__rfc", "ND"),
            "rfc_curp_beneficiario": kwargs.get("cuentaclave", "ND"),
            "cuentatransferencia_id": kwargs.get("transaction_rel__cuentatransferencia_id", "ND"),
            "saldo_remanente": kwargs.get("saldo_remanente", 0.0),
            "saldo_remanente_beneficiario": kwargs.get("saldo_remanente_beneficiario", 0.0),
            "status_trans_id": self.status_trans_id,
        }

    @staticmethod
    def _create(data) -> transferencia:
        return transferencia.objects.tranfer_to_polipay_comission(**data)


@dataclass
class TransferComissionTransactionOut(PayCommisionPolipay):
    """ Realiza el cobro de una comisión si es una dispersión """

    _registra_orden: ClassVar[RegistraOrdenSTPDispersion] = RegistraOrdenSTPDispersion

    def __init__(self, polipay_comission: InfoRazonSocialPolipayComission, data: Dict[str, Any]):
        self.polipay_comission = polipay_comission
        self.status_trans_id = 3
        self.instance = None
        self.data = data

        if self.data.get("transaction_rel__tipo_pago_id") == 4:
            _data_serializer = self._data(**self.data, **self.polipay_comission.info)
            instance = self._create(_data_serializer)
            self._registra_orden(instance)
            _update_commision_detail(self.data.get("id"), instance)

    @staticmethod
    def _saldo_remanente(monto_transaccion: float, monto_beneficiario: float) -> float:
        monto_beneficiario += monto_transaccion
        return monto_beneficiario

    def _data(self, **kwargs) -> Dict[str, Any]:
        return {
            "empresa": kwargs.get("transaction_rel__empresa", "ND"),
            "monto": float(kwargs.get("mount", "ND")),
            "nombre_emisor": kwargs.get("transaction_rel__nombre_emisor", "ND"),
            "cuenta_emisor": kwargs.get("transaction_rel__cuenta_emisor", "ND"),
            "rfc_curp_emisor": kwargs.get("transaction_rel__rfc_curp_emisor", "ND"),
            "nombre_beneficiario": kwargs.get("persona_cuenta__name", "ND"),
            "cta_beneficiario": kwargs.get("persona_cuenta__rfc", "ND"),
            "rfc_curp_beneficiario": kwargs.get("cuentaclave", "ND"),
            "cuentatransferencia_id": kwargs.get("transaction_rel__cuentatransferencia_id", "ND"),
            "saldo_remanente": kwargs.get("saldo_remanente", 0.0),
            "saldo_remanente_beneficiario": kwargs.get("saldo_remanente_beneficiario", 0.0),
            "status_trans_id": self.status_trans_id,
        }

    @staticmethod
    def _create(data) -> transferencia:
        return transferencia.objects.tranfer_to_polipay_comission(**data)


class PositiveComission:
    """ Pago de comisión positiva por SPEI """

    _transaction_out: ClassVar[TransferComissionTransactionOut] = TransferComissionTransactionOut
    _transaction_in: ClassVar[TransferComissionTransactionIn] = TransferComissionTransactionIn
    _registra_orden: ClassVar[RegistraOrdenSTPDispersion] = RegistraOrdenSTPDispersion
    _change_status_comission: ClassVar[ChangeStatusComission] = ChangeStatusComission
    _desactive_account_admin: ClassVar[DesactiveAccountAdmin] = DesactiveAccountAdmin
    _activate_account_admin: ClassVar[ActivateAccountAdmin] = ActivateAccountAdmin
    _calculate_comission: ClassVar[CalculateComission] = CalculateComission
    _transaction: ClassVar[PayCommisionPolipay] = PayCommisionPolipay
    _info_emisor: ClassVar[InfoEmisor] = InfoEmisor
    _movements: ClassVar[Movements] = Movements

    def __init__(
            self,
            clients: ListAllClients,
            beneficiario: InfoRazonSocialPolipayComission,
            admins: ComponentAllAdmin,
            log: RegisterLog,
    ):
        self.clients = clients.list_all_clients
        self.beneficiario = beneficiario
        self.admins = admins.list_admin
        self.log = log
        self.now = dt.datetime.now()
        self.list_commission_error = self.comission

    @staticmethod
    def tiempo_limite(datetime: dt.datetime) -> dt.date:
        days = (dt.timedelta(days=obtener_dias_del_mes(datetime.month, datetime.year)).days - datetime.day) + 1
        return datetime.date() + dt.timedelta(days=days)

    @staticmethod
    def get_info_account_client(client_id: int) -> Dict[str, Any]:
        return cuenta.objects.filter(persona_cuenta_id=client_id).values('id', 'monto', 'persona_cuenta_id').first()

    def validate_account(self, data: Dict[str, Any], commision_info: Dict[str, Any], client_id: int, time: dt.datetime):
        if commision_info.get("mount") < data.get('monto'):
            self._movements(client_id, commision_info.get("mount"))
            self._transaction_in(self.beneficiario, commision_info)
            self._transaction_out(self.beneficiario, commision_info)
            self._change_status_comission(commision_info.get("id"), time, status_id=1)

        if data.get('monto') == 0.0:
            self._change_status_comission(commision_info.get("id"), time, status_id=3)
            if self.tiempo_limite(dt.datetime.now()) == dt.date(2022, 4, 1):
                self._desactive_account_admin(client_id)

        if commision_info.get("mount") > data.get('monto'):
            if self.tiempo_limite(dt.datetime.now()) == dt.date(2022, 4, 1):
                self._desactive_account_admin(client_id)

    @property
    def comission(self) -> Union[List[dict], None]:
        clients = self.clients
        amount_beneficiario = self.beneficiario.info.get("monto")
        list_commission_error: list = []

        for i in range(0, len(clients)):
            client_id: int = clients[i]
            time = dt.datetime.now()
            _info_account = self.get_info_account_client(client_id)
            commision_info = self._calculate_comission(client_id, self.now)

            if commision_info.list_comission_info:
                amount = _info_account.get("monto")

                for row in commision_info.list_comission_info:
                    amount -= float(row.get("mount"))
                    amount_beneficiario += float(row.get("mount"))
                    row["saldo_remanente"] = amount
                    row["saldo_remanente_beneficiario"] = amount_beneficiario
                    try:
                        with atomic():
                            self.validate_account(_info_account, row, client_id, time)
                    except StpmexException as e:
                        self.log.json_request({"error_stp": e.msg, "desc": e.desc})
                        list_commission_error.append(row)
                    except Exception as e:
                        self.log.json_request({"error": str(e)})
                        list_commission_error.append(row)
                    else:
                        continue

            if not list_commission_error:
                self._activate_account_admin(client_id)
        return list_commission_error


class PayComissionPositiveDebts(RetrieveAPIView):
    """ Pago de comisiones adeudadas """

    permission_classes = ()

    def retrieve(self, request, *args, **kwargs):
        try:
            with atomic():
                list_clients = ListAllClients()
                comission = PositiveComission(list_clients)
        except Exception as e:
            err = MyHttpError(message="Ocurrio un error al listar las comisiones", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            message = {"message": "ok"}
            return Response(message, status=status.HTTP_200_OK)
