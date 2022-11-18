# Pago de comisiones pendientes

from decimal import Decimal
from typing import Tuple, Union, List, Dict, Any, ClassVar, NoReturn

from django.db.transaction import atomic

from polipaynewConfig.wsgi import *

from apps.transaction.models import transferencia
from polipaynewConfig.settings import COST_CENTER_POLIPAY_COMISSION
import datetime as dt
from django.db.models import QuerySet, Q
from apps.commissions.models import Commission_detail
from MANAGEMENT.Utils.utils import obtener_dias_del_mes
from apps.users.models import grupoPersona, cuenta


def to_list(queryset: QuerySet) -> List[Union[int, float, str, bool, Dict, Decimal]]:
    return list(queryset)


def get_last_month(datetime: dt.datetime) -> Tuple[dt.date, dt.date]:
    days_of_the_month = obtener_dias_del_mes(datetime.month - 1, datetime.year)
    last_month = datetime.date() - dt.timedelta(days=days_of_the_month)
    return last_month, datetime.date()


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
        self.total_amount = self.sum_amount_comission(self.list_comission_client)

    @staticmethod
    def sum_amount_comission(comission_list: Union[List, QuerySet]) -> Union[float, None]:
        if comission_list:
            return float(sum(comission_list))
        return None

    @property
    def list_comission_client(self) -> List[Decimal]:
        _start_date, _end_date = get_last_month(self.datetime)

        queryset = Commission_detail.objects.select_related('status', 'transaction_rel', 'commission').filter(
            Q(transaction_rel__fecha_creacion__date__gte=_start_date) &
            Q(transaction_rel__fecha_creacion__date__lte=_end_date)
        ).filter(
            status_id=2,
            transaction_rel__cuentatransferencia__persona_cuenta_id=self._client
        ).values_list("mount", flat=True)

        return to_list(queryset)


class ChangeStatusComission:
    def __init__(self, client_id: int, datetime: dt.datetime, status_id: int):
        self._client = client_id
        self.datetime = datetime
        self.status_id = status_id
        self.change_status_comission()

    def change_status_comission(self) -> bool:
        _start_date, _end_date = get_last_month(self.datetime)

        Commission_detail.objects.select_related('status', 'transaction_rel', 'commission').filter(
            Q(transaction_rel__fecha_creacion__date__gte=_start_date) &
            Q(transaction_rel__fecha_creacion__date__lte=_end_date)
        ).filter(
            status_id=2,
            transaction_rel__cuentatransferencia__persona_cuenta_id=self._client
        ).update(status_id=self.status_id, payment_date=dt.datetime.now())
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
            "saldo_remanente": self._emisor.get('monto'),
        }

    def _create(self) -> NoReturn:
        transferencia.objects.tranfer_to_polipay_comission(**self._data)


class PositiveComission:
    _calculate_comission: ClassVar[CalculateComission] = CalculateComission
    _movements: ClassVar[Movements] = Movements
    _change_status_comission: ClassVar[ChangeStatusComission] = ChangeStatusComission
    _transaction: ClassVar[TransferComissionToPolipayComission] = TransferComissionToPolipayComission
    _info_emisor: ClassVar[InfoEmisor] = InfoEmisor

    def __init__(self, clients: ListAllClients):
        self.clients = clients.list_clients
        self.now = dt.datetime.now()
        self.beneficiario = InfoRazonSocialPolipayComission
        self.comission()

    @staticmethod
    def get_info_account_client(client_id: int) -> Dict[str, Any]:
        return cuenta.objects.filter(persona_cuenta_id=client_id).values('id', 'monto', 'persona_cuenta_id').first()

    def validate_account(self, data: Dict[str, Any], amount: float, client_id: int):
        if amount < data.get('monto'):
            self._movements(client_id, amount)
            self._transaction(self.beneficiario(), self._info_emisor(client_id), amount)
            self._change_status_comission(client_id, self.now, status_id=1)

        if data.get('monto') == 0.0:
            self._change_status_comission(client_id, self.now, status_id=3)

        if amount > data.get('monto'):
            self._change_status_comission(client_id, self.now, status_id=3)

    def comission(self):
        clients = self.clients

        for i in range(0, len(clients)):
            client_id: int = clients[i]
            _comission = self._calculate_comission(client_id, self.now).total_amount

            if not _comission:
                continue

            if _comission:
                _info_account = self.get_info_account_client(client_id)
                self.validate_account(_info_account, _comission, client_id)


try:
    with atomic():
        list_clients = ListAllClients()
        print(list_clients.list_clients)
        print(list_clients.list_all_clients)
        comission = PositiveComission(list_clients)
except Exception as e:
    print(e)

