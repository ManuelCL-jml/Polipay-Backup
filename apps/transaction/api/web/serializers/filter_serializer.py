import datetime as dt
from typing import Any, Dict, ClassVar, NoReturn, Union

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db.transaction import atomic

from rest_framework.serializers import *

from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Utils.utils import generate_clave_rastreo_with_uuid
from apps.api_stp.client import CosumeAPISTP
from apps.api_stp.exc import StpmexException
from apps.api_stp.management import SetFolioOpetacionSTP
from apps.api_stp.signature import SignatureMassiveTestAPIStp, SignatureTestAPIStpIndividual, \
    SignatureTestAPIStpIndividualJSON, SignatureProductionAPIStpIndividual, SignatureTesterAPIStpIndividual
from apps.transaction.messages import message_email
from apps.transaction.models import transferencia, detalleTransferencia, transmasivaprod
from apps.users.models import cuenta
from apps.transaction.management import preparingNotification


# (ChrGil 2021-11-30) Cambia el estado de una transacción masiva si
# (ChrGil 2021-11-30) el estado de las transacciones individuales
# (ChrGil 2021-11-30) son (liquidada o devuelta)
def change_bulk_transaction_status(id_transfer: int) -> bool:
    try:

        # (ChrGil 2021-11-30) Regresa el id si es una transacción masiva, si no regresa False
        massive_id: int = transferencia.objects.select_related(
            'masivo_trans'
        ).filter(masivo_trans_id__isnull=False).get(id=id_transfer).get_masivo_trans

    except ObjectDoesNotExist as e:
        return False

    else:

        # (ChrGil 2021-11-30) Regresa el numero total de transferencias individuales de una masiva
        total_bulk_transfers_1: int = transferencia.objects.select_related(
            'masivo_trans'
        ).filter(
            masivo_trans_id=massive_id
        ).count()

        # (ChrGil 2021-11-30) Regresa el numero total de transferencias individuales de una masiva con el estado
        # (ChrGil 2021-11-30) liquidada o devuelta
        total_bulk_transfers_2: int = transferencia.objects.select_related(
            'status_trans',
            'masivo_trans'
        ).filter(
            Q(status_trans_id=1) |
            Q(status_trans_id=7),
            masivo_trans_id=massive_id
        ).count()

        # (ChrGil 2021-11-30) Si el numero de transacciones individuales de una masiva es igual
        # (ChrGil 2021-11-30) al numero de transacciones individuales de una masiva con el estado (liquidada o devuelta)
        # (ChrGil 2021-11-30) cambia el estado de la transacción masiva a PROCESADA
        if total_bulk_transfers_1 == total_bulk_transfers_2:
            transmasivaprod.objects.change_status_massive(massive_id, status_id=5)
            return True

        return False


class RegistraOrdenSTP:
    _info_transaction: ClassVar[Dict[str, Any]]

    def __init__(self, transaction_id: int, demo_bool: bool):
        self._transaction_id = transaction_id
        self._demo_bool = demo_bool
        self._info_transaction = self._get_info_transaction
        self._put()

    @property
    def _get_info_transaction(self) -> Dict[str, Any]:
        return transferencia.filter_transaction.get_info_transaction_stp_individual(self._transaction_id)

    def _put(self) -> NoReturn:
        try:
            json_stp_data = SignatureProductionAPIStpIndividual(self._info_transaction)
            api = CosumeAPISTP(json_stp_data.json_data_registra_orden, demo_bool=self._demo_bool)
            SetFolioOpetacionSTP(api.response, json_stp_data.json_data_registra_orden.get('claveRastreo'))
        except StpmexException as e:
            err = MyHttpError(message=e.msg, real_error="STP Error", error_desc=e.desc)
            raise ValidationError(err.standard_error_responses())


