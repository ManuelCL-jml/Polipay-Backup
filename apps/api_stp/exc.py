import re
from typing import Dict, NoReturn, Any

from pydantic import PydanticValueError
from MANAGEMENT.Supplier.STP.stp import CatErrorsResponseRegistraOrden, CatErrorRetornaOrden


# (ChrGil 2021-12-28) Manejo de errores de STP
# (ChrGil 2021-12-28) Codigo extraido de cuenca-mx. Todos los creditos para cuenca-mx
# (ChrGil 2021-12-28) https://github.com/cuenca-mx/stpmex-python/blob/main/stpmex/client.py
# class StpmexException(Exception):
#     def __init__(self, **kwargs):
#         for attr, value in kwargs.items():
#             setattr(self, attr, value)
#
#     def __repr__(self):
#         return (
#                 self.__class__.__name__
#                 + '('
#                 + ', '.join(
#             [
#                 f'{attr}={repr(value)}'
#                 for attr, value in self.__dict__.items()
#             ]
#         )
#                 + ')'
#         )
#
#     def __str__(self):
#         return repr(self)


# (ChrGil 2021-12-29) Mi Exception
class StpmexException(Exception):
    def __init__(self, msg: str, desc: str):
        self.msg = msg
        self.desc = desc


class InvalidPassphrase(StpmexException):
    """El passphrase es incorrecto"""


class CompanyNotValid(StpmexException):
    """El passphrase es incorrecto"""


class InvalidAccountType(StpmexException):
    """Tipo de cuenta inválida"""


class SignatureValidationError(StpmexException):
    """Error validando la firma"""


class DuplicateOrder(StpmexException):
    """Orden Duplicada"""


class InvalidRfcOrCurp(StpmexException):
    """RFC o CURP inválido"""


class ClaveRastreoAlreadyInUse(StpmexException):
    """La clave de rastreo es repetida"""


class PldRejected(StpmexException):
    """'Orden sin cuenta ordenante. Se rechaza por PLD"""


class NoServiceResponse(StpmexException):
    """No se recibió respuesta del servicio"""


class NoOrdenesEncontradas(StpmexException):
    """No se encontraron ordenes"""


class InvalidTrackingKey(StpmexException):
    """Clave de rastreeo inválida"""


class BankCodeClabeMismatch(StpmexException):
    """La cuenta clabe no coincide para la institución operante"""


class SameAccount(StpmexException):
    """Transferencia a la misma cuenta"""


class DuplicatedAccount(StpmexException):
    """Cuenta duplicada"""


class InvalidField(StpmexException):
    """Campo inválido"""


class MandatoryField(StpmexException):
    """El campo X es obligatorio"""


class InvalidInstitution(StpmexException):
    """La Institucion no es valida"""


class AccountDoesNotExist(StpmexException):
    """La cuenta no existe"""


class InvalidAmount(StpmexException):
    """El monto es inválido para una de las instituciones"""


class ErrorValidatingSignature(StpmexException):
    """Si el servicio retorna, error validando la firma"""


class OrdenNotFound(StpmexException):
    """Si la orden no existe"""


class BlockedInstitutionError(PydanticValueError):
    """Institución bloqueada"""

    code = 'clabe.bank_code'
    msg_template = '{bank_name} has been blocked by STP.'


# (ChrGil 2021-12-28) Manejo de errores de STP
# (ChrGil 2021-12-28) Codigo extraido de cuenta-mx. Todos los creditos para cuenta-mx
# (ChrGil 2021-12-28) https://github.com/cuenca-mx/stpmex-python/blob/main/stpmex/client.py
def _raise_description_error_exc(resp: Dict) -> NoReturn:
    class_error: CatErrorsResponseRegistraOrden = CatErrorsResponseRegistraOrden()
    result_id = str(resp['resultado']['id'])
    error: str = resp['resultado']['descripcionError']

    if result_id == "0":
        raise NoServiceResponse(class_error.get_value(result_id), error)

    elif result_id == "-1":
        raise ClaveRastreoAlreadyInUse(class_error.get_value(result_id), error)

    elif result_id == "-2":
        raise DuplicateOrder(class_error.get_value(result_id), error)

    elif result_id == "-6":
        raise CompanyNotValid(class_error.get_value(result_id), error)

    elif result_id == "-7":
        raise AccountDoesNotExist(class_error.get_value(result_id), error)

    elif result_id == "-9":
        raise InvalidInstitution(class_error.get_value(result_id), error)

    elif result_id == "-11":
        raise InvalidAccountType(class_error.get_value(result_id), error)

    elif result_id == "-20":
        raise InvalidAmount(class_error.get_value(result_id), error)

    elif result_id == "-22":
        raise BankCodeClabeMismatch(class_error.get_value(result_id), error)

    elif result_id == "-24":
        raise SameAccount(class_error.get_value(result_id), error)

    elif result_id == "-34":
        raise InvalidTrackingKey(class_error.get_value(result_id), error)

    elif result_id == "-100":
        raise NoOrdenesEncontradas(class_error.get_value(result_id), error)

    elif result_id == "-200":
        raise PldRejected(class_error.get_value(result_id), error)

    else:
        raise MandatoryField(result_id, error)


# (ChrGil 2021-12-28) Manejo de errores de STP
# (ChrGil 2021-12-28) Codigo extraido de cuenca-mx. Todos los creditos para cuenca-mx
# (ChrGil 2021-12-28) https://github.com/cuenca-mx/stpmex-python/blob/main/stpmex/client.py
def _raise_description_exc(resp: Dict) -> NoReturn:
    cat_errors: CatErrorsResponseRegistraOrden = CatErrorsResponseRegistraOrden()
    result_id: str = str(resp['id'])
    desc = resp['descripcion']

    if result_id == 0 and 'Cuenta en revisión' in desc:
        # STP regresa esta respuesta cuando se registra
        # una cuenta. No se levanta excepción porque
        # todas las cuentas pasan por este status.
        ...

    elif id == "1":
        raise InvalidField(cat_errors.get_value(result_id), desc)

    elif id == "3":
        raise DuplicatedAccount(cat_errors.get_value(result_id), desc)

    elif id == "5":
        raise MandatoryField(cat_errors.get_value(result_id), desc)

    else:
        raise StpmexException(cat_errors.get_value(result_id), desc)


# (ChrGil 2022-01-13) Excepciones personalizadas, para el endpoint CobranzaSTP
class CobranzaAbonoSTPException(Exception):
    def __init__(self, message: str):
        self.message = message


class CuentaNoExiste(CobranzaAbonoSTPException):
    """Si la cuenta clabe no existe"""


class BeneficiarioNoExiste(CobranzaAbonoSTPException):
    """Si el beneficiario no existe"""


# (ChrGil 2021-12-28) Manejo de errores de STP
# (ChrGil 2021-12-28) Codigo extraido de cuenta-mx. Todos los creditos para cuenta-mx
# (ChrGil 2021-12-28) https://github.com/cuenca-mx/stpmex-python/blob/main/stpmex/client.py
def _raise_description_error_exc_retorna_orden(resp: Dict) -> NoReturn:
    class_error: CatErrorRetornaOrden = CatErrorRetornaOrden()
    result_id = str(resp['estado'])
    error: str = resp['mensaje']

    if result_id == "1":
        raise ErrorValidatingSignature(class_error.get_value(result_id), error)
