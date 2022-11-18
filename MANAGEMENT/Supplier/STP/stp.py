from abc import ABC, abstractmethod
from typing import ClassVar, Dict, Any, Union


class STPCat(ABC):
    @abstractmethod
    def get_value(self, key: str) -> None:
        ...


# (ChrGil 2021-12-16) Catalogo de estado de una dispersión STP
# (ChrGil 2021-12-16) Para mas información visita:
# (ChrGil 2021-12-16) https://stpmex.zendesk.com/hc/es/articles/360040200791-Cat%C3%A1logo-de-Estados-de-Dispersi%C3%B3n
class CatEstadoDispersion(STPCat):
    _data: ClassVar[Dict[str, Any]] = {
        "C": "Capturada",
        "PL": "Pendiente Liberar",
        "L": "Liberada",
        "PA": "Pendiente Autorizar",
        "A": "Autorizada",
        "E": "Enviada",
        "LQ": "Liquidada",
        "XC": "Por Cancelar",
        "CN": "Cancelada",
        "D": "Devuelta",
        "XD": "Por Devolver",
        "CL": "Cancelada Local",
        "CR": "Canc. Rechazada",
        "RL": "Rechazada Local",
        "EA": "Enviada Adapter",
        "CA": "Cancelada Adapter",
        "RA": "Rechazada Adapter",
        "RB": "Rechazada Banxico"
    }

    def get_value(self, key: str) -> str:
        return self._data.get(str(key))


# (ChrGil 2021-12-16) Catalogo de Errores de respuesta al registrar una orden
# (ChrGil 2021-12-16) Para mas información visita:
# (ChrGil 2021-12-16) https://stpmex.zendesk.com/hc/es/articles/360002813311-Cat%C3%A1logo-de-respuesta-RegistraOrden-
class CatErrorsResponseRegistraOrden(STPCat):
    _data: ClassVar[Dict[str, Any]] = {
        "0": "Otros",
        "1": "Dato Obligatorio",
        "2": "Dato No Catalogado",
        "3": "La cuenta No Pertenece a la Empresa",
        "4": "Cuenta invalida",
        "5": "Dato Duplicado",
        "6": "Cuenta No Asociada",
        "7": "Cuenta No Habilitada",
        "8": "Rfc_Curp Inválido",
        "-1": "Clave de rastreo duplicada",
        "-2": "Orden duplicada",
        "-3": "La clave no existe en el catalogo de usuario",
        "-5": "Dato obligatorio {institución contraparte}",
        "-6": "Empresa_Invalida O Institucion_Operante_Invalida",
        "-9": "Institucion_Invalida",
        "-10": "Medio_Entrega_Invalido",
        "-11": "El tipo de cuenta es invalido",
        "-12": "Tipo_Operacion_Invalida",
        "-13": "Tipo_Pago_Invalida",
        "-14": "El usuario es invalido",
        "-16": "Fecha_Operacion_Invalida",
        "-17": "No se pudo determinar un usuario para asociar a la orden",
        "-18": "La institución operante no está asociada al usuario",
        "-20": "Monto_Invalido",
        "-21": "Digito_Verificador_Invalido",
        "-22": "Institucion_No_Coincide_En_Clabe",
        "-23": "Longitud_Clabe_Incorrecta",
        "-26": "Clave de rastreo invalida",
        "-30": "Enlace Financiero en modo consultas",
        "-34": "Valor inválido. Se aceptan caracteres a-z,A-Z,0-9",
        "-200": "Se rechaza por PLD"
    }

    def get_value(self, key: str) -> str:
        return self._data.get(str(key))


# (ChrGil 2021-12-16) Catalogo de estado de trapaso de STP
# (ChrGil 2021-12-16) Para mas información visita:
# (ChrGil 2021-12-16) https://stpmex.zendesk.com/hc/es/articles/360043962952-Cat%C3%A1logo-de-Estados-de-Traspasos
class CatEstadoTraspaso(STPCat):
    _data: ClassVar[Dict[str, Any]] = {
        "TC": "Traspaso Capturado",
        "TL": "Traspaso Liberado",
        "TA": "Traspaso Autorizado",
        "TLQ": "Traspaso Liquidado",
        "TCL": "Traspaso Cancelado"
    }

    def get_value(self, key: str) -> str:
        return self._data.get(str(key))


