from typing import Dict, List, NoReturn, Any, ClassVar

from MANAGEMENT.AlgSTP.GenerarFirmaSTP import GeneraFirma, SignatureCertSTP, GetPriKeyPordSTP, GetPriKey, \
    DataSTPConsultaSaldoCuenta, RegistraOrdenDataSTP
from apps.api_stp.interface import BuildObjectJSONStp, EmisorTransaction
from apps.api_stp.render_json import RenderJSONRegistraOrdenTest, RenderJSONRegistraOrdenProduction, \
    RenderJSONConsultaSaldoCuenta, RenderJSONRegistraOrdenProductionComission

# (ChrGil 2022-01-16) Clase que permite renderizar el JSON de STP, para el ambiente de pruebas
# (ChrGil 2022-01-16) ademas agrega la firma STP a cada objeto JSON, para el ambiente de pruebas
# (ChrGil 2022-01-16) La información hardcodeada es porque STP lo solicita asi en pruebas
from apps.transaction.models import transferencia
from apps.users.models import cuenta


class SignatureTestAPIStpIndividual(BuildObjectJSONStp):
    _render: ClassVar[RenderJSONRegistraOrdenTest] = RenderJSONRegistraOrdenTest
    _list_json_data_stp: List[Dict[str, Any]]
    json_data_registra_orden: Dict[str, Any]

    def __init__(self, transaction_data: EmisorTransaction):
        self._transaction_data = transaction_data.info_transaction_stp
        self._add_stp_signature()

    def _add_stp_signature(self) -> NoReturn:
        new_json_data = self._render(**self._transaction_data).render_json_stp
        sing_text_plain = self._generate_sing(self._default_data_stp, new_json_data)
        sing_encr = self._sing_firma_stp(self._private_key, sing_text_plain.cadena_original)
        new_json_data.update({"firma": sing_encr.signature()})
        self.json_data_registra_orden = new_json_data


class SignatureTestAPIStpIndividualJSON(BuildObjectJSONStp):
    _render: ClassVar[RenderJSONRegistraOrdenTest] = RenderJSONRegistraOrdenTest
    _list_json_data_stp: List[Dict[str, Any]]
    json_data_registra_orden: Dict[str, Any]

    def __init__(self, transaction_data: Dict[str, Any]):
        self._transaction_data = transaction_data
        print(transaction_data)
        self._add_stp_signature()

    def _add_stp_signature(self) -> NoReturn:
        new_json_data = self._render(**self._transaction_data).render_json_stp
        sing_text_plain = self._generate_sing(self._default_data_stp, new_json_data)
        sing_encr = self._sing_firma_stp(self._private_key, sing_text_plain.cadena_original)
        new_json_data.update({"firma": sing_encr.signature()})
        self.json_data_registra_orden = new_json_data


# (ChrGil 2022-01-16) Renderiza el JSON data que se le envia a STP, para las transacciones masivas
# (ChrGil 2022-01-16) Ambiente de pruebas
class SignatureMassiveTestAPIStp(BuildObjectJSONStp):
    _render: ClassVar[RenderJSONRegistraOrdenTest] = RenderJSONRegistraOrdenTest
    _list_json_data_stp: List[Dict[str, Any]]
    json_data_registra_orden: List[Dict[str, Any]]

    def __init__(self, transaction_data: List[Dict[str, Any]]):
        self._list_transaction_data = transaction_data
        self._list_json_data_stp = []
        self._json_data_stp = []
        self._add_stp_signature()

    def _add_stp_signature(self):
        for data in self._list_transaction_data:
            new_json_data = self._render(**data).render_json_stp
            sing_text_plain = self._generate_sing(self._default_data_stp, new_json_data)
            sing_encr = self._sing_firma_stp(self._private_key, sing_text_plain.cadena_original)
            new_json_data.update({"firma": sing_encr.signature()})
            self._list_json_data_stp.append(new_json_data)

        self.json_data_registra_orden = self._list_json_data_stp


# (ChrGil 2022-01-16) Clase que permite renderizar el JSON de STP, para el ambiente de produccion
# (ChrGil 2022-01-16) ademas agrega la firma STP a cada objeto JSON, para el ambiente de produccion
class SignatureProductionAPIStp(BuildObjectJSONStp):
    _render: ClassVar[RenderJSONRegistraOrdenProduction] = RenderJSONRegistraOrdenProduction
    _list_json_data_stp: List[Dict[str, Any]]
    json_data_registra_orden: List[Dict[str, Any]]

    def __init__(self, transaction_data: List[Dict[str, Any]]):
        self._list_transaction_data = transaction_data
        self._list_json_data_stp = []
        self._json_data_stp = []
        self._add_stp_signature()

    def _add_stp_signature(self):
        for data in self._list_transaction_data:
            new_json_data = self._render(**data).render_json_stp
            sing_text_plain = self._generate_sing(self._default_data_stp, new_json_data)
            sing_encr = self._sing_firma_stp(self._private_key, sing_text_plain.cadena_original)
            new_json_data.update({"firma": sing_encr.signature()})
            self._list_json_data_stp.append(new_json_data)

        self.json_data_registra_orden = self._list_json_data_stp


