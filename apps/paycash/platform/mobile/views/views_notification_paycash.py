import datetime as dt
import json

from django.db.transaction import atomic
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework import status

from typing import Dict, List, Any, ClassVar, Union
from dataclasses import dataclass

from MANAGEMENT.notifications.movil.push import push_notify_paycash
from apps.logspolipay.manager import RegisterLog
from apps.notifications.models import notification
from apps.paycash.models import PayCashReference
from apps.paycash.platform.mobile.serializers.serializers_notification_paycash import SerializerPayCashNotifica
from apps.transaction.models import transferencia
from apps.users.models import cuenta
from polipaynewConfig.settings import COST_CENTER_POLIPAY_PAYCASH_COMISSION


@dataclass
class RequestDataPayCashNotifica:
    request_data: Dict[str, Any]

    @property
    def get_folio(self) -> int:
        return self.request_data.get("payment").get("Folio")

    @property
    def get_resultado(self) -> int:
        return self.request_data.get("payment").get("Resultado")

    @property
    def get_tipo(self) -> int:
        return self.request_data.get("payment").get("Tipo")

    @property
    def get_emisor(self) -> int:
        return self.request_data.get("payment").get("Emisor")

    @property
    def get_secuencia(self) -> int:
        return self.request_data.get("payment").get("Secuencia")

    @property
    def get_monto(self) -> float:
        return self.request_data.get("payment").get("Monto")

    @property
    def get_fecha(self) -> str:
        return self.request_data.get("payment").get("Fecha")

    @property
    def get_hora(self) -> str:
        return self.request_data.get("payment").get("Hora")

    @property
    def get_autorizacion(self) -> str:
        return self.request_data.get("payment").get("Autorizacion")

    @property
    def get_referencia(self) -> str:
        return self.request_data.get("payment").get("Referencia")

    @property
    def get_value(self) -> str:
        return self.request_data.get("payment").get("Value")

    @property
    def get_fecha_creacion(self) -> str:
        return self.request_data.get("payment").get("FechaCreacion")

    @property
    def get_fecha_confirmacion(self) -> str:
        return self.request_data.get("payment").get("FechaConfirmacion")

    @property
    def get_fecha_vencimiento(self) -> str:
        return self.request_data.get("payment").get("FechaVencimiento")


@dataclass
class GetReferenceInfo:
    request_data: RequestDataPayCashNotifica

    def __post_init__(self):
        reference = self.get_reference_info

        if reference:
            self.reference = reference

        if not reference:
            raise ValueError("Referencia no encontrada")

    @property
    def get_reference_info(self) -> Union[Dict[str, Any], None]:
        return PayCashReference.objects.detail_reference_with_value(self.request_data.get_value)


class CreatePayCashNotifica:
    _serializer_class: ClassVar[SerializerPayCashNotifica] = SerializerPayCashNotifica

    def __init__(self, request_data: RequestDataPayCashNotifica, referencia: GetReferenceInfo):
        self.request_data = request_data
        self.referencia = referencia
        self.create()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "type_reference_id": self.referencia.reference.get("type_reference_id"),
            "status_reference_id": self.referencia.reference.get("status_reference_id"),
        }

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "folio": self.request_data.get_folio,
            "resultado": self.request_data.get_resultado,
            "tipo": self.request_data.get_tipo,
            "emisor": self.request_data.get_emisor,
            "secuencia": self.request_data.get_secuencia,
            "monto": self.request_data.get_monto,
            "fecha": self.request_data.get_fecha,
            "hora": self.request_data.get_hora,
            "autorizacion": self.request_data.get_autorizacion,
            "referencia": self.request_data.get_referencia,
            "value": self.request_data.get_value,
            "fecha_creacion": self.request_data.get_fecha_creacion,
            "fecha_confirmacion": self.request_data.get_fecha_confirmacion,
            "fecha_vencimiento": self.request_data.get_fecha_vencimiento,
            "reference_id": self.referencia.reference.get("id"),
        }

    def create(self):
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.create()


