import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple, Union, List, Dict, Any, ClassVar, NoReturn

from django.db.models import QuerySet
from django.db.transaction import atomic

from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView
from rest_framework import status

from MANAGEMENT.ComissionPay.comission import ComponentAllAdmin
from MANAGEMENT.mails.messages import EmailWarningCommissionList
from apps.api_stp.client import CosumeAPISTP
from apps.api_stp.exc import StpmexException
from apps.api_stp.management import SetFolioOpetacionSTP
from apps.api_stp.signature import SignatureProductionAPIStpIndividualComissionPay
from apps.logspolipay.manager import RegisterLog
from polipaynewConfig.settings import COST_CENTER_POLIPAY_COMISSION
from apps.transaction.models import transferencia
from apps.commissions.models import Commission_detail
from MANAGEMENT.Utils.utils import obtener_dias_del_mes
from apps.users.models import grupoPersona, cuenta
from MANAGEMENT.Standard.errors_responses import MyHttpError


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
            status=2,
            client_id=self._client,
            start_date=_start_date,
            end_date=_end_date
        )
        return to_list(queryset)


class ChangeStatusComission:
    def __init__(self, client_id: int, datetime: dt.datetime, status_id: int):
        self._client = client_id
        self.datetime = datetime
        self.status_id = status_id
        self.change_status_comission()

    def change_status_comission(self) -> bool:
        # _start_date, _end_date = get_last_month(self.datetime)

        Commission_detail.objects.select_related('status', 'transaction_rel', 'commission').filter(
            # Q(transaction_rel__fecha_creacion__date__gte=_start_date) &
            # Q(transaction_rel__fecha_creacion__date__lte=_end_date)
        ).filter(
            status_id=2,
            transaction_rel__cuentatransferencia__persona_cuenta_id=self._client
        ).update(status_id=self.status_id, payment_date=dt.datetime.now())
        return True


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
    def get_info_account_client(client_id: int) -> Dict[str, Any]:
        return cuenta.objects.filter(persona_cuenta_id=client_id).values('id', 'monto', 'persona_cuenta_id').first()

    def validate_account(self, data: Dict[str, Any], commision_info: Dict[str, Any], client_id: int, time: dt.datetime):
        if commision_info.get("mount") < data.get('monto'):
            self._movements(client_id, commision_info.get("mount"))
            self._transaction_in(self.beneficiario, commision_info)
            self._transaction_out(self.beneficiario, commision_info)
            self._change_status_comission(client_id, self.now, status_id=1)

        if data.get('monto') == 0.0:
            self._change_status_comission(client_id, time, status_id=3)

        if commision_info.get("mount") > data.get('monto'):
            self._change_status_comission(client_id, time, status_id=3)

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
        return list_commission_error


class SendMailCommission:
    _mail: ClassVar[EmailWarningCommissionList] = EmailWarningCommissionList

    def __init__(self, commission: PositiveComission, admins: ComponentAllAdmin):
        if commission.list_commission_error:
            self.send_mails(admins.list_admin, commission.list_commission_error)

    # @property
    # def data

    def send_mails(self, list_admin: List[Dict[str, Any]], list_commission: List[Dict]):
        for row in list_admin:
            self._mail(to=row.get("email"), name=row.get("name"), commission_list=list_commission)


class PayComissionPositive(RetrieveAPIView):
    """ Pago de comisiones pendientes """

    _rs_polipay_commision: ClassVar[InfoRazonSocialPolipayComission] = InfoRazonSocialPolipayComission
    _positive_comission: ClassVar[PositiveComission] = PositiveComission
    _all_admin: ClassVar[ComponentAllAdmin] = ComponentAllAdmin
    _all_clients: ClassVar[ListAllClients] = ListAllClients
    _log: ClassVar[RegisterLog] = RegisterLog
    permission_classes = ()

    def retrieve(self, request, *args, **kwargs):
        log = self._log(-1, request)
        try:
            with atomic():
                log.json_request(request.data)
                list_clients = self._all_clients()
                beneficiario = self._rs_polipay_commision()
                all_admin = self._all_admin()
                self._positive_comission(list_clients, beneficiario, all_admin, log)
        except Exception as e:
            err = MyHttpError(message="Ocurrio un error al listar las comisiones", real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            message = {"message": "ok"}
            log.json_response(message)
            return Response(message, status=status.HTTP_200_OK)
