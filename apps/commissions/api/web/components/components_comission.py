# Logica del negocio

import datetime as dt
from typing import Dict, ClassVar, List, Any

from django.db.models import Q

from apps.commissions.models import Commission_detail, Commission
from apps.paycash.models import PayCashReference
from apps.users.models import persona, grupoPersona, cuenta
from MANAGEMENT.Utils.utils import get_id_cuenta_eje, get_values_list


class ComponentInfoComission:
    account_id: ClassVar[int]

    def __init__(self, admin: persona, **kwargs):
        self._cuenta_eje = get_id_cuenta_eje(admin.get_only_id())
        self._cost_center_id = kwargs.get('cost_center_id', None)
        self._comission_id = kwargs.get('comission_id', None)
        self._raise_error()

    def _raise_error(self):
        if self._cost_center_id:
            self.account_id = self._get_account_id.get('id')
            exists = grupoPersona.objects.exist(
                empresa_id=self._cuenta_eje,
                person_id=self._cost_center_id,
                group_id=5,
                person__state=True
            )

            if not exists:
                raise ValueError('Centro de costos no valido o no existe')

        if self._comission_id:
            self.account_id = None
            if not Commission_detail.objects.filter(id=self._comission_id).exists():
                raise ValueError('Comisión no valida o no existe')

        if (self._comission_id is None) and (self._cost_center_id is None):
            raise ValueError('Error al listar y/o ver las comisiones')

    @property
    def _get_account_id(self) -> Dict[str, Any]:
        return cuenta.objects.filter(persona_cuenta_id=self._cost_center_id).values('id').first()


# (ChrGil 2022-03-18) Componente que se encraga de listar las comisiones positivas por centro de costos
# (ChrGil 2022-03-18) y mostrar el detalle de esa comisión
class ComponentListPositiveComission:
    _defaul_size: ClassVar[int] = 5
    _comission_positive: ClassVar[int] = 1
    comission_list: ClassVar[List[Dict[str, Any]]]
    comission_detail: ClassVar[Dict[str, Any]]

    def __init__(self, **kwargs):
        self._cost_center_account = kwargs.get('cost_center_account_id', None)
        self._comission_id = kwargs.get('comission_id', None)
        self._start_date = kwargs.get('start_date', dt.date.today() - dt.timedelta(days=91))
        self._end_date = kwargs.get('end_date', dt.date.today())
        self.size = kwargs.get('size', self._defaul_size)
        self._raise_comission()

    def _raise_comission(self):
        if self._comission_id:
            self.comission_detail = self._render_detail(**self._detail)

        if self._cost_center_account:
            self.comission_list = [self._render_list(**comission) for comission in self._list]

    @staticmethod
    def _render_list(**kwargs):
        amount = kwargs.get('mount')
        percent = kwargs.get('commission__commission_rel__percent')
        date: dt.datetime = kwargs.get('transaction_rel__fecha_creacion')

        return {
            "id": kwargs.get('id'),
            "FechaOperacion": date.strftime('%d/%m/%Y %H:%M'),
            "CantidadComision": round(float(amount), 4),
            "PorcentajeComision": round(float(percent * 100), 2),
            "status": kwargs.get('status'),
            "type": kwargs.get('status__type'),
        }

    @property
    def _list(self) -> List[Dict[str, Any]]:
        return Commission_detail.objects.select_related('commission', 'transaction_rel', 'status').filter(
            Q(transaction_rel__fecha_creacion__date__gte=self._start_date) &
            Q(transaction_rel__fecha_creacion__date__lte=self._end_date)
        ).filter(
            commission__commission_rel__type_id=self._comission_positive,
            transaction_rel__cuentatransferencia_id=self._cost_center_account,
            status_id__in=[2, 3],
        ).values(
            "id",
            "transaction_rel__fecha_creacion",
            "mount",
            "commission__commission_rel__percent",
            "status",
            "status__type",
        ).order_by('-transaction_rel__fecha_creacion')

    @staticmethod
    def _render_detail(**kwargs) -> Dict[str, Any]:
        percent = kwargs.get('commission__commission_rel__percent')
        date: dt.datetime = kwargs.get('transaction_rel__fecha_creacion')
        amount = kwargs.get('transaction_rel__monto')

        return {
            "ClaveRastreo": kwargs.get('transaction_rel__clave_rastreo'),
            "ConceptoPago": kwargs.get('transaction_rel__concepto_pago'),
            "Monto": round(float(amount), 2),
            "FechaOperacion": date.strftime('%d-%m-%Y %-H:%M'),
            "PorcentajeComision": round(float(percent * 100), 2),
        }

    @property
    def _detail(self) -> Dict[str, Any]:
        return Commission_detail.objects.select_related('commission', 'transaction_rel', 'status').filter(
            id=self._comission_id
        ).values(
            "transaction_rel__clave_rastreo",
            "transaction_rel__concepto_pago",
            "transaction_rel__monto",
            "transaction_rel__fecha_creacion",
            "commission__commission_rel__percent",
            "status",
            "status__type",
        ).first()

    @property
    def total_amount_comission(self) -> Dict[str, Any]:
        comission_amount_list = Commission_detail.objects.select_related(
            'commission', 'transaction_rel', 'status'
        ).filter(
            commission__commission_rel__type_id=self._comission_positive,
            transaction_rel__cuentatransferencia_id=self._cost_center_account,
            status_id=2,
        ).values_list("mount", flat=True)

        return {
            "ComisionTotal": round(float(sum(comission_amount_list)), 4)
        }


