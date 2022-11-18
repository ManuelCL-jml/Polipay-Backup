from typing import Any, Dict

from django.db.models import Q
from django.db.transaction import atomic
from rest_framework.serializers import *

import datetime as dt

from apps.transaction.models import transferencia
from apps.users.models import cuenta


class CreateTransactionReceivedIn(Serializer):
    empresa = CharField(read_only=True, allow_null=False, allow_blank=False)
    nombre_emisor = CharField()
    transmitter_bank_id = IntegerField()
    cuenta_emisor = CharField()
    monto = FloatField()
    concepto_pago = CharField()
    referencia_numerica = CharField()
    clave_rastreo = CharField()
    date_modify = CharField()
    hora = CharField(write_only=True)
    nombre_beneficiario = CharField(read_only=True)
    cta_beneficiario = CharField(read_only=True)
    receiving_bank_id = IntegerField(read_only=True)
    rfc_curp_beneficiario = CharField(read_only=True)

    def validate_clave_rastreo(self, value: str) -> str:
        if len(value) > 30:
            raise ValidationError({'code': 400,
                                   'status': 'Error',
                                   'detail': 'Asegúrese que la longitud no sea mayor a 30 caracteres'})
        return value

    def validate_cuenta_emisor(self, value: str) -> str:
        if len(value) > 18:
            raise ValidationError({'code': 400,
                                   'status': 'Error',
                                   'detail': 'Asegúrese que la longitud no sea mayor a 18 digitos'})
        return value

    def validate_referencia_numerica(self, value: str) -> str:
        if len(value) > 7:
            raise ValidationError({'code': 400,
                                   'status': 'Error',
                                   'detail': 'Asegúrese que la longitud no sea mayor a 7 digitos'})
        return value

    def validate_monto(self, value: float):
        if value < 1:
            raise ValidationError({'code': 400,
                                   'status': 'Error',
                                   'detail': 'No es posible transferir montos en 0 o negativos'})
        return value

    def validate(self, attrs):
        date_modify = (attrs['date_modify'])
        hora = (attrs['hora'])

        attrs['empresa'] = self.context['cuenta_eje']
        attrs['nombre_beneficiario'] = self.context['nombre_beneficiario']
        attrs['cta_beneficiario'] = self.context['cuentaclave']
        attrs['date_modify'] = dt.datetime.strptime(f'{date_modify}{hora}', "%d/%m/%Y%H:%M")
        attrs['cuentatransferencia_id'] = self.context.get('cuenta_id')

        return attrs

    def create(self, **kwargs) -> transferencia:
        self.validated_data.pop('hora')
        instance_trans_recibida: transferencia = transferencia.objects.create_trans_rec(**self.validated_data)
        instance_trans_recibida.save()
        return instance_trans_recibida


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
            attrs['saldo_remanente'] = 0.0
            attrs['saldo_remanente_beneficiario'] = 0.0

        # La transacción es liquidada si es negativa
        if self.context.get('comission_type') == 2:
            attrs['saldo_remanente'] = amount_emisor.get('monto')
            attrs['saldo_remanente_beneficiario'] = amount_beneficiario.get('monto')
            attrs["status_trans_id"] = 1
        return attrs

    def create(self, **kwargs):
        transferencia.objects.tranfer_to_polipay_comission(**self.validated_data)


class SerializerCreateTransactionReceivedFisicPerson(Serializer):
    empresa = CharField(read_only=True, allow_null=True, allow_blank=True)
    nombre_emisor = CharField()
    transmitter_bank_id = IntegerField()
    cuenta_emisor = CharField()
    monto = FloatField()
    concepto_pago = CharField()
    referencia_numerica = CharField()
    clave_rastreo = CharField()
    date_modify = CharField()
    hora = CharField(write_only=True)
    nombre_beneficiario = CharField(read_only=True)
    cta_beneficiario = CharField(read_only=True)
    receiving_bank_id = IntegerField(read_only=True)
    rfc_curp_beneficiario = CharField(read_only=True)

    def validate_clave_rastreo(self, value: str) -> str:
        if len(value) > 30:
            raise ValidationError({'code': 400,
                                   'status': 'Error',
                                   'detail': 'Asegúrese que la longitud no sea mayor a 30 caracteres'})
        return value

    def validate_cuenta_emisor(self, value: str) -> str:
        if len(value) > 18:
            raise ValidationError({'code': 400,
                                   'status': 'Error',
                                   'detail': 'Asegúrese que la longitud no sea mayor a 18 digitos'})
        return value

    def validate_referencia_numerica(self, value: str) -> str:
        if len(value) > 7:
            raise ValidationError({'code': 400,
                                   'status': 'Error',
                                   'detail': 'Asegúrese que la longitud no sea mayor a 7 digitos'})
        return value

    def validate(self, attrs):
        date_modify = (attrs['date_modify'])
        hora = (attrs['hora'])

        attrs['empresa'] = self.context['cuenta_eje']
        attrs['nombre_beneficiario'] = self.context['nombre_beneficiario']
        attrs['cta_beneficiario'] = self.context['cuentaclave']
        attrs['date_modify'] = dt.datetime.strptime(f'{date_modify}{hora}', "%d/%m/%Y%H:%M")
        attrs['cuentatransferencia_id'] = self.context.get('cuenta_id')

        return attrs

    def create(self, **kwargs) -> transferencia:
        self.validated_data.pop('hora')
        instance_trans_recibida: transferencia = transferencia.objects.create_trans_rec(**self.validated_data)
        return instance_trans_recibida