class InfoTransactionPendiente:
    info_transaction: ClassVar[Dict[str, Any]]

    def __init__(self, transaction_id: int):
        self._transaction_id = transaction_id

        if not self._exists_transaction:
            raise ValueError('La transacción no ha sido autorizada o la transacción ya fue devuelta ó liquidada')

        self.info_transaction = self.get_info_transaction

    @property
    def _exists_transaction(self) -> bool:
        return transferencia.objects.filter(
            id=self._transaction_id,
            status_trans_id=3,
            user_autorizada_id__isnull=False
        ).exists()

    @property
    def get_info_transaction(self) -> Dict[str, Any]:
        return transferencia.objects.filter(id=self._transaction_id).values(
            'id',
            'cta_beneficiario',
            'nombre_beneficiario',
            'rfc_curp_beneficiario',
            't_ctaBeneficiario',
            'monto',
            'referencia_numerica',
            'empresa',
            't_ctaEmisor',
            'nombre_emisor',
            'cuenta_emisor',
            'rfc_curp_emisor',
            'email',
            'saldo_remanente',
            'cuentatransferencia_id',
            'masivo_trans_id',
            'transmitter_bank_id',
            'receiving_bank_id',
            'emisor_empresa_id',
            'date_modify',
            'clave_rastreo',
            'cuentatransferencia__persona_cuenta_id',
            'concepto_pago'
        ).first()


def obtener_monto_actual(data: Dict[str, Any]):
    cuenta_emisor: Dict[str, Any] = cuenta.objects.filter(
        id=data.get("cuentatransferencia_id")).values(
        'id', 'monto'
    ).first()

    saldo_remanente = cuenta_emisor.get('monto') + data.get('monto')
    return saldo_remanente


# (ChrGil 2022-05-11) Devulve la transacción al emisor, creando una transferencia recibida al emisor
def devolver_transaccion(transaction_info: Dict[str, Any], saldo_remanente: float) -> transferencia:
    return transferencia.objects.create(
        cta_beneficiario=transaction_info.get('cuenta_emisor'),
        nombre_beneficiario=transaction_info.get('nombre_emisor'),
        rfc_curp_beneficiario=transaction_info.get('rfc_curp_emisor'),
        t_ctaBeneficiario=transaction_info.get('t_ctaEmisor'),
        monto=transaction_info.get('monto'),
        referencia_numerica=transaction_info.get('referencia_numerica'),
        empresa=transaction_info.get('empresa'),
        t_ctaEmisor=transaction_info.get('t_ctaBeneficiario'),
        nombre_emisor=transaction_info.get('nombre_beneficiario'),
        cuenta_emisor=transaction_info.get('cta_beneficiario'),
        rfc_curp_emisor=transaction_info.get('rfc_curp_beneficiario'),
        email=transaction_info.get('email'),
        saldo_remanente_beneficiario=saldo_remanente,
        cuentatransferencia_id=transaction_info.get('cuentatransferencia_id'),
        masivo_trans_id=transaction_info.get('masivo_trans_id'),
        transmitter_bank_id=transaction_info.get('receiving_bank_id'),
        receiving_bank_id=transaction_info.get('receiving_bank_id'),
        emisor_empresa_id=transaction_info.get('emisor_empresa_id'),
        concepto_pago='Transacción Devuelta',
        tipo_pago_id=5,
        status_trans_id=1,
        date_modify=dt.datetime.now(),
        clave_rastreo=generate_clave_rastreo_with_uuid()
    )


