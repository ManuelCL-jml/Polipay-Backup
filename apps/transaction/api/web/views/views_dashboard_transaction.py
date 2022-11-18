from typing import Dict, Any, List, ClassVar

from django.db.models import QuerySet, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status

from MANAGEMENT.Standard.errors_responses import MyHttpError
from apps.transaction.models import transferencia, transmasivaprod
from apps.users.models import cuenta, persona


class StatusCat:
    status_individual: ClassVar[Dict[str, Any]] = {
        1: "Liquidada",
        2: "Incompleta",
        3: "Pendiente",
        5: "Cancelada",
        6: "Creada",
        7: "Devuelta",
        9: "Programada",
    }

    status_massive: ClassVar[Dict[str, Any]] = {
        1: "Creadas",
        2: "Pendientes",
        3: "Canceladas",
        4: "En proceso",
        5: "Procesadas",
    }

    def __init__(self, status_id: int):
        self._status_id = status_id

    @property
    def get_status_individual(self) -> str:
        return self.status_individual.get(self._status_id)

    @property
    def get_status_massive(self) -> str:
        return self.status_massive.get(self._status_id)


class DashboardDispersionMassive:
    status_list: ClassVar[List[int]] = [1, 2, 3, 4, 5]

    def __init__(self, **kwargs):
        self._cost_center_id = kwargs.get('cost_center_id')
        self.massive = self._render

    @property
    def _list_only_id_transaction_massive(self) -> List[int]:
        list_sets_massive = transferencia.objects.select_related(
            'status_trans',
            'tipo_pago',
            'cuentatransferencia',
            'masivo_trans'
        ).filter(
            cuentatransferencia__persona_cuenta_id=self._cost_center_id,
            masivo_trans_id__isnull=False,
            tipo_pago_id=4
        ).values_list('masivo_trans_id', flat=True)

        return list(set(list_sets_massive))

    @staticmethod
    def _get_only_id_massive(status_id: int) -> List[int]:
        return transmasivaprod.objects.select_related('statusRel').filter(
            statusRel_id=status_id).values_list('id', flat=True)

    def _sum_amount_transaction_massive(self, status_id: int):
        list_sets_massive = transferencia.objects.select_related(
            'tipo_pago',
            'cuentatransferencia',
            'masivo_trans'
        ).filter(
            cuentatransferencia__persona_cuenta_id=self._cost_center_id,
            masivo_trans_id__in=self._get_only_id_massive(status_id),
            tipo_pago_id=4
        ).values_list('monto', flat=True)
        return round(sum(list_sets_massive), 4)

    def _transaccion_massive(self, status_id: int):
        return transmasivaprod.objects.filter(
            id__in=self._list_only_id_transaction_massive,
            statusRel_id=status_id,
        ).count()

    @property
    def _render(self) -> List[Dict[str, Any]]:
        return [
            {
                "status_id": status,
                "status": StatusCat(status).get_status_massive,
                "count": self._transaccion_massive(status),
                "total_amount": self._sum_amount_transaction_massive(status)
            }
            for status in self.status_list
        ]


class DashboardDispersionIndividual:
    status_list: ClassVar[List[int]] = [1, 5, 9]
    status_individual: ClassVar[Dict[str, Any]] = {
        1: "Liquidada",
        5: "Cancelada",
        9: "Programada",
    }

    def __init__(self, **kwargs):
        self._cost_center_id = kwargs.get('cost_center_id')
        self.individual = self._render

    @staticmethod
    def _sum_amount(amount_list: List[float]) -> float:
        return round(sum(amount_list), 2)

    @staticmethod
    def query(**kwargs):
        return transferencia.objects.select_related(
            'status_trans',
            'tipo_pago',
            'cuentatransferencia',
            'masivo_trans'
        ).filter(
            masivo_trans_id__isnull=True,
            **kwargs
        ).count()

    @staticmethod
    def sum_amount_transaction(status_id: int, cost_center_id: int):
        sum_transaction = transferencia.objects.select_related(
            'status_trans',
            'tipo_pago',
            'cuentatransferencia',
            'masivo_trans'
        ).filter(
            status_trans_id=status_id,
            cuentatransferencia__persona_cuenta_id=cost_center_id,
            tipo_pago_id=4,
            masivo_trans_id__isnull=True,
        ).values_list('monto', flat=True)

        return round(sum(sum_transaction), 4)

    def transaccion_individual(self, status_id: int, cost_center_id: int):
        return self.query(status_trans_id=status_id, cuentatransferencia__persona_cuenta_id=cost_center_id,
                          tipo_pago_id=4)

    def transaccion_recibida(self, cost_center_id: int):
        return self.query(status_trans_id=1, cuentatransferencia__persona_cuenta_id=cost_center_id, tipo_pago_id=5)

    @property
    def _render(self) -> List[Dict[str, Any]]:
        return [
            {
                "status_id": status,
                "status": StatusCat(status).get_status_individual,
                "count": self.transaccion_individual(status, self._cost_center_id),
                "total_amount": self.sum_amount_transaction(status, self._cost_center_id)
            }
            for status in self.status_list
        ]


