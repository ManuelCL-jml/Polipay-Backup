import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import ClassVar, Any, Dict, List

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Q
from django.db.transaction import atomic

from rest_framework.serializers import *

from MANAGEMENT.Standard.errors_responses import ErrorResponseSTP
from MANAGEMENT.Supplier.STP.stp import CatCambioEstado, CatCausasDevolucion
from MANAGEMENT.Utils.utils import generate_clave_rastreo_with_uuid
from apps.api_stp.models import Supplier_transactions
from apps.transaction.models import transferencia, detalleTransferencia, transmasivaprod
from apps.users.models import cuenta
from polipaynewConfig.settings import CLABE_POLIPAY_COMISSION


class ChangeStatus(ABC):
    """ 1. Polipay a Polipay, 2. Polipay a terceros, 10. Saldos Wallet """
    _tipo_pago_aceptado: ClassVar[List] = [
        1, 2, 10
    ]

    @abstractmethod
    def _change_status(self) -> None:
        ...

    @abstractmethod
    def _get_transaction_data(self) -> None:
        ...

    @abstractmethod
    def _change_status_massive_transaction(self) -> None:
        ...

    @abstractmethod
    def _send_notification(self) -> None:
        ...

    @abstractmethod
    def get_transfer_id(self) -> None:
        ...


class DevolverTransaccion(ChangeStatus):
    @abstractmethod
    def _devolver(self) -> None:
        ...

    @abstractmethod
    def _create_detail_transaction(self) -> None:
        ...


class CancelarTransaccion(ChangeStatus):
    @abstractmethod
    def _devolver(self) -> None:
        ...


# (ChrGil 2021-11-30) Cambia el estado de una transacción masiva si
# (ChrGil 2021-11-30) el estado de las transacciones individuales
# (ChrGil 2021-11-30) tienen el estado (liquidada o devuelta)
def change_bulk_transaction_status(transaction_id: int) -> bool:
    try:

        # (ChrGil 2021-11-30) Regresa el id si es una transacción masiva, si no regresa False
        massive_id: int = transferencia.objects.select_related(
            'masivo_trans'
        ).filter(masivo_trans_id__isnull=False).get(id=transaction_id).get_masivo_trans

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
        date_modify=datetime.datetime.now(),
        clave_rastreo=generate_clave_rastreo_with_uuid()
    )


@dataclass
class Liquidar(ChangeStatus):
    _transaction_data: ClassVar[Dict[str, Any]]

    _cat_beneficiarios: ClassVar[List[int]] = [
        CLABE_POLIPAY_COMISSION,
    ]

    """ 1. Polipay a Plipay, 10. Fondeo Saldos Wallet """
    _tipo_pago_aceptado: ClassVar[List[int]] = [
        1, 2, 10
    ]

    def __init__(self, folio_origen: str, status: int, context: Dict[str, Any]):
        self.folio_origen = folio_origen
        self.status = status
        self.context = context
        self.transaction_data = self._get_transaction_data()

        if self.transaction_data.get("tipo_pago_id") in self._tipo_pago_aceptado:
            self._change_status()
            self._change_status_massive_transaction()
            self._send_notification()

    def _get_transaction_data(self) -> Dict[str, Any]:
        return transferencia.objects.filter(
            clave_rastreo=self.folio_origen,
            tipo_pago_id__in=self._tipo_pago_aceptado
        ).values(
            'id',
            'cta_beneficiario',
            'emisor_empresa_id',
            'tipo_pago_id'
        ).first()

    def _change_status(self) -> None:
        transaction_id = self.transaction_data.get('id')
        if self.transaction_data.get("tipo_pago_id") in self._tipo_pago_aceptado:
            transferencia.objects.filter(id=transaction_id).update(
                status_trans_id=self.status,
                date_modify=datetime.datetime.now()
            )

    def get_transfer_id(self) -> int:
        return self.transaction_data.get('id')

    def _change_status_massive_transaction(self) -> None:
        change_bulk_transaction_status(self.transaction_data.get('id'))

    def _send_notification(self) -> None:
        if self.transaction_data.get('emisor_empresa_id'):
            # Notificar al emisor/receptor de la transferencia
            # (Liquidar) Notifica al emisor (1)
            # (Devolver) Notifica al emisor (7)
            # preparingNotification(idDeTransferencia=self._transaction_data.get('id'), opcion=1)
            ...


