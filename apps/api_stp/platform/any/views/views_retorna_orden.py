import datetime as dt
from typing import Any, Dict, ClassVar

from MANAGEMENT.AlgSTP.GenerarFirmaSTP import RetornaOrdenDataSTP, GeneraFirma
from MANAGEMENT.Utils.utils import generate_clave_rastreo_with_uuid
from apps.transaction.models import transferencia

# d = {
#     "fechaOperacion": 20220311,
#     "institucionOperante": 90646,
#     "claveRastreo": "POD30331984906BDCA57DB7928A96D",
#     "claveRastreoDevolucion": "PO55A164C6444EB0E9F02A696C1B62",
#     "empresa": "BECPOLIMENTES",
#     "monto": 0.01,
#     "digitoIdentificadorBeneficiario": "2",
#     "medioEntrega": "3",
#     "firma": "PWY95qKqRcV5ohLgfaZNCDT75/Ygo7Fm9X1ygl6W+g4bxz3cbnQvzRYBo6sh4TtlUU31vfY1d8rOtXMlXHZYsLvNaHySVPmWqx+VeqLbRxdO0Vub5fMo3Jnh3qRrHNKJ2c1oBgVhiFns84lwB/wXExBFr9DI+bur4I389efnltwvZP5foX/vV/lACJxqi5HwBQMf4+TnDzJabPWBdlL3HIAnbiLMQSC3jZwkhsXXg1ICk7qb8rtTd6RniEEO9JdxmnHiquni1XpOhArUp5C09oVjmmBEiVA6qitPfJ1q/8qjQHZ11Z1XLdxEPJUV8ij6E6IR00wItqpoVRgZ/KhLSA=="
# }


class TransaccionRetornada:
    def __init__(self, transaction_id: int):
        self._transaction_id = transaction_id

    @property
    def _get_data_transaccion(self) -> Dict[str, Any]:
        return transferencia.objects.select_related().filter(id=self._transaction_id).values(
            'id',
            'clave_rastreo',
            'empresa',
            'monto',
            'transmitter_bank__participante'
        ).first()


class RetornaOrden:
    payload: ClassVar[Dict[str, Any]]

    def __init__(self, **kwargs):
        self._institucion_operante = kwargs.get('institucion_operante')
        self._clave_rastreo = kwargs.get('clave_rastreo')
        self._empresa = kwargs.get('empresa')
        self._monto = kwargs.get('monto')
        self.payload = self._payload

    @staticmethod
    def _fecha_operacion() -> str:
        return dt.datetime.strftime(dt.datetime.now(), fmt='%Y%m%d')

    @staticmethod
    def _clave_rastreo_devolucion() -> str:
        return generate_clave_rastreo_with_uuid()

    @property
    def _payload(self) -> Dict[str, Any]:
        return {
            "fechaOperacion": self._fecha_operacion(),
            "institucionOperante": self._institucion_operante,
            "claveRastreo": self._clave_rastreo,
            "claveRastreoDevolucion": self._clave_rastreo_devolucion(),
            "empresa": self._empresa,
            "monto": round(self._monto, 2),
            "digitoIdentificadorBeneficiario": "2",
            "medioEntrega": "3",
            "firma": None
        }


class GenerarFirmaRetornaOrdenSTP:
    _firma: ClassVar[GeneraFirma] = GeneraFirma
    _data_stp: ClassVar[RetornaOrdenDataSTP] = RetornaOrdenDataSTP()

    def __init__(self, orden: RetornaOrden):
        self._orden = orden

    @property
    def _generate_sing(self):
        return self._firma(self._data_stp, self._orden.payload)

    def add_sing(self):
        self._orden.payload.update({'firma': self._generate_sing})
