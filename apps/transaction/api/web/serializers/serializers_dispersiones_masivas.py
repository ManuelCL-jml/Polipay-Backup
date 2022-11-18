import base64
import datetime as dt
from typing import Dict, ClassVar, Any, Union

from django.db.models import Q

from rest_framework.serializers import *

from MANAGEMENT.Utils.utils import strftime
from apps.transaction.exc import RazonSocialDoesNotExist, AccountDoesNotExist
from polipaynewConfig.exceptions import ErrorsList
from apps.users.models import grupoPersona, cuenta, persona
from apps.transaction.models import (
    transmasivaprod,
    transferencia,
    TransMasivaProg, transferenciaProg)


class SerializerRazonSocial(Serializer):
    _cuenta_eje_id: ClassVar[int]
    _razon_social_id: ClassVar[int]
    _administrative_id: ClassVar[int]

    razon_social_id = IntegerField()
    cuenta_eje_id = IntegerField()
    administrative_id = IntegerField()

    def validate(self, attrs):
        attr = dict(attrs)
        self._cuenta_eje_id = attr.get('cuenta_eje_id')
        self._razon_social_id = attr.get('razon_social_id')

        if not grupoPersona.objects.belonging_to_cuenta_eje(self._cuenta_eje_id, self._razon_social_id):
            raise RazonSocialDoesNotExist('Razón social no valido o no existe')

        if not cuenta.objects.filter(persona_cuenta_id=self._razon_social_id, is_active=True).exists():
            raise AccountDoesNotExist('Cuenta de la razón social no valido o no esta activo')

        return attrs

    @property
    def get_info_account_razon_social(self) -> Dict[str, Union[str, int, bool, float]]:
        return cuenta.objects.filter(persona_cuenta_id=self._razon_social_id).values(
            'id', 'monto', 'is_active', 'cuentaclave').first()

    @property
    def get_info_razon_social(self) -> Dict[str, Union[int, str]]:
        return persona.objects.filter(id=self._razon_social_id).values('id', 'name').first()

    @property
    def get_info_admin(self) -> Dict[str, Union[int, str]]:
        return persona.objects.filter(id=self._administrative_id).values('id', 'email').first()


# (ChrGil 2021-11-02) Crear archivo de xlsx
def create_xlsx_file(file, cost_center: str):
    decrypted = base64.b64decode(file)
    with open(f"TMP/cost_center_{cost_center}.xlsx", "wb") as file:
        file.write(decrypted)
    return file.name


# (ChrGil 2021-11-01) Serializador para crear una transferencia masiva
class SerializerMassiveDispersion(Serializer):
    observations = CharField()
    status = DateTimeField()
    user_admin_id = DateTimeField()

    def validate(self, attrs):
        return attrs

    def create(self, **kwargs) -> int:
        return transmasivaprod.objects.create_transaction_massive(**self.validated_data).get_only_id()


# (ChrGil 2021-11-03) Serializador para crear una transacción masiva programada
class SerializerTransMasivaProg(Serializer):
    _list_errors: ClassVar[ErrorsList] = ErrorsList()

    masivaReferida_id = IntegerField()
    fechaProgramada = DateTimeField(allow_null=True)
    fechaEjecucion = DateTimeField(allow_null=True)

    def validate(self, attrs):
        attr = dict(attrs)
        self._list_errors.clear_list()

        if attr.get('fechaProgramada') is None or attr.get('fechaEjecucion') is None:
            ErrorsList('fechaProgramada', attr.get('fechaProgramada'), 'Asegúrese de que este campo no este vacio')

        if len(self._list_errors.show_errors_list()) > 0:
            raise ValidationError(self._list_errors.standard_error_responses())

        self._list_errors.clear_list()
        return attrs

    def create(self, **kwargs):
        TransMasivaProg.objects.create(**self.validated_data)


# (ChrGil 2021-11-03) Serializador para crear una transacción individual programada
class SerializerTransInidivudalProg(Serializer):
    _list_errors: ClassVar[ErrorsList] = ErrorsList()

    transferReferida_id = IntegerField()
    fechaProgramada = DateTimeField(allow_null=True)
    fechaEjecucion = DateTimeField(allow_null=True)

    def validate(self, attrs):
        attr = dict(attrs)
        self._list_errors.clear_list()

        if attr.get('fechaProgramada') is None or attr.get('fechaEjecucion') is None:
            ErrorsList('fechaProgramada', attr.get('fechaProgramada'), 'Asegúrese de que este campo no este vacio')

        if len(self._list_errors.show_errors_list()) > 0:
            raise ValidationError(self._list_errors.standard_error_responses())

        self._list_errors.clear_list()
        return attrs

    def create(self, **kwargs):
        transferenciaProg.objects.create(**self.validated_data)