@dataclass
class ChangeStatusReference:
    reference: GetReferenceInfo

    def __post_init__(self):
        status_id: int = 1
        reference_id = self.reference.reference.get("id")
        self._update(status_id, reference_id)

    @staticmethod
    def _update(status_id: int, reference_id: int):
        PayCashReference.objects.update_reference(
            reference_id,
            status_reference=status_id,
            date_modify=dt.datetime.now()
        )


@dataclass
class DepositPayment:
    request_data: RequestDataPayCashNotifica
    referencia: GetReferenceInfo

    def __post_init__(self):
        user_id = self.referencia.reference.get("persona_cuenta__persona_cuenta_id")
        self._deposit_amount(user_id, self.request_data.get_monto)

    @staticmethod
    def _deposit_amount(owner: int, amount: float):
        cuenta.objects.deposit_amount(owner, amount)


@dataclass
class WithdrawCommission:
    referencia: GetReferenceInfo

    def __post_init__(self):
        user_id = self.referencia.reference.get("persona_cuenta__persona_cuenta_id")
        amount = self.referencia.reference.get("comission_pay")
        self._debit_amount(user_id, amount)

    @staticmethod
    def _debit_amount(owner: int, amount: float):
        cuenta.objects.withdraw_amount(owner, amount)


@dataclass
class CreateInternalMovement:
    request_data: RequestDataPayCashNotifica
    referencia: GetReferenceInfo

    def __post_init__(self):
        self.tipo_pago_id = 9
        self.transaction = self.create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "rfc": self.referencia.reference.get("persona_cuenta__persona_cuenta__rfc"),
            "nombre_beneficiario": self.referencia.reference.get("persona_cuenta__persona_cuenta__name"),
            "email": self.referencia.reference.get("persona_cuenta__persona_cuenta__email"),
            "cuenta_beneficiario": self.referencia.reference.get("persona_cuenta__cuenta"),
            "cuentatransferencia_id": self.referencia.reference.get("persona_cuenta_id"),
            "concepto_pago": self.referencia.reference.get("payment_concept"),
            "referencia_numerica": self.request_data.get_referencia,
            "nombre_emisor": "PayCash Pago en Efectivo",
            "cuenta_emisor": self.request_data.get_referencia,
            "tipo_pago_id": self.tipo_pago_id,
            "monto": self.request_data.get_monto,
        }

    def create(self) -> transferencia:
        return transferencia.objects.create_internal_movement(**self._data)


@dataclass
class CreateInternalMovementComission:
    request_data: RequestDataPayCashNotifica
    referencia: GetReferenceInfo
    _withdraw_commission: ClassVar[WithdrawCommission] = WithdrawCommission
    _rs_polipay_comission: ClassVar[int] = COST_CENTER_POLIPAY_PAYCASH_COMISSION

    def __post_init__(self):
        self.tipo_pago_id = 1
        paycash_comission = self._get_info_polipay_paycash_comission

        if paycash_comission:
            self.paycash_comission = paycash_comission
            comission_pay = self.referencia.reference.get("comission_pay")
            self._deposit_amount(paycash_comission.get("persona_cuenta_id"), amount=comission_pay)
            saldo_remanente = self._saldo_remanente(paycash_comission.get("monto"), amount=comission_pay)
            self.saldo_remanente = saldo_remanente
            self.create()

        if not paycash_comission:
            raise ValueError("El beneficiario del pago de la comisión no existe")

    @property
    def _get_info_polipay_paycash_comission(self) -> Dict[str, Any]:
        return cuenta.objects.get_info_polipay_comission(self._rs_polipay_comission)

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "rfc": self.paycash_comission.get("persona_cuenta__rfc"),
            "nombre_beneficiario": self.paycash_comission.get("persona_cuenta__name"),
            "email": "ND",
            "cuenta_beneficiario": self.paycash_comission.get("cuentaclave"),
            "cuentatransferencia_id": self.referencia.reference.get("persona_cuenta_id"),
            "concepto_pago": "Comisión de depósito en efectivo PayCash",
            "referencia_numerica": self.request_data.get_referencia,
            "nombre_emisor": self.referencia.reference.get("persona_cuenta__persona_cuenta__name"),
            "cuenta_emisor": self.referencia.reference.get("persona_cuenta__cuenta"),
            "tipo_pago_id": self.tipo_pago_id,
            "monto": self.referencia.reference.get("comission_pay"),
            "saldo_remanente_beneficiario": self.saldo_remanente
        }

    def create(self):
        transferencia.objects.create_internal_movement(**self._data)

    @staticmethod
    def _deposit_amount(owner: int, amount: float):
        cuenta.objects.deposit_amount(owner, amount)

    @staticmethod
    def _saldo_remanente(amount_beneficiario: float, amount: float):
        amount_beneficiario += amount
        return amount_beneficiario


