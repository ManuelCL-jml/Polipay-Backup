from typing import ClassVar, Dict, Any, NoReturn, Union, List
from dataclasses import dataclass, field

from apps.api_stp.interface import CatError


@dataclass
class CatErrorsCobranzaAbonoSTP(CatError):
    _cat: ClassVar[Dict[str, Any]] = {
        1: "Institución no catalogado",
        2: "Clave rastreo no valido",
        3: "Clave de rastreo duplicada",
        4: "Asegúrese que la longitud no sea mayor a 45 caracteres",
        5: "Asegúrese que la longitud no sea mayor a 20 digitos",
        6: "Asegúrese que la longitud no sea mayor a 40 caracteres",
        7: "Asegúrese que la longitud no sea mayor a 7 digitos",
        8: "Asegúrese que la longitud no sea mayor a 13 caracteres",
        9: "Asegúrese que la longitud no sea mayor a 30 caracteres",
        10: "Cuenta invalida",
        11: "La cuenta no existe",
        12: "Formato de fecha no valido",
        13: "Monto no valido",
        14: "Tipo cuenta no catalogado o formato no valido",
        15: "Formato de cadena numerica no valido",
        16: "Tipo de dato no esperado",
        17: "Asegúrese que la longitud no sea mayor a 14 caracteres",
        18: "Beneficiario no valido o no existe",
        19: "Cuenta clabe no válida o no existe",
        20: "Folio de la transacción no valido o no existe",
        21: "Asegúrese que la longitud no sea mayor a 8 digitos",
        22: "Asegúrese que la longitud no sea mayor a 10 digitos",
        23: "Asegúrese que la longitud no sea mayor a 14 digitos",
    }

    def get_error(self, error_id: int) -> str:
        return self._cat.get(error_id)


@dataclass
class MyErrorValidation:
    error_detail: ClassVar[Dict[str, Any]]

    def __init__(self, cat_error: CatError, error_id: int, field: str, data: Union[str, int, float, bool, Any]):
        self._cat_error = cat_error
        self._error_id = error_id
        self._field = field
        self._data = data

        self.create_error()

    def create_error(self) -> NoReturn:
        self.error_detail = {
            "error_id": self._error_id,
            "field": self._field,
            "data": self._data,
            "message": self._cat_error.get_error(self._error_id)
        }


@dataclass
class AddErrorStack:
    _error_stack: List[Dict[str, Any]] = field(default_factory=list)

    def add(self, validation: MyErrorValidation):
        self._error_stack.append(validation.error_detail)

    @property
    def len_list_error_stack(self) -> int:
        return len(self._error_stack)

    def clear_stack(self) -> NoReturn:
        self._error_stack.clear()

    @property
    def estructura_error(self):
        return {
            "code": [400],
            "status": ["ERROR"],
            "detail": self._error_stack
        }