class Devolver(DevolverTransaccion):
    _transaction_data: ClassVar[Dict[str, Any]]

    """ 1. Polipay a Plipay, 10. Fondeo Saldos Wallet """
    _tipo_pago_aceptado: ClassVar[List[int]] = [
        1, 2, 10
    ]

    def __init__(self, folio_origen: str, status: int, motivo: str, context: Dict[str, Any]):
        self.folio_origen = folio_origen
        self.status = status
        self.motivo = motivo
        self.context = context
        self._transaction_data = self._get_transaction_data()

        if self._transaction_data.get("tipo_pago_id") in self._tipo_pago_aceptado:
            self._change_status()
            self._change_status_massive_transaction()
            self._send_notification()

    def _get_transaction_data(self) -> Dict[str, Any]:
        return transferencia.objects.filter(
            clave_rastreo=self.folio_origen,
            tipo_pago_id__in=self._tipo_pago_aceptado
        ).values(
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
            'concepto_pago',
            'tipo_pago_id'
        ).first()

    def _change_status(self) -> None:
        if self.motivo is None:
            message = 'Debes de definir un motivo de devolución'
            err = ErrorResponseSTP(message=message, code=400)
            self.context.get('log').json_response(err.error)
            raise ValidationError(err.error)

        saldo_remanente = obtener_monto_actual(self._transaction_data)
        devolver_transaccion(self._transaction_data, saldo_remanente)
        transferencia.objects.filter(id=self._transaction_data.get('id')).update(
            status_trans_id=self.status,
            date_modify=datetime.datetime.now()
        )

        self._create_detail_transaction()
        self._devolver()

    def _change_status_massive_transaction(self) -> None:
        change_bulk_transaction_status(self._transaction_data.get('id'))

    # (ChrGil 2021-12-22) Registra en la bd el motivo por el que se devolvio la transacción
    def _create_detail_transaction(self) -> None:
        detalleTransferencia.objects.create(transfer_id=self._transaction_data.get('id'), json_content=self.motivo)

    def get_transfer_id(self) -> int:
        return self._transaction_data.get('id')

    def _devolver(self) -> None:
        instance: cuenta = cuenta.objects.get(id=self._transaction_data.get('cuentatransferencia_id'))
        instance.monto += self._transaction_data.get('monto')
        instance.save()

    def _send_notification(self) -> None:
        if self._transaction_data.get('emisor_empresa'):
            # Notificar al emisor/receptor de la transferencia
            # (Liquidar) Notifica al emisor (1)
            # (Devolver) Notifica al emisor (7)
            # preparingNotification(idDeTransferencia=self._transaction_data.get('id'), opcion=1)
            ...


class Cancelar(CancelarTransaccion):
    _transaction_data: ClassVar[Dict[str, Any]]

    def __init__(self, folio_origen: str, status: int, context: Dict[str, Any]):
        self.folio_origen = folio_origen
        self.status = status
        self.context = context
        self._transaction_data = self._get_transaction_data()

        if self._transaction_data.get("tipo_pago_id") in self._tipo_pago_aceptado:
            self._change_status()
            self._send_notification()

    def _get_transaction_data(self) -> Dict[str, Any]:
        return transferencia.objects.filter(
            clave_rastreo=self.folio_origen).values(
            'id', 'cuenta_emisor', 'monto', 'emisor_empresa_id', 'cuentatransferencia_id', 'tipo_pago_id').first()

    def _change_status(self) -> None:
        saldo_remanente = obtener_monto_actual(self._transaction_data)
        devolver_transaccion(self._transaction_data, saldo_remanente)
        transferencia.objects.filter(id=self._transaction_data.get('id')).update(
            status_trans_id=self.status,
            date_modify=datetime.datetime.now()
        )

        self._devolver()

    def _change_status_massive_transaction(self) -> None:
        change_bulk_transaction_status(self._transaction_data.get('id'))

    def get_transfer_id(self) -> int:
        return self._transaction_data.get('id')

    def _devolver(self) -> None:
        instance: cuenta = cuenta.objects.get(id=self._transaction_data.get('cuentatransferencia_id'))
        instance.monto += self._transaction_data.get('monto')
        instance.save()

    def _send_notification(self) -> None:
        if self._transaction_data.get('emisor_empresa'):
            # Notificar al emisor/receptor de la transferencia
            # (Liquidar) Notifica al emisor (1)
            # (Devolver) Notifica al emisor (7)
            # preparingNotification(idDeTransferencia=self._transaction_data.get('id'), opcion=1)
            ...