class SendMailBeneficiario:
    def __init__(self, transaction_info: InfoTransactionPendiente):
        self._transaction_info = transaction_info.info_transaction
        email = transaction_info.info_transaction.get('email')
        if email != 'ND':
            if email:
                self._send_mail()

    @property
    def _context_data_email(self):
        folio = f"{dt.datetime.now().strftime('%Y%m%d%H%S')}"

        return {
            "folio": folio,
            "name": self._transaction_info.get('nombre_beneficiario'),
            "fecha_operacion": self._transaction_info.get('date_modify'),
            "observation": self._transaction_info.get('concepto_pago'),
            "nombre_emisor": self._transaction_info.get('empresa'),
            "monto": self._transaction_info.get('monto'),
            "status": "LIQUIDADA",
            "clave_rastreo": self._transaction_info.get('clave_rastreo'),
        }

    def _send_mail(self) -> NoReturn:
        message_email(
            template_name='transaction_terceros_beneficiario.html',
            context=self._context_data_email,
            title='Transacción recibida',
            body=self._transaction_info.get('concepto_pago'),
            email=self._transaction_info.get('email')
        )


# (ChrGil 2022-02-08) Regresa el monto de la transacción a al monto del emisor
class DepositAmountEmisor:
    def __init__(self, transaction: InfoTransactionPendiente):
        self._transaction = transaction
        self._persona_cuenta_id = transaction.get_info_transaction.get('cuentatransferencia__persona_cuenta_id')
        self._deposit_amount()

    def _deposit_amount(self) -> NoReturn:
        cuenta.objects.deposit_amount(self._persona_cuenta_id, self._transaction.get_info_transaction.get('monto'))


class ChangeStatusTransaction:
    _deposit_amount: ClassVar[DepositAmountEmisor] = DepositAmountEmisor
    _send_email: ClassVar[SendMailBeneficiario] = SendMailBeneficiario

    def __init__(
            self,
            transaction: InfoTransactionPendiente,
            status_id: int,
            motivo: Union[str, None],
            context: Dict[str, Any]
    ):
        self._transaction = transaction
        self._status_id = status_id
        self._motivo = motivo

        if status_id == 1:
            self._enviada_stp()
            change_bulk_transaction_status(transaction.get_info_transaction.get('id'))
            RegistraOrdenSTP(context.get('transaction_id'), context.get('demo_bool'))
            try:
                self._send_email(transaction)
            except Exception as e:
                print(e)

        if status_id == 7:
            if self._motivo is None:
                raise ValueError('Debes definir un motivo, por la devuelta de la transacción')

            self._devolver()
            self._motivo_devuelta()
            self._deposit_amount(transaction)
            change_bulk_transaction_status(transaction.get_info_transaction.get('id'))

    def _enviada_stp(self) -> NoReturn:
        transferencia.objects.filter(
            id=self._transaction.get_info_transaction.get('id')
        ).update(
            status_trans_id=4,
            date_modify=dt.datetime.now()
        )

    def _devolver(self):
        saldo_remanente = obtener_monto_actual(self._transaction.info_transaction)
        devolver_transaccion(self._transaction.info_transaction, saldo_remanente)
        transferencia.objects.filter(
            id=self._transaction.get_info_transaction.get('id')
        ).update(
            status_trans_id=7,
            date_modify=dt.datetime.now()
        )

    def _motivo_devuelta(self):
        detalleTransferencia.objects.create(
            transfer_id=self._transaction.get_info_transaction.get('id'),
            json_content=self._motivo
        )


# (ChrGil 2021-11-29) Cambia el estado de transacción ya sea a liquidada o devuelta
class ChangeStatusSerializer(Serializer):
    _transaction_info: ClassVar[InfoTransactionPendiente] = InfoTransactionPendiente

    status_trans_id = IntegerField()
    motivo = CharField(allow_null=True, allow_blank=True)

    def validate(self, attrs):
        return attrs

    def update_transfer(self, validated_data):
        status_trans_id = validated_data['status_trans_id']
        motivo = validated_data['motivo']
        transaction_info = self._transaction_info(self.context.get('transaction_id'))

        ChangeStatusTransaction(transaction_info, status_trans_id, motivo, self.context)
        idDeTransferencia = self.context.get('transaction_id')

        # (Liquidar) Notifica al emisor (1)
        # (Devolver) Notifica al emisor (7)
        # preparingNotification(idDeTransferencia=idDeTransferencia, opcion=1)
