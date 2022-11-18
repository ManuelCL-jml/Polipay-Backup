import datetime
import base64
import itertools

#from datetime import date
from django.db.models import Q
from django.core.files import File
from rest_framework.serializers import ValidationError

from random import choice
from string import ascii_letters, digits
from typing import Dict

from .models import CredencialesAPI
from apps.users.models import grupoPersona, persona, tarjeta, cuenta, documentos, trelacion
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog

DATE_FORMAT = '%Y%m%d'


def get_instance_grupo_persona(admin_id: int, endpoint:str) -> isinstance:
    message_not_register = {
        "code": [400],
        "status": "ERROR",
        "detail": [
            {
                "data": admin_id,
                "field": "id",
                "message": "Not existing Id.",
            }
        ]
    }
    message_not_admin = {
        "code": [400],
        "status": "ERROR",
        "detail": [
            {
                "data": admin_id,
                "field": "id",
                "message": "Not an admin id.",
            }
        ]
    }
    try:  # verificamos que exista esa persona en la base de datos
        persona.objects.get(id=admin_id)
    except Exception as e:
        # Aqui se hace uso del caso en el que el id para la función RegisterSystemLog debe ir vacío, comentar a CHRIS A
        RegisterSystemLog(idPersona=-1, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_not_register)
        raise ValidationError(message_not_register)
    try:  # verificamos que sea un id de un administrativo de cuenta eje
        return grupoPersona.objects.get(Q(relacion_grupo_id=1) | Q(relacion_grupo_id=3), person_id=admin_id,
                                        is_admin=True)
    except Exception as e:
        RegisterSystemLog(idPersona=admin_id, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_not_admin)
        raise ValidationError(message_not_admin)


# FUNCION QUE DADO EL ID DE UN ADMINISTRATIVO RECUPERA EL ID DE LA CUENTA EJE A LA QUE PERTENECE
def get_id_cuenta_eje(admin_id: int, endpoint:str) -> int:
    return get_instance_grupo_persona(admin_id, endpoint).get_only_id_empresa()


# FUNCION QUE RECUPERA LA LISTA DE ADMINISTRATIVOS ASOCIADOS A UNA CUENTA EJE
def get_list_admins(cuenta_eje_id: int) -> list:
    list_admin = []  # Contendra unicamente las instancias de administrativos de la cuenta eje
    list_instance_admin = grupoPersona.objects.filter(
        Q(relacion_grupo_id=1) | Q(relacion_grupo_id=3),
        empresa_id=cuenta_eje_id,
        is_admin=True)  # hace referencia a la informacion de la cuenta eje brindada (grupoPersona)
    for admin in list_instance_admin:
        instance_admin = persona.objects.get(id=admin.person_id)
        list_admin.append(instance_admin)
    return list_admin


def filter_credentials(name: str, date_start, date_end) -> list:
    list_cuentas_eje = persona.objects.filter(
        name__icontains=name,
    )
    credentials_list = []

    for cuenta in list_cuentas_eje:
        dict_credential = {}
        try:
            credential = CredencialesAPI.objects.get(personaRel_id=cuenta.id, fechaCreacion__gte=date_start,
                                                     fechaCreacion__date__lte=date_end)
            dict_credential['cuenta_eje_name'] = cuenta.name
            dict_credential['id_cuenta_eje'] = cuenta.id
            dict_credential['username'] = credential.username
            dict_credential['password'] = credential.password
            dict_credential['fechaCreacion'] = credential.fechaCreacion
            credentials_list.append(dict_credential)
        except Exception as e:
            pass
    return credentials_list


# FUNCION QUE VALIDA QUE EL ID PROPORCIONADO SEA DE UN SUERADMINISDOR DEL SISTEMA
def validate_superadmin(id_superadmin, endpoint):
    try:
        persona.objects.get(id=id_superadmin, is_superuser=True)
    except Exception as e:
        message_not_superadmin = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": id_superadmin,
                    "field": "id_superadmin",
                    "message": "Not valid ID",
                }
            ]
        }
        RegisterSystemLog(idPersona=-1, type=1,      #corregir con la funcion de Avalos
                          endpoint=endpoint,
                          objJsonResponse=message_not_superadmin)
        raise ValidationError(message_not_superadmin)


# FUNCION QUE VERIFICA QUE LAS PERSONA EXIST EN LA DB
def get_Persona_orList_error(instance, id_cuentaeje, endpoint:str, *args, **kwargs):
    try:
        object = instance.objects.get(*args, **kwargs)
        return object
    except Exception as e:
        message_not_validID = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": kwargs["id"],
                    "field": "id_persona",
                    "message": "Not valid person ID",
                }
            ]
        }
        RegisterSystemLog(idPersona=id_cuentaeje, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_not_validID)
        raise ValidationError(message_not_validID)