class GetInfoRazonSocial:
    def __init__(self, razon_social_id: int):
        self.razon_social_id = razon_social_id
        self.account = self._get_account_razon_social

    def handler_error(self):
        if not persona.objects.filter(tipo_persona_id=1, id=self.razon_social_id, state=True, is_active=True).exists():
            raise ValueError('Razon social no valido o no existe')

    @property
    def _get_account_razon_social(self) -> Dict[str, Any]:
        return cuenta.objects.filter(
            persona_cuenta_id=self.razon_social_id).values('id', 'cuenta', 'cuentaclave').first()


# (ChrGil 2022-04-12) Dashboard para dispersiones
class DashBoardDispersa(ListAPIView):
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        try:
            razon_social_id = self.request.query_params['razon_social_id']
            GetInfoRazonSocial(razon_social_id=razon_social_id)

            individual = DashboardDispersionIndividual(cost_center_id=razon_social_id)
            massive = DashboardDispersionMassive(cost_center_id=razon_social_id)

        except (ValueError, IndexError, TypeError) as e:
            err = MyHttpError(message='Ocurrio un error al mostrar el dashboard', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_200_OK)
        else:
            return Response({
                "individual": individual.individual,
                "massive": massive.massive
            }, status=status.HTTP_200_OK)


class DashboardTransactionsIndividual:
    status_list: ClassVar[List[int]] = [1, 2, 3, 4, 5, 6, 7]

    def __init__(self, **kwargs):
        self._cost_center_id = kwargs.get('cost_center_id')
        self.individual = self._render
        self.recibidas = self._add_transaction_recibida

    @staticmethod
    def query(**kwargs):
        return transferencia.objects.select_related(
            'status_trans',
            'tipo_pago',
            'cuentatransferencia',
            'masivo_trans'
        ).filter(
            masivo_trans_id__isnull=True,
            **kwargs
        ).count()

    @staticmethod
    def sum_amount_transaction(status_id: int, cost_center_id: int, tipo_pago_id: int):
        sum_transaction = transferencia.objects.select_related(
            'status_trans',
            'tipo_pago',
            'cuentatransferencia',
            'masivo_trans'
        ).filter(
            status_trans_id=status_id,
            cuentatransferencia__persona_cuenta_id=cost_center_id,
            tipo_pago_id=tipo_pago_id,
            masivo_trans_id__isnull=True,
        ).values_list('monto', flat=True)

        return round(sum(sum_transaction), 4)

    def transaccion_individual(self, status_id: int, cost_center_id: int):
        return self.query(status_trans_id=status_id, cuentatransferencia__persona_cuenta_id=cost_center_id,
                          tipo_pago_id=2)

    def transaccion_recibida(self, cost_center_id: int):
        return self.query(status_trans_id=1, cuentatransferencia__persona_cuenta_id=cost_center_id, tipo_pago_id=5)

    @property
    def _render(self) -> List[Dict[str, Any]]:
        return [
            {
                "status_id": status,
                "status": StatusCat(status).get_status_individual,
                "count": self.transaccion_individual(status, self._cost_center_id),
                "total_amount": self.sum_amount_transaction(status, self._cost_center_id, 2)
            }
            for status in self.status_list
        ]

    @property
    def _add_transaction_recibida(self):
        return {
            "type": "Recibidas",
            "count": self.transaccion_recibida(self._cost_center_id),
            "total_amount": self.sum_amount_transaction(1, self._cost_center_id, 5)
        }


