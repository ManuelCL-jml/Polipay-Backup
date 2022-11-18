import datetime as dt

from django.db.models import Q
from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView
from rest_framework import status

from typing import ClassVar, List, Dict, Any, NoReturn

from apps.transaction.management import preparingNotification
from MANAGEMENT.Utils.utils import get_values_list
from apps.transaction.messages import message_email
from apps.transaction.models import TransMasivaProg, transferenciaProg, transferencia, transmasivaprod
from apps.users.models import cuenta


# (ChrGil 2022-02-20) Lista las dispersiones masivas o individuales programadas
class ListTransactionSheduleToday:
    list_massive_id: ClassVar[List[int]]
    list_transaction_id: ClassVar[List[int]]

    def __init__(self):
        self.list_massive_id = self._get_massive_shedule
        self.list_transaction_id = self._get_individual_shedule

    @property
    def _get_massive_shedule(self) -> List[int]:
        return list(TransMasivaProg.objects.select_related('masivaReferida').filter(
            Q(fechaProgramada__year=dt.datetime.now().year) &
            Q(fechaProgramada__month=dt.datetime.now().month) &
            Q(fechaProgramada__day=dt.datetime.now().day) &
            Q(fechaProgramada__hour=dt.datetime.now().hour) &
            Q(fechaProgramada__minute=dt.datetime.now().minute)
        ).values_list('masivaReferida', flat=True))

    @property
    def _get_individual_shedule(self) -> List[int]:
        return list(transferenciaProg.objects.select_related('transferReferida').filter(
            Q(fechaProgramada__year=dt.datetime.now().year) &
            Q(fechaProgramada__month=dt.datetime.now().month) &
            Q(fechaProgramada__day=dt.datetime.now().day) &
            Q(fechaProgramada__hour=dt.datetime.now().hour) &
            Q(fechaProgramada__minute=dt.datetime.now().minute)
        ).values_list('transferReferida_id', flat=True))


# (ChrGil 2022-02-20) Lista la información de la dispersión programada a realizar
class ListTransactionInfo:
    list_transaction: ClassVar[List[Dict[str, Any]]]

    def __init__(self, shedule: ListTransactionSheduleToday):
        _massive = self._list_transaction(masivo_trans_id__in=shedule.list_massive_id)
        _individual = self._list_transaction(id__in=shedule.list_transaction_id)
        _massive.extend(_individual)
        self.list_transaction = _massive

    @staticmethod
    def _list_transaction(**kwargs) -> List[Dict[str, Any]]:
        return list(transferencia.objects.select_related(
            'tipo_pago_id',
            'masivo_trans',
            'status_trans',
            'cuentatransferencia'
        ).filter(
            **kwargs,
            tipo_pago_id=4,
            status_trans_id=9,
            programada=True,
        ).values(
            'id',
            'nombre_beneficiario',
            'cta_beneficiario',
            'monto',
            'concepto_pago',
            'nombre_emisor',
            'email',
            'masivo_trans_id'
        ))

    @property
    def _get_list_transaction_id(self) -> List[str]:
        return get_values_list('id', self.list_transaction)

    @property
    def _get_list_transaction_massive_id(self) -> List[str]:
        return get_values_list('masivo_trans_id', self.list_transaction)

    def chage_status_transaction(self):
        transferencia.objects.filter(id__in=self._get_list_transaction_id).update(
            status_trans_id=1,
            date_modify=dt.datetime.now()
        )

    def chage_status_transaction_massive(self):
        transmasivaprod.objects.filter(id__in=self._get_list_transaction_massive_id).update(
            statusRel_id=5,
            date_modified=dt.datetime.now()
        )


class DepositAmount:
    def __init__(self, list_transactions: ListTransactionInfo):
        self._list_transactions = list_transactions
        self._deposit_amount()

    def _deposit_amount(self):
        for row in self._list_transactions.list_transaction:
            account: float = row.get('cta_beneficiario')
            account_instance: cuenta = cuenta.objects.get(cuenta=account)
            account_instance.monto += row.get('monto')
            account_instance.save()


class SendMailBeneficiario:
    def __init__(self, transaction_info: ListTransactionInfo):
        self._transaction_info = transaction_info
        self._send_mail()

    def _context_data_email(self, **kwargs) -> NoReturn:
        folio = f"PO-{kwargs.get('id'):010d}"

        return {
            "folio": folio,
            "name": kwargs.get('nombre_beneficiario'),
            "fecha_operacion": dt.datetime.now(),
            "observation": kwargs.get('concepto_pago'),
            "nombre_emisor": kwargs.get('nombre_emisor'),
            "monto": kwargs.get('monto'),
        }

    def _send_mail(self) -> NoReturn:
        for context in self._transaction_info.list_transaction:
            message_email(
                template_name='MailDispersionesBeneficiario.html',
                context=self._context_data_email(**context),
                title='Dispersion',
                body=context.get('concepto_pago'),
                email=context.get('email')
            )


# (ChrGil 2022-01-04) Envio de notificación al cliente
class SendNotificationDispersaBeneficiarios:
    def __init__(self, transaction_info: ListTransactionInfo):
        self._transaction_info = transaction_info
        self._send_notification()

    def _send_notification(self) -> NoReturn:
        for account in self._transaction_info.list_transaction:
            preparingNotification(cuentaBeneficiario=account.get('cta_beneficiario'), opcion=3)


class CreateDispersionSheluded(RetrieveAPIView):
    permission_classes = ()

    @method_decorator(cache_page(60 * 0.1))
    def retrieve(self, request, *args, **kwargs):
        code: str = self.request.query_params['id']

        if code == '45124545':
            try:
                with atomic():
                    shedule_transaction = ListTransactionSheduleToday()
                    if len(shedule_transaction.list_massive_id) >= 1 or len(shedule_transaction.list_transaction_id):
                        list_transaction_info = ListTransactionInfo(shedule_transaction)
                        DepositAmount(list_transaction_info)
                        list_transaction_info.chage_status_transaction()
                        list_transaction_info.chage_status_transaction_massive()
                        SendMailBeneficiario(list_transaction_info)
                        SendNotificationDispersaBeneficiarios(list_transaction_info)
            except Exception as e:
                return Response(str(e))

        return Response(status=status.HTTP_200_OK)