@dataclass
class CreateNotification:
    request_data: RequestDataPayCashNotifica
    reference: GetReferenceInfo
    transaction: CreateInternalMovement

    def __post_init__(self):
        self.title = "Depósito de pago en efectivo recibido"
        self.person_id = self.reference.reference.get("persona_cuenta__persona_cuenta_id")
        self.token_device = self.reference.reference.get("persona_cuenta__persona_cuenta__token_device")
        self.create()
        self.send_notification()

    @property
    def _title(self) -> str:
        return self.title

    @staticmethod
    def _body(amount: float) -> str:
        return f"PayCash te envió un depósito en efectivo de ${amount:3,.2f} a tu cuenta Polipay"

    @property
    def _detail(self) -> Dict[str, Any]:
        return self.transaction.transaction.notification_detail

    @property
    def _data(self):
        return {
            "titulo": self._title,
            "cuerpo": self._body(self.request_data.get_monto),
            "detalle": self._detail
        }

    def create(self):
        notification.objects.create(
            person_id=self.person_id,
            notification_type_id=1,
            json_content=json.dumps(self._data),
            transaction_id=self.transaction.transaction.id
        )

    def send_notification(self):
        push_notify_paycash(
            title=self._title,
            person_id=self.person_id,
            message=self._body(self.request_data.get_monto),
            detail=self._data,
            token=self.token_device,
            number_notification=notification.objects.get_number_notification(self.person_id)
        )


class PayCashNotifica(GenericViewSet):
    _request_data: ClassVar[RequestDataPayCashNotifica] = RequestDataPayCashNotifica
    _notified: ClassVar[CreatePayCashNotifica] = CreatePayCashNotifica
    _reference_info: ClassVar[GetReferenceInfo] = GetReferenceInfo
    _change_status: ClassVar[ChangeStatusReference] = ChangeStatusReference
    _deposit_payment: ClassVar[DepositPayment] = DepositPayment
    _withdraw_commission: ClassVar[WithdrawCommission] = WithdrawCommission
    _create_internal_movement: ClassVar[CreateInternalMovement] = CreateInternalMovement
    _create_internal_movement_comission: ClassVar[CreateInternalMovementComission] = CreateInternalMovementComission
    _notify: ClassVar[CreateNotification] = CreateNotification
    _log: ClassVar[RegisterLog] = RegisterLog
    permission_classes = ()

    def create(self, request):
        log = self._log(0, request)

        try:
            with atomic():
                log.json_request(request.data)
                request_data = self._request_data(request.data)
                referencia = self._reference_info(request_data)
                self._notified(request_data, referencia)
                transaction = self._create_internal_movement(request_data, referencia)
                self._create_internal_movement_comission(request_data, referencia)
                self._change_status(referencia)
                self._deposit_payment(request_data, referencia)
                self._withdraw_commission(referencia)
                self._notify(request_data, referencia, transaction)

        except Exception as e:
            err = {"code": 400, "message": str(e)}
            log.json_response(err)
            return Response(err, status=status.HTTP_400_BAD_REQUEST)
        else:
            succ = {"code": 200, "message": "Payment successfully notified"}
            log.json_response({"success": succ})
            return Response(succ, status=status.HTTP_200_OK)