# (ChrGil 2022-04-12) Dashboard de polipay a polipay
class DashboardPolipayToPolipay:
    def __init__(self, razon_social: GetInfoRazonSocial):
        self._cuenta = razon_social.account.get('cuenta')
        self._cuentaclave = razon_social.account.get('cuentaclave')
        self.polipay_to_polipay = self._render

    @staticmethod
    def _sum_amount(amount_list: List[float]) -> float:
        return round(sum(amount_list), 2)

    @property
    def transaction_polipay_to_polipay_enviadas(self) -> QuerySet:
        return transferencia.objects.filter(
            Q(cuenta_emisor__icontains=self._cuenta) |
            Q(cuenta_emisor__icontains=self._cuentaclave)
        ).filter(
            status_trans_id=1,
            tipo_pago_id=1
        )

    @property
    def transaction_polipay_to_polipay_recibidas(self) -> QuerySet:
        return transferencia.objects.filter(
            Q(cta_beneficiario__icontains=self._cuenta) |
            Q(cta_beneficiario__icontains=self._cuentaclave)
        ).filter(
            status_trans_id=1,
            tipo_pago_id=1
        )

    @property
    def sum_amount_dispersion_polipay_to_polipay_enviadas(self) -> List[float]:
        return self.transaction_polipay_to_polipay_enviadas.values_list('monto', flat=True)

    @property
    def sum_amount_dispersion_polipay_to_polipay_recibidas(self) -> List[float]:
        return self.transaction_polipay_to_polipay_recibidas.values_list('monto', flat=True)

    @property
    def _render(self) -> Dict[str, Any]:
        return {
            "enviadas": {
                "count": self.transaction_polipay_to_polipay_enviadas.count(),
                "total_amount": self._sum_amount(self.sum_amount_dispersion_polipay_to_polipay_enviadas)
            },
            "recibidas": {
                "count": self.transaction_polipay_to_polipay_recibidas.count(),
                "total_amount": self._sum_amount(self.sum_amount_dispersion_polipay_to_polipay_recibidas)
            }
        }


class DashboardTransactionsMassive:
    status_list: ClassVar[List[int]] = [1, 2, 3, 4, 5]

    def __init__(self, **kwargs):
        self._cost_center_id = kwargs.get('cost_center_id')
        self.massive = self._render

    @property
    def _list_only_id_transaction_massive(self) -> List[int]:
        list_sets_massive = transferencia.objects.select_related(
            'status_trans',
            'tipo_pago',
            'cuentatransferencia',
            'masivo_trans'
        ).filter(
            cuentatransferencia__persona_cuenta_id=self._cost_center_id,
            masivo_trans_id__isnull=False,
            tipo_pago_id=2
        ).values_list('masivo_trans_id', flat=True)

        return list(set(list_sets_massive))

    @staticmethod
    def _get_only_id_massive(status_id: int) -> List[int]:
        return transmasivaprod.objects.select_related('statusRel').filter(
            statusRel_id=status_id).values_list('id', flat=True)

    def _sum_amount_transaction_massive(self, status_id: int):
        list_sets_massive = transferencia.objects.select_related(
            'tipo_pago',
            'cuentatransferencia',
            'masivo_trans'
        ).filter(
            cuentatransferencia__persona_cuenta_id=self._cost_center_id,
            masivo_trans_id__in=self._get_only_id_massive(status_id),
            tipo_pago_id=2
        ).values_list('monto', flat=True)
        return round(sum(list_sets_massive), 4)

    def _transaccion_massive(self, status_id: int):
        return transmasivaprod.objects.select_related('statusRel').filter(
            id__in=self._list_only_id_transaction_massive,
            statusRel_id=status_id,
        ).count()

    @property
    def _render(self) -> List[Dict[str, Any]]:
        return [
            {
                "status_id": status,
                "status": StatusCat(status).get_status_massive,
                "count": self._transaccion_massive(status),
                "total_amount": self._sum_amount_transaction_massive(status)
            }
            for status in self.status_list
        ]


# (ChrGil 2022-04-12) Dashboard para Transacciones
class DashBoardTransaction(ListAPIView):
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        try:
            razon_social_id = self.request.query_params['razon_social_id']
            razon_social = GetInfoRazonSocial(razon_social_id=razon_social_id)

            individual = DashboardTransactionsIndividual(cost_center_id=razon_social_id)
            massive = DashboardTransactionsMassive(cost_center_id=razon_social_id)
            polipay_to_polipay = DashboardPolipayToPolipay(razon_social)

        except (ValueError, IndexError, TypeError, AttributeError) as e:
            err = MyHttpError(message='Ocurrio un error al mostrar el dashboard', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_200_OK)
        else:
            return Response({
                "TransactionIndividual": individual.individual,
                "TransactionMassive": massive.massive,
                "PolipayToPolipay": polipay_to_polipay.polipay_to_polipay,
                "Recibidas": individual.recibidas,
            }, status=status.HTTP_200_OK)
