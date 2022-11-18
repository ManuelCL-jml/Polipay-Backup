import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, ClassVar, List, Union, NoReturn

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives.hashes import SHA256
from base64 import b64encode
from decouple import config

from polipaynewConfig.settings import PUBLIC_KEY_STP_CER, PRIVATE_KEY_STP, PASS_STP_PRIVATE_KEY, \
    PASS_STP_PRIVATE_KEY_PRODUCTION, PRIVATE_KEY_STP_PRODUCTION, PUBLIC_KEY_STP_CER_PRODUCTION, PARAPHRASE


# (ChrGil 2021-12-13) Interfaz de data STP
class DataSTP(ABC):

    @abstractmethod
    def data_obj(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def len_data_obj(self) -> int:
        ...


class BuildSignature(ABC):
    _start: ClassVar[str] = "|"
    _end: ClassVar[str] = "||"

    @abstractmethod
    def _build_signature(self) -> NoReturn:
        ...

    @abstractmethod
    def _genera_cadena_original(self, list_char) -> bytes:
        ...


class Keys(ABC):
    _location_file: ClassVar[Union[str, None]] = None
    _signature: ClassVar[Union[bytes, None]] = None

    @abstractmethod
    def get_key(self):
        ...


# (ChrGil 2021-12-13) Información proveeida por la API STP
class RegistraOrdenDataSTP(DataSTP):
    def data_obj(self) -> Dict[str, Any]:
        return {
            "institucionContraparte": "Institución contraparte",
            "empresa": "Empresa",
            "fechaOperacion": "Fecha de operación",
            "folioOrigen": "Folio origen",
            "claveRastreo": "Clave de rastreo",
            "institucionOperante": "Institución operante",
            "monto": "Monto del pago",
            "tipoPago": "Tipo del pago",
            "tipoCuentaOrdenante": "Tipo de la cuenta del ordenante",
            "nombreOrdenante": "Nombre del ordenante",
            "cuentaOrdenante": "Cuenta del ordenante",
            "rfcCurpOrdenante": "RFC / Curp del ordenante",
            "tipoCuentaBeneficiario": "Tipo de cuenta del beneficiario",
            "nombreBeneficiario": "Nombre del beneficiario",
            "cuentaBeneficiario": "Cuenta del beneficiario",
            "rfcCurpBeneficiario": "RFC / Curp del beneficiario",
            "emailBeneficiario": "Email del beneficiario",
            "tipoCuentaBeneficiario2": "Tipo de cuenta del beneficiario 2",
            "nombreBeneficiario2": "Nombre del beneficiario 2",
            "cuentaBeneficiario2": "Cuenta del beneficiario 2",
            "rfcCurpBeneficiario2": "RFC / Curp del beneficiario 2",
            "conceptoPago": "Concepto del pago",
            "conceptoPago2": "Concepto del pago 2",
            "claveCatUsuario1": "Clave del catálogo de usuario 1",
            "claveCatUsuario2": "Clave del catálogo de usuario 2",
            "clavePago": "Clave del pago",
            "referenciaCobranza": "Referencia de cobranza",
            "referenciaNumerica": "Referencia numérica",
            "tipoOperacion": "Tipo de operación",
            "topologia": "Topología",
            "usuario": "Usuario",
            "medioEntrega": "Medio de entrega",
            "prioridad": "Prioridad",
            "iva": "IVA"
        }

    def len_data_obj(self) -> int:
        return len(self.data_obj().keys())


# (ChrGil 2022-03-14) Información proveeida por la API STP
class RetornaOrdenDataSTP(DataSTP):
    def data_obj(self) -> Dict[str, Any]:
        return {
            "fechaOperacion": "Fecha que se realiza la devolución",
            "institucionOperante": "Banco emisor",
            "claveRastreo": "clave rastro del movimiento",
            "monto": "monto a devolver",
            "empresa": "Nombre de la empresa que envía las operaciones y que estáconfigurada en “Enlace Financiero”.",
            "digitoIdentificadorBeneficiario": "id del beneficiario, tercero a tercero",
            "claveRastreoDevolucion": "Folio origen",
            "medioEntrega": "Por defecto sería el medio de entrega 3",
        }

    def len_data_obj(self) -> int:
        return len(self.data_obj().keys())


# (ChrGil 2022-03-14) Consulta Saldo cuenta
class DataSTPConsultaSaldoCuenta(DataSTP):
    def data_obj(self) -> Dict[str, Any]:
        return {
            "empresa": "Alias de la empresa registrado dentro de Enlace Financiero.",
            "cuentaOrdenante": "Cuenta de la cual se desea consultar el saldo.",
            "fecha": "Fecha actual o histórico (AAAAMMDD).",
        }

    def len_data_obj(self) -> int:
        return len(self.data_obj().keys())


class GeneraFirma(BuildSignature):
    cadena_original: ClassVar[bytes] = b''

    def __init__(self, data_stp: DataSTP, my_data: Dict[str, Any]):
        self._data_stp = data_stp
        self._my_data = my_data
        self._build_signature()

    def _build_signature(self) -> NoReturn:
        joined_fields: List[str] = []
        length_data_stp: int = self._data_stp.len_data_obj()
        index: int = 0

        # (ChrGil 2021-12-10) Se recorren las claves de la data de STP
        for key in self._data_stp.data_obj().keys():
            index += 1

            if len(joined_fields) == 0:
                joined_fields.append(self._start)

            # (ChrGil 2021-12-10) Si existe regresa el "value", si no regresa "None"
            value = self._my_data.get(key)
            if value:
                joined_fields.append(f'|{value}')

            if value is None:
                joined_fields.append('|')

            if index == length_data_stp:
                joined_fields.append(self._end)

        self.cadena_original = self._genera_cadena_original(joined_fields)

    def _genera_cadena_original(self, list_char: List[str]) -> bytes:
        cadena_original = "".join(list_char)
        return cadena_original.encode('utf-8')


# # (ChrGil 2021-12-15) Obtiene clave privada
# @dataclass
# class GetPriKey(Keys):
#     def get_key(self) -> RSAPrivateKey:
#         with open(file=PRIVATE_KEY_STP, mode="rb") as key_file:
#             private_key = serialization.load_pem_private_key(
#                 key_file.read(), password=PASS_STP_PRIVATE_KEY)
#             return private_key

# (ChrGil 2021-12-15) Obtiene clave privada STP pruebas
@dataclass
class GetPriKey(Keys):
    def get_key(self) -> RSAPrivateKey:
        with open(file=PRIVATE_KEY_STP, mode="rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(), password=PASS_STP_PRIVATE_KEY)
            return private_key


# (ChrGil 2021-12-15) Obtiene clave publica (Certificado) STP pruebas
@dataclass
class GetPubKey(Keys):
    def get_key(self) -> RSAPublicKey:
        with open(file=PUBLIC_KEY_STP_CER, mode="rb") as key_file:
            cert = x509.load_pem_x509_certificate(key_file.read())
            return cert.public_key()


@dataclass
class SignatureCertSTP:
    _key: ClassVar[Keys]
    _firma_stp: ClassVar[bytes]

    def __init__(self, key: Keys, firma_stp: bytes):
        self._key = key
        self._firma_stp = firma_stp

    def signature(self) -> str:
        signature = self._key.get_key().sign(
            self._firma_stp,
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        return b64encode(signature).decode('utf-8')


class EncryptionSingSTP:
    def __init__(self, key: Keys, sing_stp: str):
        self._public_key = key
        self._sing_stp = sing_stp.encode('utf-8')

    # (ChrGil 2021-12-15) Encripta la firma de STP
    def encryption(self) -> str:
        ciphertext = self._public_key.get_key().encrypt(
            self._sing_stp,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return b64encode(ciphertext).decode('utf-8')


class DecryptionSingSTP:
    _b64decode_ciphertext: ClassVar[bytes]

    def __init__(self, key: Keys, ciphertext: str):
        self._private_key = key
        self._ciphertext = ciphertext
        self._b64decode_ciphertext = base64.b64decode(self._ciphertext)

    # (ChrGil 2021-12-15) Descifra un texto cifrado, con la llave privada
    def decryption(self) -> str:
        plaintext = self._private_key.get_key().decrypt(
            self._b64decode_ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=SHA256()),
                algorithm=SHA256(),
                label=None
            )
        )

        return plaintext.decode('utf-8')


# (ChrGil 2021-12-15) Obtiene clave privada STP Producción
@dataclass
class GetPriKeyPordSTP(Keys):
    def get_key(self) -> RSAPrivateKey:
        with open(file=PRIVATE_KEY_STP_PRODUCTION, mode="rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(), password=PARAPHRASE)
            return private_key


# (ChrGil 2021-12-15) Obtiene clave publica (Certificado) STP Producción
@dataclass
class GetPubKeyProdSTP(Keys):
    def get_key(self) -> RSAPublicKey:
        with open(file=PUBLIC_KEY_STP_CER_PRODUCTION, mode="rb") as key_file:
            cert = x509.load_pem_x509_certificate(key_file.read())
            return cert.public_key()
