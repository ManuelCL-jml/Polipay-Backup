import datetime as dt
import json

# import firebase_admin
from django.db.transaction import atomic
# from firebase_admin import credentials, messaging, exceptions
from typing import ClassVar, List, Dict, Any, NoReturn

from decouple import config

from polipaynewConfig.wsgi import *
# from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from django.db.models import Q
from MANAGEMENT.Utils.utils import get_values_list
from apps.transaction.messages import message_email
from apps.transaction.models import TransMasivaProg, transferenciaProg, transferencia, transmasivaprod
from apps.users.models import cuenta
# from apps.transaction.management import preparingNotification


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
            fechaProgramada__minute=dt.datetime.now().minute
        ).values_list('masivaReferida', flat=True))

    @property
    def _get_individual_shedule(self) -> List[int]:
        return list(transferenciaProg.objects.select_related('transferReferida').filter(
            fechaProgramada__minute=dt.datetime.now().minute
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


# (ChrGil 2022-02-20) Deposita a la cuenta del beneficiario el monto que se disperso
class BeneficiaryDeposits:
    def __init__(self, list_transactions: ListTransactionInfo):
        self._list_transactions = list_transactions
        self._account_list = self._get_list_account
        self._update()

    @property
    def _get_list_account(self) -> List[str]:
        return get_values_list('cta_beneficiario', self._list_transactions.list_transaction)

    @property
    def _get_list_instance_cuenta(self) -> List[cuenta]:
        return list(cuenta.objects.filter(
            Q(cuenta__in=self._account_list) | Q(cuentaclave__in=self._account_list)
        ))

    def _update(self):
        _transactions: List[Dict[str, Any]] = self._list_transactions.list_transaction
        _cuenta_list = self._get_list_instance_cuenta
        _total_amount: float = 0.0

        try:
            for index in range(0, len(_transactions)):
                _total_amount = _cuenta_list[index].monto
                _total_amount += _transactions[index].get('monto')
                _cuenta_list[index].monto = round(_total_amount, 2)

        except IndexError as e:
            cuenta.objects.bulk_update(objs=_cuenta_list, fields=['monto'])
        else:
            cuenta.objects.bulk_update(objs=_cuenta_list, fields=['monto'])


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
# class SendNotificationDispersaBeneficiarios:
#     def __init__(self, transaction_info: ListTransactionInfo):
#         self._transaction_info = transaction_info
#         self._send_notification()
#
#     def _send_notification(self) -> NoReturn:
#         for account in self._transaction_info.list_transaction:
#             preparingNotification(cuentaBeneficiario=account.get('cta_beneficiario'), opcion=3)


if __name__ == '__main__':
    shedule_transaction = ListTransactionSheduleToday()
    try:
        if len(shedule_transaction.list_massive_id) >= 1 or len(shedule_transaction.list_transaction_id):
            list_transaction_info = ListTransactionInfo(shedule_transaction)
            deposit = BeneficiaryDeposits(list_transaction_info)
            list_transaction_info.chage_status_transaction()
            list_transaction_info.chage_status_transaction_massive()
            SendMailBeneficiario(list_transaction_info)
            # SendNotificationDispersaBeneficiarios(list_transaction_info)
    except Exception as e:
        # (ChrGil 2022-02-21) Si hay una excepción no hagas nada
        print(e)
        pass