# (ChrGil 2022-03-21) Suma el monto de las comisiones pendiente
class ComponentSumAmountComission:
    amount_comission: ClassVar[float]

    def __init__(self, comission_list: ComponentListPositiveComission):
        self._comission_list = comission_list

        if len(comission_list.comission_list) == 0:
            self.amount_comission = None

        if len(comission_list.comission_list) >= 1:
            self.amount_comission = self._render

    @property
    def _sum_amount(self) -> float:
        return sum(get_values_list("CantidadComision", self._comission_list.comission_list))

    @property
    def _render(self):
        return {
            "ComisionTotal": round(self._sum_amount, 4)
        }


class ComponentInfoCuentaEje:
    def __init__(self, cuenta_eje_id: int):
        self.cuenta_eje_id = cuenta_eje_id
        cuenta_eje = self.get_info_cuenta_eje

        if cuenta_eje:
            self.cuenta_eje = cuenta_eje

        if not cuenta_eje:
            raise ValueError("Empresa no encontrada")

    @property
    def get_info_cuenta_eje(self) -> Dict[str, Any]:
        return persona.objects.filter(id=self.cuenta_eje_id, state=True).values(
            "id",
            "name",
        ).first()


class ComponentDetailServiceComission:
    def __init__(self, cuenta_eje_id: int):
        self.cuenta_eje_id = cuenta_eje_id
        self.list = [self.render(**row) for row in self.get_comission_detail]

    @property
    def get_comission_detail(self) -> List[Dict[str, Any]]:
        return Commission.objects.filter(
            Q(person_payer_id=self.cuenta_eje_id) |
            Q(person_debtor_id=self.cuenta_eje_id)
        ).values(
            "commission_rel_id",
            "commission_rel__percent",
            "commission_rel__amount",
            "commission_rel__type_id",
            "commission_rel__servicio_id",
            "commission_rel__servicio__service__nombre",
        ).order_by("commission_rel__servicio_id")

    @staticmethod
    def render(**kwargs) -> Dict[str, Any]:
        type_comission = kwargs.get("commission_rel__type_id")

        return {
            "CommissionId": kwargs.get("commission_rel_id"),
            "Percent": float(kwargs.get("commission_rel__percent")) * 100,
            "Amount": float(kwargs.get("commission_rel__amount")),
            "TypeId": True if type_comission == 1 else False,
            "ServiceId": kwargs.get("commission_rel__servicio_id"),
            "ServiceName": kwargs.get("commission_rel__servicio__service__nombre"),
        }
