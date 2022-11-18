from typing import Dict, Any, NoReturn, ClassVar

from apps.api_stp.client import CosumeAPISTP
from apps.api_stp.signature import SignatureProductionAPIStpIndividual
from apps.transaction.models import transferencia


class SetFolioOpetacionSTP:
    def __init__(self, response: Dict[str, Any], clave_rastreo: str):
        self._response = response
        self._clave_rastreo = clave_rastreo
        self._set_folio()

    @property
    def _get_folio(self) -> int:
        return self._response.get('resultado').get('id')

    def _set_folio(self) -> NoReturn:
        transferencia.filter_transaction.update_folio_operacion(self._clave_rastreo, self._get_folio)

# class ComponenCosumeAPIStpRegistraOrden:
#     _sing: ClassVar[SignatureProductionAPIStpIndividual] = SignatureProductionAPIStpIndividual
#     _folio_operacion: ClassVar[SetFolioOpetacionSTP] = SetFolioOpetacionSTP
#     _api: ClassVar[CosumeAPISTP] = CosumeAPISTP
#
#     def __init__(self, transaction_info: Dict[str, Any], demo_bool: bool):
#         self._transaction = transaction_info
#         self._demo_bool = demo_bool
#         self._registra_orden()
#
#     def _sing_json(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
#         return self._sing(transaction).json_data_registra_orden
#
#     def _registra_orden(self) -> NoReturn:
#         data = self._sing_json(self._transaction)
#         api = self._api(data, demo_bool=self._demo_bool)
#         self._folio_operacion(api.response, data.get('claveRastreo'))
#
#
# class ComponentTransactionInfo:
#     def __init__(self, transaction_id: int):
#         self.transaction_info = self._get_info_transaction(transaction_id)
#
#     @staticmethod
#     def _get_info_transaction(transaction_id: int) -> Dict[str, Any]:
#         return transferencia.objects.select_related(
#             'masivo_trans',
#             'transmitter_bank',
#             'receiving_bank'
#         ).filter(
#             id=transaction_id
#         ).values(
#             'id',
#             'clave_rastreo',
#             'concepto_pago',
#             'cta_beneficiario',
#             'cuenta_emisor',
#             'empresa',
#             'monto',
#             'nombre_beneficiario',
#             'nombre_emisor',
#             'referencia_numerica',
#             'rfc_curp_beneficiario',
#             't_ctaBeneficiario',
#             't_ctaEmisor',
#             'rfc_curp_emisor',
#             'tipo_pago',
#             'cuentatransferencia__persona_cuenta__rfc'
#         ).first()