# FUNCION QUE VALIDA QUE LA INSTANCIA PROPORCIONADA EXISTA EN EL MODELO CORRESPONDIENTE
def get_Object_orList_error(instance, id_cuentaeje, endpoint:str, *args, **kwargs):
    try:
        object = instance.objects.get(*args, **kwargs)
        return object
    except Exception as e:
        message_not_found = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": instance.__name__,
                    "field": "",
                    "message": "Wrong data, register not found",
                }
            ]
        }
        RegisterSystemLog(idPersona=id_cuentaeje, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_not_found)
        raise ValidationError(message_not_found)


def get_card_Stock(person_id):
    disponibles = 0
    asignadas = 0
    tarjetas = tarjeta.objects.filter(clientePrincipal_id=person_id)

    for card in tarjetas:
        if card.statusInterno_id == 1:
            disponibles += 1
        elif card.statusInterno_id == 2:
            asignadas += 1
    total = disponibles + asignadas
    card_stock = {'total_tarjetas': total, 'total_tarjetas_asignadas': asignadas,
                  'total_tarjetas_disponibles': disponibles}
    return card_stock


def personalexterno_list(personalexterno_id_list) -> list:
    list_personalexterno = []
    for personalexterno_id in personalexterno_id_list:
        personaexterna = persona.objects.get(id=personalexterno_id["person_id"])
        personaexterna_detail = {
            "id": personaexterna.id,
            "email": personaexterna.email,
            "fecha_nacimiento": personaexterna.fecha_nacimiento,
            "name": personaexterna.name,
            "last_name": personaexterna.last_name,
            "phone": personaexterna.phone,
            "curp": personaexterna.curp
        }
        list_personalexterno.append(personaexterna_detail)
    return list_personalexterno


# funcion para validar la credenciales para la API --Aun en construccion------------------------------
def validate_credentials(username, password, endpoint:str):
    try:  # Aqui va la desencriptacion de la password
        instance_credential = CredencialesAPI.objects.get(username=username, password=password)
    except Exception as e:
        message_credentials_not_found = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": "",
                    "field": "",
                    "message": "Not valid credentials",
                }
            ]
        }
        #Aqui se hace uso del caso en el que el id para la función RegisterSystemLog debe ir vacío, comentar a CHRIS A
        RegisterSystemLog(idPersona=-1, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_credentials_not_found)
        raise ValidationError(message_credentials_not_found)
    return instance_credential.personaRel_id


def getKward(request):
    diccionario = {}

    if request['date_start'] != 'null':
        date_s = datetime.datetime.strptime(request['date_start'], '%d/%m/%y %H:%M:%S')
        diccionario['fecha_creacion__gte'] = date_s.date()
    if request['date_start'] == 'null':
        datenow = datetime.datetime.now()
        date_s = datenow - datetime.timedelta(days=30)
        diccionario['fecha_creacion__gte'] = date_s.date()
    if request['date_end'] == 'null':
        date_e = datetime.datetime.now()
        diccionario['fecha_creacion__lte'] = date_e.date()
    if request['date_end'] != 'null':
        date_e = datetime.datetime.strptime(request['date_end'], '%d/%m/%y %H:%M:%S')
        diccionario['fecha_creacion__lte'] = date_e.date()

    return diccionario


def generar_username(nombre, apellido):  ###  Crear usuario de persona externa
    for _ in iter(int, 1):
        code = ''.join([choice(ascii_letters + digits) for i in range(15)])
        username_code = nombre.replace(" ", "") + apellido.replace(" ", "") + str(code)
        username_45 = username_code[:45]
        if persona.objects.filter(username=username_45):
            pass
        else:
            username = persona.objects.filter(username=username_45)
            return username_45


"""
    create_file
    Recibe documento encriptado (cadena base64) y lo transforma en documento pdf
"""


# (ChrGil 2021-11-02) Crear archivo
def create_file(file: str, person_id: int):
    decrypted = base64.b64decode(file)
    with open(f"TMP/API_dispersa/persona_externo_id_{person_id}_{strftime(datetime.date.today())}.pdf", "wb") as file:
        file.write(decrypted)
    return file.name


"""
    strftime
    Convierte un datetime objects a un string
"""


# (ChrGil 2021-12-07) Convierte un datetime objects a un string
def strftime(date: datetime.date):
    return date.strftime(DATE_FORMAT)