# (ChrGil 2022-01-16) Clase que permite renderizar el JSON de STP, para el ambiente de produccion
# (ChrGil 2022-01-16) ademas agrega la firma STP a cada objeto JSON, para el ambiente de produccion
class SignatureProductionAPIStpIndividual(BuildObjectJSONStp):
    _private_key: ClassVar[GetPriKeyPordSTP] = GetPriKeyPordSTP()
    _sing_firma_stp: ClassVar[SignatureCertSTP] = SignatureCertSTP
    _render: ClassVar[RenderJSONRegistraOrdenProduction] = RenderJSONRegistraOrdenProduction
    _list_json_data_stp: List[Dict[str, Any]]
    json_data_registra_orden: Dict[str, Any]

    def __init__(self, transaction_data: Dict[str, Any]):
        self._transaction_data = transaction_data
        self._add_stp_signature()

    @property
    def _render_data_stp(self) -> Dict[str, Any]:
        return self._render(**self._transaction_data).render_json_stp

    @property
    def _stp_signature(self) -> bytes:
        return self._generate_sing(self._default_data_stp, self._render_data_stp).cadena_original

    @property
    def _encryp(self) -> str:
        return self._sing_firma_stp(self._private_key, self._stp_signature).signature()

    def _add_stp_signature(self) -> NoReturn:
        json = self._render_data_stp
        json.update({"firma": self._encryp})
        self.json_data_registra_orden = json


# (ChrGil 2022-01-16) Clase que permite renderizar el JSON de STP, para el ambiente de pruebas
# (ChrGil 2022-01-16) ademas agrega la firma STP a cada objeto JSON, para el ambiente de pruebas
class SignatureTesterAPIStpIndividual(BuildObjectJSONStp):
    _private_key: ClassVar[GetPriKeyPordSTP] = GetPriKey()
    _sing_firma_stp: ClassVar[SignatureCertSTP] = SignatureCertSTP
    _render: ClassVar[RenderJSONRegistraOrdenProduction] = RenderJSONRegistraOrdenProduction
    _list_json_data_stp: List[Dict[str, Any]]
    json_data_registra_orden: Dict[str, Any]

    def __init__(self, transaction_data: Dict[str, Any]):
        self._transaction_data = transaction_data
        self._add_stp_signature()

    @property
    def _render_data_stp(self) -> Dict[str, Any]:
        return self._render(**self._transaction_data).render_json_stp

    @property
    def _stp_signature(self) -> bytes:
        return self._generate_sing(self._default_data_stp, self._render_data_stp).cadena_original

    @property
    def _encryp(self) -> str:
        return self._sing_firma_stp(self._private_key, self._stp_signature).signature()

    def _add_stp_signature(self) -> NoReturn:
        json = self._render_data_stp
        json.update({"firma": self._encryp})
        self.json_data_registra_orden = json


# (ChrGil 2022-01-16) Clase que permite renderizar el JSON de STP, para el ambiente de pruebas
# (ChrGil 2022-01-16) ademas agrega la firma STP a cada objeto JSON, para el ambiente de pruebas
class SignatureAPIConsultaSaldoCuenta:
    _private_key: ClassVar[GetPriKeyPordSTP] = GetPriKey()
    _sing_firma_stp: ClassVar[SignatureCertSTP] = SignatureCertSTP
    _render: ClassVar[RenderJSONConsultaSaldoCuenta] = RenderJSONConsultaSaldoCuenta
    _data_stp: ClassVar[DataSTPConsultaSaldoCuenta] = DataSTPConsultaSaldoCuenta()
    _list_json_data_stp: List[Dict[str, Any]]
    _generate_sing: ClassVar[GeneraFirma] = GeneraFirma

    def __init__(self, persona_cuenta: str, empresa: str, fecha: int = None):
        self._cuenta = persona_cuenta
        self._empresa = empresa
        self._fecha = fecha
        self._add_stp_signature()

    @property
    def _render_data_stp(self) -> Dict[str, Any]:
        return self._render(cuenta_ordenante=self._cuenta, empresa=self._empresa, fecha=self._fecha).render_json_stp

    @property
    def _stp_signature(self) -> bytes:
        return self._generate_sing(self._data_stp, self._render_data_stp).cadena_original

    @property
    def _encryp(self) -> str:
        c = b"||BECTELEMATIC|646180171800000002||"
        print(self._stp_signature)
        return self._sing_firma_stp(self._private_key, self._stp_signature).signature()

    def _add_stp_signature(self) -> NoReturn:
        json = self._render_data_stp
        json.update({"firma": self._encryp})
        self.json_data_consulta_pago = json


class SignatureProductionAPIStpIndividualComissionPay(BuildObjectJSONStp):
    _private_key: ClassVar[GetPriKeyPordSTP] = GetPriKeyPordSTP()
    _sing_firma_stp: ClassVar[SignatureCertSTP] = SignatureCertSTP
    _render: ClassVar[RenderJSONRegistraOrdenProductionComission] = RenderJSONRegistraOrdenProductionComission
    _list_json_data_stp: List[Dict[str, Any]]
    json_data_registra_orden: Dict[str, Any]

    def __init__(self, transaction_data: transferencia):
        self._transaction_data = transaction_data
        self._add_stp_signature()

    @property
    def _render_data_stp(self) -> Dict[str, Any]:
        return self._render(self._transaction_data).render_json_stp

    @property
    def _stp_signature(self) -> bytes:
        return self._generate_sing(self._default_data_stp, self._render_data_stp).cadena_original

    @property
    def _encryp(self) -> str:
        return self._sing_firma_stp(self._private_key, self._stp_signature).signature()

    def _add_stp_signature(self) -> NoReturn:
        json = self._render_data_stp
        json.update({"firma": self._encryp})
        self.json_data_registra_orden = json
