from typing import ClassVar, Dict, Any


# (ChrGil 2022-02-02) Cambia las keys del json_response a uno más estandarizado
class JsonResponseDetailTransactionReceived:
    _json_response: ClassVar[Dict[str, Any]] = {
        "id": "id",
        "nombre_beneficiario": "NombreBeneficiario",
        "cta_beneficiario": "CuentaBeneficiario",
        "receiving_bank__institucion": "BancoBeneficiario",
        "cuenta_emisor": "CuentaEmisor",
        "nombre_emisor": "NombreEmisor",
        "transmitter_bank__institucion": "BancoEmisor",
        "monto": "monto",
        "concepto_pago": "ConceptoPago",
        "referencia_numerica": "ReferenciaNumerica",
        "fecha_creacion": "FechaCreacion",
        "tipo_pago__nombre_tipo": "TipoPago",
    }

    def __init__(self, json_data: Dict[str, Any]):
        self.json_data = self._change_key(json_data)

    def _change_key(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        return {value: json_data.get(key) for key, value in self._json_response.items()}


class JsonResponseDetailTransactionTercerosInidivual:
    _json_response: ClassVar[Dict[str, Any]] = {
        "id": "id",
        "clave_rastreo": "ClaveRastreo",
        "nombre_beneficiario": "NombreBeneficiario",
        "cta_beneficiario": "CuentaBeneficiario",
        "receiving_bank__institucion": "BancoBeneficiario",
        "cuenta_emisor": "CuentaEmisor",
        "nombre_emisor": "NombreEmisor",
        "empresa": "NombreEmpresa",
        "rfc_curp_emisor": "RfcCurpEmisor",
        "monto": "monto",
        "concepto_pago": "ConceptoPago",
        "referencia_numerica": "ReferenciaNumerica",
        "fecha_creacion": "FechaCreacion",
        "tipo_pago__nombre_tipo": "TipoPago",
        "email": "EmailBeneficiario",
        "emisor_empresa__name": "PersonaRealizaOperacionName",
        "emisor_empresa__last_name": "PersonaRealizaOperacionLastName",
        "user_autorizada__name": "PersonaAutorizaOperacionName",
        "user_autorizada__last_name": "PersonaAutorizaOperacionLastName",
    }

    def __init__(self, json_data: Dict[str, Any], **kwargs):
        self.json_data = self._change_key(json_data)
        self.json_data['FechaModify'] = kwargs.get('sheluded', None)

    def _change_key(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        return {value: json_data.get(key) for key, value in self._json_response.items()}