"""
    PersonaExternaGrupoPersona
    Liga el personal externo recien creado a la cuenta eje que le corresponda en la tabla "grupoPersona"
"""


def persona_externa_grupopersona(cuenta_eje_id, instance, endpoint:str):
    relacion_grupo_persona = get_Object_orList_error(trelacion, cuenta_eje_id, endpoint, id=6)
    persona_externa = grupoPersona.objects.create(empresa_id=cuenta_eje_id, person_id=instance.id,
                                                  nombre_grupo="Personal Externo",
                                                  relacion_grupo=relacion_grupo_persona)
    return


"""
    order_cuenta
    Genera el registro en la tabla cuenta del nbuevo personal externo cuidando que su campo "cuenta" no exista ya en la 
    DB
"""


def order_cuenta(instance):  ### Ordenar y crear cuenta de persona externa
    queryset = cuenta.objects.all()
    cuenta_min = int(8999999999)
    cuentas_list = []
    for data in queryset:
        cuentas = ''.join(filter(str.isdigit, data.cuenta))  # eliminamos alguna letra
        if int(cuentas) > int(cuenta_min):  # retornamos solo numeros igual o mayor a 9000000000
            cuentas_list.append(cuentas)
    num_cuenta = code_cuenta(cuentas_list)
    account = cuenta.objects.create(cuenta=num_cuenta, persona_cuenta_id=instance.id,
                                    cuentaclave="XXXXXXX" + str(num_cuenta) + "X",
                                    is_active=True)
    return account


"""
    code_cuenta
    verfica que el codigo (campo cuenta) no exista aún en la tabla
"""


def code_cuenta(cuentas_list):  ### Crear cuenta de persona externa
    for cuenta_num in itertools.count(start=9000000000):
        if str(cuenta_num) not in str(cuentas_list):
            return cuenta_num


"""
    Estructura especial para poder hacer dispersiones
"""


def get_data_empresa(id_emp) -> Dict:
    instance_emp = persona.objects.get(id=id_emp)
    empresa_data = {
        "id": instance_emp.id,
        "name": instance_emp.name,
        "is_active": instance_emp.is_active,
        "create": instance_emp.date_joined,
        "clabe": instance_emp.clabeinterbancaria_uno
    }
    return empresa_data


"""
    Valida que el correo recibido sea de un administrativo de la cuenta eje proporcionada
"""


def validate_email_admin(id_cuenta_eje, email, endpoint:str):
    try:
        id_admin = persona.objects.get(email=email).get_only_id()

    except Exception as e:
        message_unexisting_email = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": email,
                    "field": "email",
                    "message": "Not existing email",
                }
            ]
        }
        RegisterSystemLog(idPersona=id_cuenta_eje, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_unexisting_email)
        raise ValidationError(message_unexisting_email)

    queryset = grupoPersona.objects.filter(
        Q(relacion_grupo_id=1) | Q(relacion_grupo_id=3),
        empresa_id=id_cuenta_eje, person_id=id_admin,
        is_admin=True)
    if not queryset:
        message_not_admin = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": email,
                    "field": "email",
                    "message": "Not valid admin email",
                }
            ]
        }
        RegisterSystemLog(idPersona=id_cuenta_eje, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_not_admin)
        raise ValidationError(message_not_admin)
    else:
        return True


"""
    Valida que una lista de personas pertenezcan a una cuenta eje
"""


def validate_list_persona(person_list, cuenta_eje_id, endpoint:str):
    for person in person_list:
        try:  # Se verifica que la cuenta del beneficiario exista en la BD
            instance_cuenta = cuenta.objects.get(cuenta=person['cta_beneficiario']).get_person_id
        except Exception as e:
            message_unexisting_cuenta = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": person['cta_beneficiario'],
                        "field": "cta_beneficiario",
                        "message": "Not existing cuenta beneficiario",
                    }
                ]
            }
            RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_unexisting_cuenta)
            raise ValidationError(message_unexisting_cuenta)
        try:  # Se verifica que la persona le pertenezca la cuenta
            instance_persona = persona.objects.get(id=instance_cuenta, email=person['email']).get_only_id()
        except Exception as e:
            message_not_matching_persona_cuenta = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": person['email'],
                        "field": "email",
                        "message": "Not matching email with cuenta beneficiario",
                    }
                ]
            }
            RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_not_matching_persona_cuenta)
            raise ValidationError(message_not_matching_persona_cuenta)
        try:  # Se verifica que la persona pertenecezca a la cuenta eje
            instance_grupo_persona = grupoPersona.objects.get(empresa_id=cuenta_eje_id, person_id=instance_persona)
        except Exception as e:
            message_not_from_cuenta_eje = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": person['email'],
                        "field": "email",
                        "message": "Cuenta beneficiaria does not belong to cuenta eje",
                    }
                ]
            }
            RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_not_from_cuenta_eje)
            raise ValidationError(message_not_from_cuenta_eje)
    return True


