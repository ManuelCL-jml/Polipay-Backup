from typing import Dict, ClassVar
from apps.transaction.models import transferencia


class RenderJSONRegistraOrdenTest:
    render_json_stp: ClassVar[Dict[str, str]]

    def __init__(self, **kwargs):
        self.render_json_stp = self._render_json_stp(**kwargs)

    @staticmethod
    def _render_json_stp(**kwargs) -> Dict[str, str]:
        return {
            "claveRastreo": kwargs.pop('clave_rastreo'),
            "conceptoPago": kwargs.pop('concepto_pago'),
            "cuentaBeneficiario": "646180110400000007",
            "cuentaOrdenante": "646180171800000002",
            "empresa": "BECPOLIMENTES",
            "institucionContraparte": "90646",
            "institucionOperante": "90646",
            "monto": f"{kwargs.pop('monto'):.2f}",
            "nombreBeneficiario": kwargs.pop('nombre_beneficiario'),
            "nombreOrdenante": kwargs.pop('nombre_emisor'),
            "referenciaNumerica": kwargs.pop('referencia_numerica'),
            "rfcCurpBeneficiario": kwargs.pop('rfc_curp_beneficiario'),
            "rfcCurpOrdenante": kwargs.pop('cuentatransferencia__persona_cuenta__rfc'),
            "tipoCuentaBeneficiario": kwargs.pop('t_ctaBeneficiario'),
            "tipoCuentaOrdenante": kwargs.pop('t_ctaEmisor'),
            "tipoPago": "1",
            "firma": None
        }


# (ChrGil 2022-01-16) Clase que permite renderizar el JSON de STP, para el ambiente de produccion
# (ChrGil 2022-01-16) masivas
class RenderJSONRegistraOrdenProduction:
    render_json_stp: ClassVar[Dict[str, str]]

    def __init__(self, **kwargs):
        self.render_json_stp = self._render_json_stp(**kwargs)

    @staticmethod
    def _render_json_stp(**kwargs):
        return {
            "claveRastreo": kwargs.get('clave_rastreo'),
            "conceptoPago": kwargs.get('concepto_pago'),
            "cuentaBeneficiario": kwargs.get('cta_beneficiario'),
            "cuentaOrdenante": kwargs.get('cuenta_emisor'),
            "empresa": kwargs.get('empresa'),
            "institucionContraparte": kwargs.get('receiving_bank__participante', "90646"),
            "institucionOperante": "90646",
            "monto": f"{kwargs.get('monto'):.2f}",
            "nombreBeneficiario": kwargs.get('nombre_beneficiario'),
            "nombreOrdenante": kwargs.get('nombre_emisor'),
            "referenciaNumerica": kwargs.get('referencia_numerica'),
            "rfcCurpBeneficiario": kwargs.get('rfc_curp_beneficiario'),
            "rfcCurpOrdenante": kwargs.get('rfc_curp_emisor'),
            "tipoCuentaBeneficiario": kwargs.get('t_ctaBeneficiario'),
            "tipoCuentaOrdenante": kwargs.get('t_ctaEmisor'),
            "tipoPago": "1",
            "firma": None
        }


# (ChrGil 2022-01-16) Clase que permite renderizar el JSON de STP, para consultar
# (ChrGil 2022-01-16) el saldo de una cuenta
class RenderJSONConsultaSaldoCuenta:
    render_json_stp: ClassVar[Dict[str, str]]

    def __init__(self, **kwargs):
        self.render_json_stp = self._render_json_stp(**kwargs)
        if self.render_json_stp.get('fecha') is None:
            self.render_json_stp.pop('fecha')

    @staticmethod
    def _render_json_stp(**kwargs):
        return {
            "cuentaOrdenante": kwargs.get('cuenta_ordenante'),
            "empresa": kwargs.get('empresa'),
            "fecha": kwargs.get('fecha', None),
            "firma": None
        }


# (ChrGil 2022-01-16) Realiza una transacción por spei con el cobro de la comisión
class RenderJSONRegistraOrdenProductionComission:
    render_json_stp: ClassVar[Dict[str, str]]

    def __init__(self, transaction: transferencia):
        self.render_json_stp = self._render_json_stp(transaction)

    @staticmethod
    def _render_json_stp(transaction: transferencia):
        return {
            "claveRastreo": transaction.clave_rastreo,
            "conceptoPago": transaction.concepto_pago,
            "cuentaBeneficiario": transaction.cta_beneficiario,
            "cuentaOrdenante": transaction.cuenta_emisor,
            "empresa": transaction.empresa,
            "institucionContraparte": "90646",
            "institucionOperante": "90646",
            "monto": f"{transaction.monto:.2f}",
            "nombreBeneficiario": transaction.nombre_beneficiario.strip(),
            "nombreOrdenante": transaction.nombre_emisor.strip(),
            "referenciaNumerica": transaction.referencia_numerica,
            "rfcCurpBeneficiario": transaction.rfc_curp_beneficiario,
            "rfcCurpOrdenante": transaction.rfc_curp_emisor,
            "tipoCuentaBeneficiario": transaction.t_ctaBeneficiario,
            "tipoCuentaOrdenante": transaction.t_ctaEmisor,
            "tipoPago": "1",
            "firma": None
        }
