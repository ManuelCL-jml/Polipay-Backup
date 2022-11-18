# (ChrGil 2021-12-29) Mi Exception
from typing import Dict, NoReturn, Any

from requests import Response


class PayCashException(Exception):
    def __init__(self, msg: str, code: str):
        self.msg = msg
        self.code = code


class TokenErrorAccess(PayCashException):
    """El acceso para generar el token es invalido."""


class ExistPayConfirm(PayCashException):
    """existe un pago confirmado, no se puede cancelar"""


class OperationNotExist(PayCashException):
    """la operacion no existe."""


class OperationHasBeenPreviouslyCanceled(PayCashException):
    """la operacion ha sido previamente cancelada."""


class SearchErrorMexico(PayCashException):
    """El acceso para generar el token es invalido."""


class InvalidIssuer(PayCashException):
    """El emisor indicado no es valido."""


class ReferenceError(PayCashException):
    """Error en tipo de referencia, por favor verifique datos."""


class FailedGenerateReference(PayCashException):
    """	Error. No es posible generar la referencia."""


class InvalidAmount(PayCashException):
    """Monto invalido, monto superior al maximo configurado."""


class InvalidOperation(PayCashException):
    """Operacion invalida o previamente cancelada."""


class MaximumTimeExpired(PayCashException):
    """Tiempo maximo para reverso ha expirado."""


class OperationDoesNotExist(PayCashException):
    """La operacion no existe."""


class ErrorServicePayCash(PayCashException):
    """Error Service."""


class ErrorReferenceLatam(PayCashException):
    """Error regresado por paycash latam"""


class ErrorSearchLatam(PayCashException):
    """Error regresado por paycash latam"""


class ErrorCancelLatam(PayCashException):
    """Error regresado por paycash latam"""


class UnknownError(PayCashException):
    """Si Paychas regresa un error no catalogado"""


class TokenExpired(PayCashException):
    """El token de paycash ha expirado"""


def _raise_error_response(data: Dict) -> bool:
    error_code = data.get("ErrorCode")
    messsage = data.get("ErrorMessage")

    if error_code == "0":
        return True

    elif error_code == "111":
        raise TokenErrorAccess(msg=messsage, code=error_code)

    elif error_code == "51":
        raise ExistPayConfirm(msg=messsage, code=error_code)

    elif error_code == "61":
        raise OperationNotExist(msg=messsage, code=error_code)

    elif error_code == "71":
        raise OperationHasBeenPreviouslyCanceled(msg=messsage, code=error_code)

    elif error_code == "102":
        raise SearchErrorMexico(msg=messsage, code=error_code)

    elif error_code == "22":
        raise InvalidIssuer(msg=messsage, code=error_code)

    elif error_code == "23":
        raise ReferenceError(msg=messsage, code=error_code)

    elif error_code == "24":
        raise FailedGenerateReference(msg=messsage, code=error_code)

    elif error_code == "25":
        raise InvalidAmount(msg=messsage, code=error_code)

    elif error_code == "50":
        raise InvalidOperation(msg=messsage, code=error_code)

    elif error_code == "61":
        raise OperationDoesNotExist(msg=messsage, code=error_code)

    elif error_code == "71":
        raise OperationDoesNotExist(msg=messsage, code=error_code)

    elif error_code == "150":
        raise ErrorServicePayCash(msg=messsage, code=error_code)

    elif error_code == "101":
        raise ErrorReferenceLatam(msg=messsage, code=error_code)

    elif error_code == "102":
        raise ErrorSearchLatam(msg=messsage, code=error_code)

    elif error_code == "105":
        raise ErrorCancelLatam(msg=messsage, code=error_code)

    elif error_code == "112":
        raise TokenExpired(msg=messsage, code=error_code)

    else:
        raise UnknownError(msg="Error desconocido", code="101")


def _check_response(response: Response):
    _raise_error_response(response.json())