"""
    Valida que la suma de los N montos a dispersar sea igual a monto total
"""


def validate_monto_total(person_list, monto_total, cuenta_eje_id, endpoint:str):
    suma_montos = 0
    for person in person_list:
        suma_montos = person['monto'] + suma_montos
        if person['monto'] < 0:
            message_negative_monto = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": person['monto'],
                        "field": "monto",
                        "message": "Invalid amount",
                    }
                ]
            }
            RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_negative_monto)
            raise ValidationError(message_negative_monto)
    if monto_total == suma_montos:
        return True
    else:
        message_not_matching_montos = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": monto_total,
                    "field": "MontoTotal",
                    "message": "Total amount must equal the sum of individual amounts ",
                }
            ]
        }
        RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_not_matching_montos)
        raise ValidationError(message_not_matching_montos)


"""
    Validacion que verifica que unicamente se tengan 5 tarjetas por cuenta
"""


def validate_cards_count(instance, lista_tarjetas, cuenta_eje_id, endpoint:str):
    queryset = tarjeta.objects.filter(cuenta_id=instance.id)
    total_len = len(lista_tarjetas) + len(queryset)
    if len(queryset) == 5:
        message_enough_cards = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": instance.cuenta,
                    "field": "Cuenta",
                    "message": "This account already has 5 cards",
                }
            ]
        }
        RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_enough_cards)
        raise ValidationError(message_enough_cards)
    elif total_len >= 5:
        message_only_5cards = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": instance.cuenta,
                    "field": "Cuenta",
                    "message": "This account can only storage a top of 5 cards",
                }
            ]
        }
        RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_only_5cards)
        raise ValidationError(message_only_5cards)


def validate_tarjeta_cuenta(cuenta_id, numero_tarjeta, numera_cuenta, cuenta_eje_id, endpoint:str):
    queryTarjeta = tarjeta.objects.filter(tarjeta=numero_tarjeta, cuenta_id=cuenta_id).exists()
    if not queryTarjeta:
        message_not_matching_tarjeta_cuenta = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": numero_tarjeta,
                    "field": "cta_beneficiario",
                    "message": "Not matching cta_beneficiario with cuentatransferencia",
                }
            ]
        }
        RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_not_matching_tarjeta_cuenta)
        raise ValidationError(message_not_matching_tarjeta_cuenta)
    queryCuenta = cuenta.objects.filter(id=cuenta_id, cuenta=numera_cuenta).exists()
    if not queryCuenta:
        message_not_matching_numero_cuenta = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": numera_cuenta,
                    "field": "cuenta_emisor",
                    "message": "Not matching cuenta_emisor with cuentatransferencia",
                }
            ]
        }
        RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_not_matching_numero_cuenta)
        raise ValidationError(message_not_matching_numero_cuenta)
    return True


def validate_PE_cuenta_eje(person_id, cuenta_eje_id, endpoint:str):
    queryPersonalExterno = grupoPersona.objects.filter(person_id=person_id, empresa_id=cuenta_eje_id,
                                                       relacion_grupo_id=6).exists()
    if not queryPersonalExterno:
        message_not_matching_tarjeta_cuenta = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": "",
                    "field": "",
                    "message": "Not matching personal externo with cuenta eje",
                }
            ]
        }
        RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_not_matching_tarjeta_cuenta)
        raise ValidationError(message_not_matching_tarjeta_cuenta)
    return True


"""
    VALIDA QUE LA FECHA INGRESADA SEA POSTERIOR A LA FECHA ACTUAL
    ***validación necesaria para cuando se desean programar dispersiones
"""


def validate_later_date(is_schedule: bool, prog_date: datetime, cuenta_eje_id, endpoint:str):
    pdate = datetime.datetime.strptime(prog_date, "%Y-%m-%d %H:%M:%S")
    if is_schedule and datetime.datetime.today() > pdate:
        message_not_validate_date = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": prog_date,
                    "field": "schedule",
                    "message": "Not validate date, schedule date must be subsequent to the current date"
                }
            ]
        }
        RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_not_validate_date)
        raise ValidationError(message_not_validate_date)
    return True