# (ChrGil 2021-12-16) Catalogo de causas de devolución de STP
# (ChrGil 2021-12-16) Para mas información visita:
# (ChrGil 2021-12-16) https://stpmex.zendesk.com/hc/es/articles/360002797652-Cat%C3%A1logo-de-causas-de-devoluci%C3%B3n
class CatCausasDevolucion(STPCat):
    _data: ClassVar[Dict[str, Any]] = {
        "1": "Cuenta inexistente",
        "2": "Cuenta bloqueada",
        "3": "Cuenta cancelada",
        "5": "Cuenta en otra divisa",
        "6": "Cuenta no pertenece al Participante Receptor",
        "13": "Beneficiario no reconoce el pago",
        "14": "Falta información mandatorio para completar el pago",
        "15": "Tipo de pago erróneo",
        "16": "Tipo de operación errónea",
        "17": "Tipo de cuenta no corresponde",
        "18": "A solicitud del emisor",
        "19": "Carácter inválido",
        "20": "Excede el límite de saldo autorizado de la cuenta",
        "21": "Excede el límite de abonos permitidos en el mes en la cuenta",
        "22": "Número de línea de telefonía móvil no registrado",
        "23": "Cuenta adicional no recibe pagos que no proceden de Banxico",
        "24": "Estructura de la información adicional incorrecta",
        "25": "Falta instrucción para dispersar recursos de clientes por alcanzar límite al saldo",
        "26": "Resolución resultante del Convenio de Colaboración para la Protección del Cliente Emisor",
        "27": "Pago opcional no aceptado por el Participante Receptor",
        "28": "Tipo de pago Codi sin notificación de abono en tiempo reducido",
        "30": "Clave de rastreo repetida por Participante Emisor y día de operación"
    }

    def get_value(self, key: str) -> str:
        return self._data.get(str(key))


# (ChrGil 2021-12-16) Catalogo de estado de cobranza de STP
# (ChrGil 2021-12-16) Para mas información visita:
# (ChrGil 2021-12-16) https://stpmex.zendesk.com/hc/es/articles/360043962492-Cat%C3%A1logo-de-Estados-de-Cobranza
class CatEstadoCobranza(STPCat):
    _data: ClassVar[Dict[str, Any]] = {
        "D": "Devuelta",
        "LQ": "Liquidada",
        "CCE": "Confirmación enviada",
        "CXO": "Por enviar confirma",
        "CCO": "Confirmada",
        "CCR": "Confirmación rech"
    }

    def get_value(self, key: str) -> str:
        return self._data.get(str(key))


# (ChrGil 2021-12-18) Catalogo de Tipo Cuenta
# (ChrGil 2021-12-16) Para mas información visita:
# (ChrGil 2021-12-16) https://stpmex.zendesk.com/hc/es/articles/360002813231-Cat%C3%A1logo-Tipo-Cuenta-
class CatTipoCuenta(STPCat):
    _data: ClassVar[Dict[str, Any]] = {
        "3": "Tarjeta Debito",
        "10": "Telefono Celular",
        "40": "CLABE"
    }

    def get_value(self, key: Union[str, int]) -> str:
        return self._data.get(str(key))


