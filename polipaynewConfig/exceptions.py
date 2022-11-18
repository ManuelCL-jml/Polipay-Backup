from dataclasses import dataclass
from typing import List, Dict, Any

from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler
from rest_framework import serializers, status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data['status_code'] = response.status_code

    return response


##usuario no encontrado
def get_CustomUser_Or_Error(instance, *args, **kwargs):
    try:
        user = instance.objects.filter(*args, **kwargs)
        if len(user) != 0:
            return user
    except:
        raise serializers.ValidationError({"status": "Usuario no encontrado"})


##objeto no encontrado
def get_Object_Or_Error(instance, *args, **kwargs):
    try:
        object = instance.objects.get(*args, **kwargs)
        return object
    except:
        raise serializers.ValidationError({"status": "Objecto no encontrado"})


##Identificar numero entero
def NumInt(size):
    try:
        size = int(size)
        return size
    except:
        raise serializers.ValidationError({"status": "Se esperaba un numero entero"})


class transaction_error(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Error al validar"
    default_code = 'invalido'

    def __init__(self, message):
        super(transaction_error, self).__init__(message)

        try:
            raise transaction_error()
        except transaction_error as e:
            print(str(e))


def filter_Object_Or_Error(instance, *args, **kwargs):
    object = instance.objects.filter(*args, **kwargs)
    if object:
        return object
    else:
        raise serializers.ValidationError({"status": "Objecto no encontrado"})


def add_list_errors(data: Dict, list_errors: List):
    return list_errors.append(data)


# Funcion de respuesta de error

def structure_response(code: int, status: str):
    return {
        "code": code,
        "status": status.upper()
    }


def satus_ok(message: str, code: int, extra_kwargs: Dict = None) -> Dict:
    data = structure_response(code, "ok")
    data['message'] = message
    data['extra_kwargs'] = extra_kwargs
    return data


def status_error(list_error: List) -> Dict:
    data = structure_response(400, "error")
    data["detail"] = list_error
    return data


# (ChrGil 2021-10-08) Agregar a un listado, los errores estandarizados
class ErrorsList:
    errors_list: List[Dict] = []

    def __init__(self, field: str = None, value: str = None, message: str = None):
        self.field = field
        self.value = value
        self.message = message
        self.add_error(self.render_error())

    def render_error(self) -> Dict:
        return {
            "field": 'null' if self.field is None else self.field,
            "data": 'null' if self.value is None else self.value,
            "message": 'null' if self.message is None else self.message
        }

    def add_error(self, data: Dict[str, Any]):
        self.errors_list.append(data)

    def show_errors_list(self) -> List[Dict]:
        return self.errors_list

    def clear_list(self):
        self.errors_list.clear()

    def len_list_errors(self) -> int:
        return len(self.errors_list)

    def print(self):
        print(self.errors_list)

    def standard_error_responses(self) -> Dict[str, Any]:
        return {
            "code": ['400'],
            "status": ["ERROR"],
            "detail": self.show_errors_list()
        }

# (JM 2021-12-06) Funcion para utilizar un get con error actualizado a back end
def GetObjectOrError(instance, *args, **kwargs):
    try:
        object = instance.objects.get(*args, **kwargs)
        return object
    except:
        mensaje = "No se encontro ningun registro"
        for datos in kwargs:
            raise serializers.ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [{"field": datos , "data":kwargs.get(datos),"message": mensaje}]})

# (JM 2021-12-06 Funcion para mostrar errores)

def MensajeError(error):
    if error:
        raise serializers.ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [error]})
    else:
        return

