# (ChrGil 2021-12-29) Mi Exception
from typing import Any


class AdelanteZapopanException(Exception):
    def __init__(self, msg: str):
        self.msg = msg


class ErrorLongitudCuenta(AdelanteZapopanException):
    """Si la longitud de la cuenta con coincide"""


class ClabeNoExiste(AdelanteZapopanException):
    """Si en el diccionario no existen las cuentas"""


class CardAlreadyExists(AdelanteZapopanException):
    """Si la terjeta ya existe en la base de datos de Polipay"""


class AccountAlreadyExists(AdelanteZapopanException):
    """Si la cuenta ya existe en la base de datos de Polipay"""


class APIInntecException(Exception):
    def __init__(self, msg: Any, detail: Any = None):
        self.msg = msg
        self.detail = detail


class CardNotFound(APIInntecException):
    """La tarjeta no existe en la base de datos de Polipay"""


class FailAssignedCard(APIInntecException):
    """La tarjeta no se pudo asigar"""


class ErrorValidationInntec(APIInntecException):
    """Si inntec regresa un error de validación"""


# (ChrGil 2022-01-25) Excepciones Dispersiones
class DispersionesException(Exception):
    def __init__(self, message: str):
        self.message = message


class RazonSocialDoesNotExist(DispersionesException):
    """Si la razón social ya sea cuenta eje o centro costos no existe"""


class AccountDoesNotExist(DispersionesException):
    """Si la cuenta no existe o no esta activa"""


class GroupNameNotProvided(DispersionesException):
    """Si el cliente realiza una masiva pero no envia el nombre del grupo"""


# (ChrGil 2022-02-02) Excepciones para el envio de parametros de url en los listados
class ParamsRaiseException(Exception):
    def __init__(self, message: str):
        self.message = message


class ParamsNotProvided(ParamsRaiseException):
    """Si el cliente no envia parametros obligatorios"""


class ParamStatusNotProvided(ParamsRaiseException):
    """Si el cliente no evia el parametro status"""


# (ChrGil 2022-02-02) Excepcones personalizadas para validar centro de costos
class CostCenterException(Exception):
    def __init__(self, message):
        self.message = message


class CostCenterIsNotActivate(CostCenterException):
    """Si el centro de costos no está activo o fue dado de baja"""


class CostCenterStatusAccount(CostCenterException):
    """Si la cuenta del centro de costos no está activa"""


class InsufficientBalance(CostCenterException):
    """Si el monto es menor o igual a cero del centro de costos"""


class TransactionException(Exception):
    def __init__(self, message: str):
        self.message = message


class TransactionDoestNotExists(TransactionException):
    """Si no existe la transacción"""


class CouldNotChangeState(TransactionException):
    """Si quiere cambiar el estado por segunda vez"""