# (ChrGil 2021-12-18) Catalogo de bancos registrados por STP
# (ChrGil 2021-12-18) Para mas información visita:
# (ChrGil 2021-12-18) https://stpmex.zendesk.com/hc/es/articles/360002812851-Cat%C3%A1logo-Instituciones
# (ChrGil 2021-12-18) La Institución 846 GEM - STP es para Ambiente de Pruebas (Desarrollo).
class CatBancos(STPCat):
    _data: ClassVar[Dict[str, Any]] = {
        "2001": "BANXICO",
        "37006": "BANCOMEXT",
        "37009": "BANOBRAS",
        "37019": "BANJERCITO",
        "37135": "NAFIN",
        "37166": "BANSEFI",
        "37168": "HIPOTECARIA FED",
        "40002": "BANAMEX",
        "40012": "BBVA MEXICO",
        "40014": "SANTANDER",
        "40021": "HSBC",
        "40030": "BAJIO",
        "40036": "INBURSA",
        "40042": "MIFEL",
        "40044": "SCOTIABANK",
        "40058": "BANREGIO",
        "40059": "INVEX",
        "40060": "BANSI",
        "40062": "AFIRME",
        "40072": "BANORTE",
        "40106": "BANK OF AMERICA",
        "40108": "MUFG",
        "40110": "JP MORGAN",
        "40112": "BMONEX",
        "40113": "VE POR MAS",
        "40124": "DEUTSCHE",
        "40126": "CREDIT SUISSE",
        "40127": "AZTECA",
        "40128": "AUTOFIN",
        "40129": "BARCLAYS",
        "40130": "COMPARTAMOS",
        "40132": "MULTIVA BANCO",
        "40133": "ACTINVER",
        "40136": "INTERCAM BANCO",
        "40137": "BANCOPPEL",
        "40138": "ABC CAPITAL",
        "40140": "CONSUBANCO",
        "40141": "VOLKSWAGEN",
        "40143": "CIBANCO",
        "40145": "BBASE",
        "40147": "BANKAOOL",
        "40148": "PAGATODO",
        "40150": "INMOBILIARIO",
        "40151": "DONDE",
        "40152": "BANCREA",
        "40154": "BANCO FINTERRA",
        "40155": "ICBC",
        "40156": "SABADELL",
        "40157": "SHINHAN",
        "40158": "MIZUHO BANK",
        "40160": "BANCO S3",
        "90600": "MONEXCB",
        "90601": "GBM",
        "90602": "MASARI",
        "90605": "VALUE",
        "90606": "ESTRUCTURADORES",
        "90608": "VECTOR",
        "90613": "MULTIVA CBOLSA",
        "90616": "FINAMEX",
        "90617": "VALMEX",
        "90620": "PROFUTURO",
        "90630": "CB INTERCAM",
        "90631": "CI BOLSA",
        "90634": "FINCOMUN",
        "90638": "AKALA",
        "90642": "REFORMA",
        "90646": "STP",
        "90648": "EVERCORE",
        "90652": "CREDICAPITAL",
        "90653": "KUSPIT",
        "90656": "UNAGRA",
        "90659": "ASP INTEGRA OPC",
        "90670": "LIBERTAD",
        "90677": "CAJA POP MEXICA",
        "90680": "CRISTOBAL COLON",
        "90683": "CAJA TELEFONIST",
        "90684": "TRANSFER",
        "90685": "FONDO (FIRA)",
        "90686": "INVERCAP",
        "90689": "FOMPED",
        "90902": "INDEVAL",
        "90903": "CoDi Valida",
        "91812": "BBVA BANCOMER2*",
        "91814": "SANTANDER2*",
        "91821": "HSBC2*",
        "91927": "AZTECA2*",
        "91872": "BANORTE2*",
        "90706": "ARCUS",
        "90904": "POLIPAY"
    }

    def get_value(self, key: Union[str, int]) -> str:
        return self._data.get(str(key))


# (ChrGil 2021-12-20) Cambios de estado STP, cuando una transacción tiene el estado pendiente
class CatCambioEstado(STPCat):
    _data: ClassVar[Dict[str, Any]] = {
        "LIQUIDADA": "1",
        "DEVUELTA": "7",
        "CANCELADA": "5",
        "Liquidación": "1",
        "Devolución": "7",
        "Cancelación": "5",
        "Liquidada": "1",
        "Devuelta": "7",
        "Cancelada": "5",
        "Liquidado": "1",
        "Devuelto": "7",
        "Cancelado": "5",
        "LIQUIDADO": "1",
        "DEVUELTO": "7",
        "CANCELADO": "5",
    }

    def get_value(self, key: str) -> str:
        return self._data.get(str(key))


# (ChrGil 2021-12-16) Catalogo de causas de devolución de STP
# (ChrGil 2021-12-16) Para mas información visita:
# (ChrGil 2021-12-16) https://stpmex.zendesk.com/hc/es/articles/360002797652-Cat%C3%A1logo-de-causas-de-devoluci%C3%B3n
class CatErrorRetornaOrden(STPCat):
    _data: ClassVar[Dict[str, Any]] = {
        "0": "Error validando la firma",
        "-1": "Orden no encontrada",
    }

    def get_value(self, key: str) -> str:
        return self._data.get(str(key))