class SerializerDispersionIndividualMassive(Serializer):
    _list_errors: ClassVar[ErrorsList] = ErrorsList()

    # (ChrGil 2022-01-02) Data que envia el Cliente
    account = CharField()
    name = CharField()
    amount = FloatField()
    mail = CharField(allow_null=True, allow_blank=True)

    # (ChrGil 2022-01-02) Data que genera el servidor
    empresa = CharField(read_only=True)
    concepto_pago = CharField(read_only=True)
    referencia_numerica = CharField(read_only=True)
    programada = BooleanField(read_only=True)
    nombre_emisor = CharField(read_only=True)
    cuenta_emisor = CharField(read_only=True)
    cuentatransferencia_id = IntegerField(read_only=True)
    masivo_trans_id = IntegerField(read_only=True, allow_null=True)
    emisor_empresa_id = IntegerField(read_only=True)
    saldo_remanente = FloatField(read_only=True)

    def _errors_list_clear(self):
        self._list_errors.clear_list()

    def validate_account(self, value: str) -> str:
        self._errors_list_clear()

        if len(value) > 20:
            ErrorsList('account', value, 'Asegúrese de que este campo no tenga más de 20 caracteres.')

        data: Dict[str, Any] = cuenta.objects.filter(cuenta=value).values('is_active').first()
        if not data:
            ErrorsList('account', value, 'La cuenta del beneficiario no existe.')

        if data:
            if not data.get('is_active'):
                ErrorsList('cuenta_beneficiario', value, 'La cuenta del beneficiario no se encuentra activa')

        return value

    def validate_name(self, value: str) -> str:
        if len(value) > 40:
            ErrorsList('name', value, 'Asegúrese de que este campo no tenga más de 40 caracteres.')
        return value

    def validate_amount(self, value: float) -> float:
        if value < 1:
            ErrorsList('amount', str(value), 'Asegúrese que el monto no sea menor a 1')
        return value

    def validate(self, attrs):
        attr = dict(attrs)

        if not self.context.get('is_active_cuenta_emisor'):
            ErrorsList('ValidationError', attr.get('cuenta_emisor'), 'Su cuenta no esta activa')

        if self.context.get('monto_cuenta_emisor') < float(self.context.get('total_amount')):
            ErrorsList('ValidationError', self.context.get('monto_cuenta_emisor'), 'Saldo insuficiente')

        if len(self._list_errors.show_errors_list()) > 0:
            raise ValidationError(self._list_errors.standard_error_responses())

        attrs = self.update_attrs(attr, self.context)
        self._list_errors.clear_list()
        return attrs

    # (ChrGil 2021-12-27) Actualiza valores de los atributos del serializador
    def update_attrs(self, attrs: Dict[str, Any], context: Dict[str, Any]):
        attrs.update({"cuentatransferencia_id": context.get('cuentatransferencia_id')})
        attrs.update({"emisor_empresa_id": context.get('emisor_empresa_id')})
        attrs.update({"masivo_trans_id": context.get('massive_trans_id')})
        attrs.update({"nombre_emisor": context.get('nombre_emisor')})
        attrs.update({"cuenta_emisor": context.get('cuenta_emisor')})
        attrs.update({"programada": context.get('programada')})
        attrs.update({"referencia_numerica": strftime(dt.date.today())})
        attrs.update({"concepto_pago": context.get('observations')})
        attrs.update({"empresa": context.get('empresa').upper()})
        return attrs

    def create(self, **kwargs) -> transferencia:
        return transferencia.objects.create_object_dispersion(**self.validated_data)


