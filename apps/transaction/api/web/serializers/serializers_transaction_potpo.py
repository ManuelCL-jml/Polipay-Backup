from rest_framework.serializers import *
from typing import Dict, List, ClassVar, Any, Union

from apps.transaction.models import transferencia


class SerializerTransactioPolipayToPolipay(Serializer):
    cta_beneficiario = CharField()
    monto = FloatField()
    nombre_beneficiario = CharField()
    concepto_pago = CharField()
    referencia_numerica = CharField()

    def validate_monto(self, value: float) -> float:
        if value < 1:
            raise ValueError("El monto no es válido")

        if self.context.get('monto') < value:
            raise ValueError("Saldo insuficiente")
        return value

    def validate_cta_beneficiario(self, value: str) -> str:
        if len(value) != 18:
            raise ValueError("Cuenta clabe no valida")

        if self.context.get("cuenta_emisor") == value:
            raise ValueError("No se encontró ningún beneficiario asociado a esa cuenta")
        return value

    def validate_nombre_beneficiario(self, value: str) -> str:
        return value.upper()

    def validate_concepto_pago(self, value: str) -> str:
        if len(value) > 40:
            raise ValueError('Asegúrese que la longitud no sea mayor a 40')
        return value

    def validate_referencia_numerica(self, value) -> int:
        if len(value) > 7:
            raise ValueError('Asegúrese que la longitud no sea mayor a 7')
        return int(value)

    def update_items_data(self, attrs: Dict[str, Any], context: Dict[str, Any]):
        attrs["cuenta_emisor"] = context.get("cuenta_emisor")
        attrs["nombre_emisor"] = context.get("nombre_emisor")
        attrs["rfc_curp_emisor"] = "ND" if not context.get("rfc_curp_emisor") else context.get("rfc_curp_emisor")
        attrs["rfc_curp_beneficiario"] = "ND" if not context.get("rfc_curp_beneficiario") else context.get("rfc_curp_beneficiario")
        attrs["empresa"] = context.get("empresa")
        attrs["created_to"] = context.get("created_to")
        attrs["saldo_remanente"] = context.get("saldo_remanente_emisor")
        attrs["cuentatransferencia_id"] = context.get("cuentatransferencia_id")
        return attrs

    def validate(self, attrs):
        return self.update_items_data(attrs, self.context)

    def create(self, **kwargs) -> transferencia:
        return transferencia.objects.create_transaction_polipay_to_polipay_v2(**self.validated_data)
