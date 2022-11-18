import decimal
import uuid
import io
import string
import base64
import random
import datetime
from decimal import Decimal
from typing import Union, Dict, Any, List
import PyPDF2
from django.http import QueryDict
from django_user_agents.utils import cache
from drf_extra_fields.fields import Base64FileField

from rest_framework.authtoken.models import Token

from apps.users.constants import TIME
from apps.users.models import grupoPersona, persona

DATE_FORMAT = '%Y%m%d'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


# (ChrGil 2021-12-07) Convierte un datetime objects a un string
def strftime(date: datetime.date):
    return date.strftime(DATE_FORMAT)


def strfdatetime(date: datetime.datetime) -> str:
    return date.strftime(DATE_FORMAT)


def strptime(date: Union[int, str]):
    return datetime.datetime.strptime(str(date), DATE_FORMAT).date()


# (ChrGil 2021-11-02) Crear archivo
def create_file(file: str, person_id: int):
    decrypted = base64.b64decode(file)
    with open(f"TMP/cliente_id_{person_id}_{strftime(datetime.date.today())}.pdf", "wb") as file:
        file.write(decrypted)
    return file.name


# (ChrGil 2021-12-09) Genera una contraseña de 12 caracteres de manera aleatoria
def random_password() -> str:
    return "".join(random.choices(string.hexdigits, k=12))


def create_numer_folio(length: int) -> str:
    return "".join(random.choices(string.digits, k=length))


# (AAF 2021-12-09) para serializador de documentos pdf
class PDFBase64File(Base64FileField):
    ALLOWED_TYPES = ['pdf']

    def get_file_extension(self, filename, decoded_file):
        try:
            PyPDF2.PdfFileReader(io.BytesIO(decoded_file))
        except PyPDF2.utils.PdfReadError as e:
            return (e)
        else:
            return 'pdf'


# (ChrGil 2021-12-20) Genera un UUID unico para cada clave traspaso
def generate_clave_rastreo_with_uuid():
    my_uuid = uuid.uuid4().hex.upper()
    print(len(my_uuid))
    my_uuid = my_uuid.replace(my_uuid[0:4], "    ")
    my_uuid = my_uuid.strip()
    my_uuid_result = f"PO{my_uuid}"
    return my_uuid_result


def generate_value_paycash_with_uuid():
    my_uuid = uuid.uuid4().hex.upper()
    my_uuid = my_uuid.replace(my_uuid[0:4], "  ")
    my_uuid = my_uuid.strip()
    my_uuid_result = f"PO{my_uuid}"
    return my_uuid_result


# (ChrGil 2022-01-06) Obtener la empresa Adelante Zapopan (Temporal)
def get_instance_grupo_persona_adelante_zapopan(admin_id: int) -> grupoPersona:
    return grupoPersona.objects.get_object_admin_company_adelante_zapopan(person_id=admin_id)


# (ChrGil 2022-01-06) Obtener la empresa Adelante Zapopan (Temporal)
def get_id_cuenta_eje_adelante_zapopan(admin_id: int) -> int:
    return get_instance_grupo_persona_adelante_zapopan(admin_id).get_only_id_empresa()


# (ChrGil 2022-01-06) Obtener la información de la cuenta eje Adelante Zapopan (Temporal)
def get_data_empresa_adelante_zapopan(admin_id: int) -> Dict[str, Any]:
    return get_instance_grupo_persona_adelante_zapopan(admin_id).company_details


def get_instance_grupo_persona(admin_id: int) -> grupoPersona:
    return grupoPersona.objects.get_object_admin_company(person_id=admin_id)


def get_id_cuenta_eje(admin_id: int) -> int:
    return get_instance_grupo_persona(admin_id).get_only_id_empresa()


def remove_asterisk(text: str):
    if text:
        if "*" in text:
            r = text.split("*")

            if r[0] == '':
                return "".join(r).replace(' ', '')

            if r[1] == '':
                return "".join(r).replace(' ', '')

            if r[0] != '' and r[1] != '':
                return " ".join(r)

            if r[0] == '' and r[1] == '':
                return ''

    return text


def get_values_list(key: str, list_dict: List[Dict[str, Any]]) -> Union[List[Union[str, int, bool, float]], bool]:
    try:
        if not isinstance(list_dict, list):
            raise ValueError(f'Se esperaba una lista de diccionarios pero entro: {type(list_dict)}')

        if not isinstance(list_dict[0], dict):
            raise ValueError(f'Se esperaba un diccionario pero entro: {type(list_dict[0])}')

        return [item.get(key) for item in list_dict]
    except IndexError as e:
        return False


def generateCodeCache(email: str) -> str:
    code = random.randrange(1000, 9999, 4)
    cache.set(email, str(code), TIME)
    return cache.get(email)


def generate_url(request, email=None) -> str:
    url = f"{request.scheme}://{request.headers['host']}/users/v2/check/code/?email={email}&code="
    return url


def generate_url_app_token(request, email=None) -> str:
    url = f"{request.scheme}://{request.headers['host']}/users/v3/check/code/?email={email}&code="
    return url


def verification_session_user(url: str, user: Dict[str, Any]) -> str:
    url += generateCodeCache(user.get('email'))
    return url


# (ChrGil 2022-01-19) Elimina valores duplicados de una lista
def remove_equal_items(key: str, list_data: List[Dict[str, Any]]) -> List[Any]:
    result = get_values_list(key, list_data)
    items = []
    data = []

    def remove_equal(list_dict_data: List[Any], index: int = 0):
        i = index
        try:
            if list_dict_data[i] not in items:
                items.append(list_dict_data[i])
                data.append(list_data[i])
                i += 1
                return remove_equal(list_dict_data, i)

            i += 1
            return remove_equal(list_dict_data, i)
        except IndexError as e:
            return data

    return remove_equal(result)


def get_month(key: int) -> Union[str, None]:
    cat_month = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre"
    }

    return cat_month.get(key)


_NUMBER_DECIMALS: int = 4


# (ChrGil 2022-01-31) Calcula el iva a pagar
def iva(amount: Decimal) -> Decimal:
    return Decimal(amount * Decimal(0.16))


# (ChrGil 2022-01-31) Calcula la comisión a pagar
def calculate_commission(amount: Union[int, float], comission: Decimal) -> Decimal:
    return Decimal(Decimal(amount) * Decimal(comission))


# (ChrGil 2022-01-31) Suma el iva a la comisión
def add_iva(amount: Decimal) -> Decimal:
    return Decimal(amount + iva(amount))


# (ChrGil 2022-02-02) Convierte a dict los parametros de url
def to_dict_params(query_params: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in query_params.items()}


# (ChrGil 2022-03-23) Definir si es año biciesto o no
def leap_year(anio: int) -> bool:
    return anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)


def obtener_dias_del_mes(mes: int, anio: int) -> int:
    # Abril, junio, septiembre y noviembre tienen 30
    if mes in [4, 6, 9, 11]:
        return 30
    # Febrero depende de si es o no bisiesto
    if mes == 2:
        if leap_year(anio):
            return 29
        else:
            return 28
    else:
        # En caso contrario, tiene 31 días
        return 31


def create_token(person_id: int) -> str:
    if Token.objects.filter(user_id=person_id).exists():
        Token.objects.get(user_id=person_id).delete()

    persona.objects.filter(id=person_id).update(is_active=True)
    return Token.objects.create(user_id=person_id).key


def get_homoclave(rfc: str) -> str:
    result = len(rfc) - 3
    homoclave = []

    for index in range(0, len(rfc)):
        if index == result:
            homoclave.append(rfc[index])
            result += 1

    return "".join(homoclave)