class SerializerDispersionIndividual(Serializer):
    _list_errors: ClassVar[ErrorsList] = ErrorsList()

    # (ChrGil 2022-01-02) Data que envia el Cliente
    account = CharField()
    name = CharField()
    amount = FloatField()
    mail = CharField(allow_null=True, allow_blank=True)

    # (ChrGil 2022-01-02) Data que genera el servidor
    empresa = CharField(read_only=True)
    concepto_pago = CharField(read_only=True)
    referencia_numerica = CharField(read_only=True)
    programada = BooleanField(read_only=True)
    nombre_emisor = CharField(read_only=True)
    cuenta_emisor = CharField(read_only=True)
    cuentatransferencia_id = IntegerField(read_only=True)
    masivo_trans_id = IntegerField(read_only=True, allow_null=True)
    emisor_empresa_id = IntegerField(read_only=True)
    saldo_remanente = FloatField(read_only=True)

    def _errors_list_clear(self):
        self._list_errors.clear_list()

    def validate_account(self, value: str) -> str:
        self._errors_list_clear()

        if len(value) > 20:
            ErrorsList('account', value, 'Asegúrese de que este campo no tenga más de 20 caracteres.')

        data: Dict[str, Any] = cuenta.objects.filter(cuenta=value).values('is_active').first()
        if not data:
            ErrorsList('account', value, 'La cuenta del beneficiario no existe.')

        if data:
            if not data.get('is_active'):
                ErrorsList('cuenta_beneficiario', value, 'La cuenta del beneficiario no se encuentra activa')

        return value

    def validate_name(self, value: str) -> str:
        if len(value) > 40:
            ErrorsList('name', value, 'Asegúrese de que este campo no tenga más de 40 caracteres.')
        return value

    def validate_amount(self, value: float) -> float:
        if value < 1:
            ErrorsList('amount', str(value), 'Asegúrese que el monto no sea menor a 1')
        return value

    def validate(self, attrs):
        attr = dict(attrs)

        if not self.context.get('is_active_cuenta_emisor'):
            ErrorsList('ValidationError', attr.get('cuenta_emisor'), 'Su cuenta no esta activa')

        if self.context.get('monto_cuenta_emisor') < float(self.context.get('total_amount')):
            ErrorsList('ValidationError', self.context.get('monto_cuenta_emisor'), 'Saldo insuficiente')

        if len(self._list_errors.show_errors_list()) > 0:
            raise ValidationError(self._list_errors.standard_error_responses())

        attrs = self.update_attrs(attr, self.context)
        self._list_errors.clear_list()
        return attrs

    # (ChrGil 2021-12-27) Actualiza valores de los atributos del serializador
    def update_attrs(self, attrs: Dict[str, Any], context: Dict[str, Any]):
        attrs.update({"cuentatransferencia_id": context.get('cuentatransferencia_id')})
        attrs.update({"emisor_empresa_id": context.get('emisor_empresa_id')})
        attrs.update({"masivo_trans_id": context.get('massive_trans_id')})
        attrs.update({"nombre_emisor": context.get('nombre_emisor')})
        attrs.update({"cuenta_emisor": context.get('cuenta_emisor')})
        attrs.update({"programada": context.get('programada')})
        attrs.update({"referencia_numerica": strftime(dt.date.today())})
        attrs.update({"concepto_pago": context.get('observations')})
        attrs.update({"empresa": context.get('empresa').upper()})
        return attrs

    def create(self, **kwargs) -> int:
        instance = transferencia.objects.create_object_dispersion(**self.validated_data)
        instance.save()
        return instance.id


class SerializerTransactionPolipayComission(Serializer):
    empresa = CharField()
    monto = FloatField()
    nombre_emisor = CharField()
    cuenta_emisor = CharField()
    rfc_curp_emisor = CharField(allow_null=True)
    nombre_beneficiario = CharField()
    cta_beneficiario = CharField()
    rfc_curp_beneficiario = CharField(allow_null=True)
    cuentatransferencia_id = IntegerField(default=None)
    status_trans_id = IntegerField(read_only=True)
    saldo_remanente = FloatField(read_only=True, default=None)
    saldo_remanente_beneficiario = FloatField(read_only=True, default=None)

    @staticmethod
    def get_amount(account: str) -> Dict[str, Any]:
        return cuenta.objects.filter(
            Q(cuenta=account) | Q(cuentaclave=account)
        ).values('id', 'monto').first()

    def validate(self, attrs):
        amount_emisor = self.get_amount(attrs['cuenta_emisor'])
        amount_beneficiario = self.get_amount(attrs['cta_beneficiario'])

        # La transacción queda pendiente si es positiva
        if self.context.get('comission_type') == 1:
            attrs["status_trans_id"] = 3

        # La transacción es liquidada si es negativa
        if self.context.get('comission_type') == 2:
            attrs['saldo_remanente'] = amount_emisor.get('monto')
            attrs['saldo_remanente_beneficiario'] = amount_beneficiario.get('monto')
            attrs["status_trans_id"] = 3

        if self.context.get('is_shedule'):
            attrs["status_trans_id"] = 9

        return attrs

    def create(self, **kwargs) -> transferencia:
        return transferencia.objects.tranfer_to_polipay_comission(**self.validated_data)