# (ChrGil 2021-12-22) Guarda registro de movimiento de STP
# (ChrGil 2021-12-22) _data_content: Dinccionario del JSON que se valida en el serializador
# (ChrGil 2021-12-22) _status_transfer: Intsnacia de clase abc, para saber que transacción es
# (ChrGil 2021-12-22) _cat_supplier: Catalogo de proveeder del servicio, este caso por fenición es (1) STP
class SaveRequestSTP:
    _data_content: ClassVar[Dict[str, Any]]
    _status_transfer: ClassVar[ChangeStatus]
    _cat_supplier: ClassVar[int]
    _fecha_consumo: ClassVar[datetime.datetime]

    def __init__(
            self,
            data_content: Dict[str, Any],
            status_transfer: ChangeStatus,
            cat_supplier: int,
            fecha_consumo: datetime.datetime
    ):
        self._data_content = data_content
        self._status_transfer = status_transfer
        self._cat_supplier = cat_supplier
        self._fecha_consumo = fecha_consumo
        self._create()

    def _create(self) -> None:
        Supplier_transactions.objects.create(
            transfer_id=self._status_transfer.get_transfer_id(),
            cat_supplier_id=self._cat_supplier,
            json_content=self._data_content,
            consumption_date=self._fecha_consumo
        )


# (ChrGil 2021-12-20) Cambio de estado de una transacción ("Cancelación",  "Liquidación" y "Devolución".)
class SerializerChangeStatus(Serializer):
    _cambio_estado_cat: ClassVar[CatCambioEstado] = CatCambioEstado()
    _causas_devolucion_cat: ClassVar[CatCausasDevolucion] = CatCausasDevolucion()

    id = IntegerField(max_value=120_000_000_000)
    empresa = CharField(max_length=15)

    # (ChrGil 2021-12-20) Por defecto es la clave rastreo, cuan se realizó la dispersión
    folioOrigen = CharField(max_length=50, allow_null=True)
    estado = CharField()
    causaDevolucion = CharField(allow_null=True, allow_blank=True)
    tsLiquidacion = CharField(max_length=14)

    def validate_folioOrigen(self, value: str) -> str:
        exists = transferencia.objects.filter(clave_rastreo=value).exists()

        if len(value) > 50:
            err = ErrorResponseSTP(message="Asegúrese que la longitud no sea mayor a 50 carateres", code=400)
            self.context.get('log').json_response(err.error)
            raise ValidationError(err.error)

        if not value.isalnum():
            err = ErrorResponseSTP(message="Asegúrese que el valor sea alfanumérico", code=400)
            self.context.get('log').json_response(err.error)
            raise ValidationError(err.error)

        if not exists:
            err = ErrorResponseSTP(message="Folio de origen no valido o no existe", code=404)
            self.context.get('log').json_response(err.error)
        #     raise ValidationError(err.error)
        return value

    def validate_estado(self, value: str) -> str:
        result = self._cambio_estado_cat.get_value(value)

        if result is None:
            err = ErrorResponseSTP(message="El estado no se encuentra catalogado", code=400)
            self.context.get('log').json_response(err.error)
            raise ValidationError(err.error)

        if len(value) > 15:
            err = ErrorResponseSTP(message="Asegúrese que la longitud no sea mayor a 15 caracteres", code=400)
            self.context.get('log').json_response(err.error)
            raise ValidationError(err.error)
        return result

    def validate_causaDevolucion(self, value: str):
        if value == "":
            return value
        return value

    def validate(self, attrs):
        return attrs

    def update_transfer(self, validated_data: Dict[str, Any], fecha_consumo: datetime.datetime) -> None:
        status = int(validated_data.get('estado'))
        motivo = validated_data.get('causaDevolucion')
        clave_rastreo = validated_data.get('folioOrigen')
        exists = transferencia.objects.filter(clave_rastreo=validated_data.get('folioOrigen')).exists()

        if exists:
            try:
                with atomic():
                    # (ChrGil 2021-12-22) Liquidada
                    if status == 1:
                        liquidar = Liquidar(clave_rastreo, status, self.context)
                        if liquidar.transaction_data.get('tipo_pago_id') == 2:
                            SaveRequestSTP(validated_data, liquidar, cat_supplier=1, fecha_consumo=fecha_consumo)

                    # (ChrGil 2021-12-22) Devuelta
                    if status == 7 or status == 5:
                        devolver = Devolver(clave_rastreo, status, motivo, self.context)
                        SaveRequestSTP(validated_data, devolver, cat_supplier=1, fecha_consumo=fecha_consumo)

            except (FieldDoesNotExist, MultipleObjectsReturned, ValueError) as e:
                message = "Ocurrió un error al momento de actualizar el estado de esta transferencia"
                err = ErrorResponseSTP(message=message, code=400, real_error=str(e))
                self.context.get('log').json_response(err.error)
                raise ValidationError(err.error)
