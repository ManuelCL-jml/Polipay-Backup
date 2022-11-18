import itertools
from os import error
import string
import time
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
from dateutil.relativedelta import relativedelta
import random
import base64
import datetime
from typing import Dict, Union
from random import choice
from string import ascii_letters, digits
import re
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import urllib.parse
### pdf
from PyPDF2 import PdfFileWriter, PdfFileReader
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from PyPDF2 import PdfFileWriter, PdfFileReader
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.db.models import Q
from django.core.cache import cache
from django.core.files import File
from apps.solicitudes.models import Solicitudes
from apps.permision.manager import *

from rest_framework.serializers import ValidationError
from MANAGEMENT.SMS.send_sms import EnviarCodigoSMS
from MANAGEMENT.VoiceMail.send_call import *
from polipaynewConfig.inntec import CategoriasInntecError, get_token, get_CardsStock, get_CardsAsignadas, \
    get_MovimientosTarjetas, get_Saldos
from .messages import *
from .constants import *
from .models import documentos, domicilio, grupoPersona, cuenta, persona, trelacion, tarjeta, TDocumento
from MANAGEMENT.Language.LanguageUnregisteredUser import LanguageUnregisteredUser
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from ..transaction.exc import CardNotFound, FailAssignedCard


def codigoSMS(phone):
    code = random.randrange(1000, 9999, 3)
    cache.set(phone, str(code), TIME)
    return cache.get(phone)


def createCodeSMSCache(instance):
    code = codigoSMS(instance.email)  # -----> Antes era instance.phone, pero se junto el codigoSMS y del email
    EnviarCodigoSMS(code, instance)
    return


def generateCodeCache(email):
    code = random.randrange(1000, 9999, 4)
    cache.set(email, str(code), TIME)
    return cache.get(email)


def createCodeCache(instance: persona):
    code = generateCodeCache(instance.email)
    if instance.tipo_persona_id == 2:
        createMessageAsigmentCode(instance, code, 'código')
        return

    if instance.tipo_persona_id == 3:
        send_mail_brigadistas(instance, code)
        return


def get_Object_orList_error(instance, *args, **kwargs):
    try:
        object = instance.objects.get(*args, **kwargs)
        return object
    except Exception as e:
        raise ValidationError({"status": [
            "¡Lo sentimos!\n\nOcurrió un error o el correo que ingresaste no se encuentra registrado.Si el problema persiste contacta a un asesor\nPolipay."]})
        # raise ValidationError({"status": ["Información incorrecta, no se encuentra registrado."]})

def get_Object_orList_err(instance, *args, **kwargs):
    try:
        object = instance.objects.get(*args, **kwargs)
        return object
    except Exception as e:
        raise ValidationError({"status": [
            "el registro en "+str(instance)+"no existe"]})


def get_Object_orList_error_language(instance, *args, **kwargs):
    try:
        object = instance.objects.get(*args, **kwargs)
        return object
    except Exception as e:
        if args["idPersona"] == 0:
            msg = LanguageUnregisteredUser(args["idLang"], args["idMessage"])
            raise ValidationError({"status": [msg]})
        elif args["idPersona"] >= 1:
            msg = LanguageRegisteredUser(args["idPersona"], args["idMessage"])
            raise ValidationError({"status": [msg]})


def Code_card(size_number):
    valores = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    size = size_number
    code = "".join([str(random.choice(valores)) for i in range(size)])
    return code


def getTotalsCounts(counts):
    if len(counts) == 5:
        return False
    else:
        return True


# - - - - - - - - - - F u n c i o n e s   I m p l e m e n t a d a s   E n   U s e r s - - - - - - - - - -

def generate_url(request, email=None, token_device=None):
    """
    Ahora la url se genera en el endpoint LoginMovil

    """
    url = f"{request.scheme}://{request.headers['host']}/users/v2/check/code/?email={email}&code="
    return url


def get_information_client(request):
    """
    Metodo gereral para obtener el HTTP_X_REAL_IP
    del cliente, sistema operativo y plataforma

    REMOTE_ADDR siempre cambia en local
    Para produccion utilizar: return request.META['HTTP_X_REAL_IP']
    Para localhost utilizar: return request.META['REMOTE_ADDR']
    """
    return request.META['HTTP_X_REAL_IP']


def verification_session_user(url, user):
    url += generateCodeCache(user.email)
    send_mail_warnign(user, url)
    return True


def create_pdf_data(file):
    decrypted = base64.b64decode(file)
    with open("TEMPLATES/Files/file.pdf", "wb") as f:
        pdf = f.write(decrypted)
    return pdf


def create_pdf_data_v2(file, instance):
    decrypted = base64.b64decode(file)
    with open('TMP/web/' + instance.username + '.pdf', "wb") as f:
        pdf = f.write(decrypted)
    return pdf

def create_pdf_data_personal_externo(file, instance):
    decrypted = base64.b64decode(file)
    with open('TMP/web/' + instance.username + '.pdf', "wb") as f:
        pdf = f.write(decrypted)
    return pdf


def create_pdf_data_v3(file, instance):
    decrypted = base64.b64decode(file)
    with open('TMP/web/Ine_admins_cuenta_eje' + instance.username + '.pdf', "wb") as f:
        pdf = f.write(decrypted)
    return pdf


def EliminarDoc(instance):
    if instance.status == 'D':
        instance.documento.delete()
        instance.delete()
    else:
        raise ValidationError('No puedes eliminar un archivo con estado "Pendiente" o "Aceptado"')


def filter_object_if_exist(instance, *args, **kwargs):
    return instance.objects.filter(*args, **kwargs).exists()


def filter_data_or_return_none(instance, *args, **kwargs):
    return instance.objects.filter(*args, **kwargs).first()


def filter_all_data_or_return_none(instance, *args, **kwargs):
    return instance.objects.filter(*args, **kwargs)


def select_related(relation: str, instance: object, *args, **kwargs):
    return instance.objects.select_related(relation).filter(*args, **kwargs)


def create_or_delete_token(token, instance):
    if filter_object_if_exist(token, user=instance):
        get_Object_orList_error(token, user=instance).delete()
        token = token.objects.create(user=instance)
        return token.key

    token = token.objects.create(user=instance)
    return token.key


def is_admin_or_collaborator(persona, grupo_persona):
    """ Si es un administrador o super retorna (5)"""
    if persona.is_staff or persona.is_superuser:
        return 5

    group_business = get_Object_orList_error(grupo_persona, person_id=persona.id)
    if group_business.is_admin:
        return 5

    data = documentos.objects.filter(Q(status__startswith='C') & Q(authorization=True), person_id=persona.id)
    return len(data)


def generate_password(last_name, phone):
    """ Generamos un password atravez de last_name y phone """

    password = " ".join(last_name).split() + " ".join(str(phone)).split()
    return "".join([random.choice(password) for i in range(10)])


# - - - - - - - - - - F u n c i o n e s   I m p l e m e n t a d a s   E n   C e n t r o   D e   C o s t o s - - - - - - - - - -

def to_list(key: str):
    """ Lista de compreción de la clabe interbancaria """

    data = [i for i in str(key)]
    return data


def get_account(clabe: str):
    """ Se obtiene la cuenta de la clabe interbancaria """

    list_clabe = to_list(clabe)
    list_clabe.pop()
    account = list_clabe[7:]
    cuenta = "".join(account)
    return cuenta


def to_int_values_cuenta(cuenta: str):
    return [int(value) for value in cuenta]


def cuenta_multiply_ponderacion(cuenta: list, ponderacion: list):
    return [cuenta[index] * ponderacion[index] for index in range(0, 16)]


def return_mod_result_all_list(result: list):
    mod = [result[index] % 10 for index in range(0, 16)]
    n = 0

    for value in mod:
        n += value

    mod_result_with_mod = n % 10

    return mod_result_with_mod


def join_list(lista: list, min: int, max: int):
    return "".join(lista[min:max])


def algoritmo_digito_verificacion(cuenta: str):
    ponderacion = [3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7]
    list_cuenta = to_int_values_cuenta(cuenta)
    result_list = cuenta_multiply_ponderacion(list_cuenta, ponderacion)
    a = return_mod_result_all_list(result_list)

    b = 10 - a
    result = b % 10

    return f'{cuenta}{result}'


def shutdown_clabe(clabe: str):
    """ Damos de baja por 6 meses esta clave """

    lis_clabe = to_list(clabe)
    join_list = "".join(lis_clabe[13:-1])
    return join_list.replace("0", "X")


def generate_cuentaclave(cuenta_eje_id: int):
    """ Obtenemos la cuentaclave asosiada a esa razon social  """
    cuentaclabe = cuenta.objects.get(persona_cuenta_id=cuenta_eje_id).get_cuentaclabe()

    """ Convertimos esa cuenta de str a list """
    list_cuenta = to_list(cuentaclabe)

    """ atravez de un filtrado obtenemos la ultima cuenta creada """
    get_last_cuenta_clave = cuenta.objects.filter(cuentaclave__startswith=join_list(list_cuenta, 0, 10)).last()

    """ obtenemos solo los 3 digitos de centro de costos """
    get_cliente_final = "".join(to_list(get_last_cuenta_clave.get_cuentaclabe())[13:17])

    """ Generamos la nueva cuenta """
    generate_key = '{}{:03d}{:04d}'.format(
        join_list(list_cuenta, 0, 10),
        int(join_list(list_cuenta, 10, 13)),
        int(get_cliente_final) + 1
    )

    if (int(get_cliente_final) + 1) > 9999:
        return 'XXXXXXXXXXXXXXXXXX', False

    """ Agregamos el algoritmo de STP """
    new_cuentaclave = algoritmo_digito_verificacion(generate_key)

    return new_cuentaclave, True


def update_all_data(instance: object, id: int, *args, **kwargs):
    return instance.objects.filter(pk=id).update(*args, **kwargs)


def get_timezone():
    """
    Obtenemos la hora local

    """
    return datetime.datetime.now()


def get_timedelta(days: int, minutes: int):
    """
    De la hora local obtenida, definimos los dias o minutos que van
    a suceder en el futuro

    """

    return get_timezone() + datetime.timedelta(days=days, minutes=minutes)


def to_dict(validated_data: dict):
    data = {}
    for k, v in validated_data.items():
        data[k] = v
    return data


def codeCuenta(cuentas_list):  ### Crear cuenta de persona externa
    cuentas = cuenta.objects.filter().last()
    cuenta_num = int(cuentas.cuenta) + 1
    return cuenta_num


def PersonaExternaGrupoPersona(pk_user, instance):
    persona_externa = grupoPersona.objects.create(empresa_id=pk_user,
                                                  person_id=instance.id,
                                                  relacion_grupo_id=6,
                                                  nombre_grupo='Personal Externo')
    return persona_externa


def OrderCuenta(instance):  ### Ordenar y crear cuenta de persona externa
    nueva_cuenta = None
    cuentas = cuenta.objects.filter(cuenta__startswith='9').values('cuenta').last()

    if cuentas:
        cuenta_actual = int(cuentas['cuenta'])
        nueva_cuenta = cuenta_actual + 1

    if not cuentas:
        nueva_cuenta = "9000000001"

    account = cuenta.objects.create(
        cuenta=str(nueva_cuenta),
        persona_cuenta_id=instance.id,
        cuentaclave="XXXXXXX" + str(nueva_cuenta) + "X",
        is_active=True
    )

    return account.cuenta


# Crear cuenta de manera masiva


def actualizarDocumento(instance):
    instance_document = documentos.objects.get(person_id=instance.id, historial=False)
    instance_document.historial = True
    instance_document.save()
    SubirDocumento(instance)


def GenerarUsername(nombre, apellido):  ###  Crear usuario de persona externa
    for _ in iter(int, 1):
        code = ''.join([choice(ascii_letters + digits) for i in range(5)])
        username_code = nombre.replace(" ", "") + apellido.replace(" ", "") + str(code)
        username_45 = username_code
        username = persona.objects.filter(username=username_45)
        if len(username) == 0:
            return username_45


def SubirDocumento(instance):
    instance_document = documentos.objects.create(person_id=instance.id)
    with open('TEMPLATES/Files/file.pdf', 'rb') as document:
        instance_document.documento = File(document)
        instance_document.save()
    return


def uploadDocument(instance):
    document_type = TDocumento.objects.get(id=12)
    instance_document = documentos.objects.create(person_id=instance.id, tdocumento_id=document_type.id)
    with open('TMP/web/Ine_admins_cuenta_eje' + instance.username + '.pdf', 'rb') as document:
        instance_document.documento = File(document)
        instance_document.save()

    return


def uploadDocumentPersonalExterno(instance):
    document_type = TDocumento.objects.get(id=12)
    instance_document = documentos.objects.create(person_id=instance.id, tdocumento_id=document_type.id)
    with open('TMP/web/' + instance.username + '.pdf', 'rb') as document:
        instance_document.documento = File(document)
        instance_document.save()

    return


def get_instance_grupo_persona(admin_id: int) -> grupoPersona:
    return grupoPersona.objects.get_object_admin_company(person_id=admin_id)


def get_id_cuenta_eje(admin_id: int) -> int:
    return get_instance_grupo_persona(admin_id).get_only_id_empresa()


def get_person_and_empresa(admin_id: int) -> Dict:
    return get_instance_grupo_persona(admin_id).get_person_and_empresa()


def get_data_empresa(admin_id: int) -> Dict:
    return get_instance_grupo_persona(admin_id).get_empresa()


# (ChrGil 2021-11-08) No se respeta la variables definidas por backend
# (ChrGil 2021-11-08) La función es bastante grande
# (ChrGil 2021-11-08) No existen lineas en blanco que faciliten la lectura de otro desarrollador
def MovimientosTarjetaInntec(NumeroTarjeta, FechaDesde, FechaHasta, tipo_inntec):
    errores = []
    token = None
    queryset = None
    FechaHasta_guion = FechaHasta
    FechaDesde_guion = FechaDesde
    if tipo_inntec in ["Pruebas", "Produccion"]:
        if tipo_inntec == "Produccion":
            queryset = get_CardsAsignadas(token)
        if tipo_inntec == "Pruebas":
            token, _ = get_tokenInntecPruebas()
            queryset = get_CardsAsignadasPrueba(token)
        FechaActual = datetime.date.today()
        if FechaDesde == "" and FechaHasta == "":
            FechaHasta = FechaActual
            FechaDesde = FechaActual - relativedelta(months=3)
        FechaDesde = str(FechaDesde).replace("-", "")
        FechaHasta = str(FechaHasta).replace("-", "")
        tarjetaExisteLocal = False
        tarjetaExisteInntec = False
        TarjetaAsignadaPersonaExterna = None
        if tarjeta.objects.filter(tarjeta=NumeroTarjeta, rel_proveedor_id=1).exists():
            tarjetaExisteLocal = True
        for i in queryset:
            NumeroTarjetaInntec = i['NumeroTarjeta']
            if int(NumeroTarjeta) == int(NumeroTarjetaInntec):
                tarjetaId = i['TarjetaId']
                tarjetaExisteInntec = True
                break
            else:
                continue
        if FechaHasta > str(FechaActual).replace("-", ""):
            errores.append(
                {"field": "FechaHasta", "data": FechaHasta_guion,
                 "message": "FechaHasta no puede ser mayor que la fecha actual"})
        if tarjetaExisteLocal == False:
            errores.append({"field": "Tarjeta", "data": NumeroTarjeta,
                            "message": "Tarjeta Inntec no encontrada en base de datos Polipay"})
        else:
            if tarjeta.objects.filter(tarjeta=NumeroTarjeta).exists():
                TarjetaAsignadaPersonaExterna = True
            else:
                TarjetaAsignadaPersonaExterna = False
        if TarjetaAsignadaPersonaExterna == False:
            errores.append({"field": "Tarjeta", "data": NumeroTarjeta,
                            "message": "Tarjeta no ha sido asignada a persona externa"})
        if tarjetaExisteInntec == False:
            errores.append({"field": "Tarjeta", "data": NumeroTarjeta,
                            "message": "Tarjeta no encontrada en base de datos Inntec"})
        if FechaDesde > FechaHasta:
            errores.append(
                {"field": "FechaDesde", "data": FechaDesde_guion, "message": "FechaDesde no puede ser mayor que FechaHasta"})
        if errores:
            raise ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [errores]})
        else:
            queryMovimientosTarjetaInntec = None
            if tipo_inntec == "Produccion":
                queryMovimientosTarjetaInntec = get_MovimientosTarjetas(tarjetaId, FechaDesde, FechaHasta)
            if tipo_inntec == "Pruebas":
                queryMovimientosTarjetaInntec = get_MovimientosTarjetasPruebas(tarjetaId, FechaDesde, FechaHasta)
            return queryMovimientosTarjetaInntec

    else:
        errores.append({"field": "Tipo", "data": tipo_inntec,
                        "message": "tipo no reconocido"})
        MensajeError(error=errores)


def MovimientosCuenta(NumeroCuenta, FechaDesde, FechaHasta):
    errores = []
    if cuenta.objects.filter(cuenta=NumeroCuenta).exists():
        pass
    else:
        errores.append(
            {"field": "Cuenta", "data": NumeroCuenta, "message": "Esta cuenta no existe"})
    FechaActual = datetime.date.today()
    if FechaDesde == "" and FechaHasta == "":
        FechaHasta = FechaActual
        FechaDesde = FechaActual.replace(day=1) - relativedelta(months=3)
        FechaDesdeHora = str(FechaDesde) + " 00:00:00"
        FechaHastaHora = str(FechaHasta) + " 23:59:59"
        FechaDesde = datetime.datetime.strptime(FechaDesdeHora, "%Y-%m-%d %H:%M:%S")
        FechaHasta = datetime.datetime.strptime(FechaHastaHora, "%Y-%m-%d %H:%M:%S")
        return FechaDesde, FechaHasta
    if FechaDesde > FechaHasta:
        errores.append(
            {"field": "FechaDesde", "data": FechaDesde, "message": "FechaDesde no puede ser mayor que FechaHasta"})
    FechaActual = datetime.datetime.today().strftime('%Y%m%d')
    if FechaHasta.replace("-", "") > FechaActual:
        errores.append(
            {"field": "FechaHasta", "data": FechaHasta, "message": "FechaHasta no puede ser mayor que la fecha actual"})
    if errores:
        raise ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [errores]})
    else:
        FechaDesdeHora = FechaDesde + " 00:00:00"
        FechaHastaHora = FechaHasta + " 23:59:59"
        FechaDesde = datetime.datetime.strptime(FechaDesdeHora, "%Y-%m-%d %H:%M:%S")
        FechaHasta = datetime.datetime.strptime(FechaHastaHora, "%Y-%m-%d %H:%M:%S")
        return FechaDesde, FechaHasta


##Buscar saldo de tarjeta inntec
def SaldoTarjetaInntec(NumeroTarjeta):
    errores = []
    tarjetaId = None
    queryset = get_CardsAsignadas(token=None)
    TarjetaAsignadaPersonaExterna = None
    tarjetaExisteLocal = False
    tarjetaExisteInntec = False
    if tarjeta.objects.filter(tarjeta=NumeroTarjeta, rel_proveedor_id=1).exists():
        tarjetaExisteLocal = True
    for i in queryset:
        NumeroTarjetaInntec = i['NumeroTarjeta']
        if int(NumeroTarjeta) == int(NumeroTarjetaInntec):
            tarjetaId = i['TarjetaId']
            tarjetaExisteInntec = True
            break
        else:
            continue
    if tarjetaExisteLocal == False:
        errores.append({"field": "Tarjeta", "data": NumeroTarjeta,
                        "message": "Tarjeta Inntec no encontrada en base de datos Polipay"})
    else:
        if tarjeta.objects.filter(tarjeta=NumeroTarjeta).exists():
            TarjetaAsignadaPersonaExterna = True
        else:
            TarjetaAsignadaPersonaExterna = False
    if TarjetaAsignadaPersonaExterna == False:
        errores.append({"field": "Tarjeta", "data": NumeroTarjeta,
                        "message": "Tarjeta no ha sido asignada a persona externa"})
    if tarjetaExisteInntec == False:
        errores.append({"field": "Tarjeta", "data": NumeroTarjeta,
                        "message": "Tarjeta no encontrada en base de datos Inntec"})
    if errores:
        raise ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [errores]})
    else:
        saldosTarjeta = get_Saldos(tarjetaId)
        return saldosTarjeta


def SaldoTarjetaInntecPruebas(NumeroTarjeta):
    token, _ = get_tokenInntecPruebas()
    errores = []
    queryset = get_CardsAsignadasPrueba(token)
    TarjetaAsignadaPersonaExterna = None
    tarjetaExisteLocal = False
    tarjetaExisteInntec = False
    if tarjeta.objects.filter(tarjeta=NumeroTarjeta, rel_proveedor_id=1).exists():
        tarjetaExisteLocal = True
    for i in queryset:
        NumeroTarjetaInntec = i['NumeroTarjeta']
        if int(NumeroTarjeta) == int(NumeroTarjetaInntec):
            tarjetaId = i['TarjetaId']
            tarjetaExisteInntec = True
            break
        else:
            continue
    if tarjetaExisteLocal == False:
        errores.append({"field": "Tarjeta", "data": NumeroTarjeta,
                        "message": "Tarjeta Inntec no encontrada en base de datos Polipay"})
    else:
        if tarjeta.objects.filter(tarjeta=NumeroTarjeta).exists():
            TarjetaAsignadaPersonaExterna = True
        else:
            TarjetaAsignadaPersonaExterna = False
    if TarjetaAsignadaPersonaExterna == False:
        errores.append({"field": "Tarjeta", "data": NumeroTarjeta,
                        "message": "Tarjeta no ha sido asignada a persona externa"})
    if tarjetaExisteInntec == False:
        errores.append({"field": "Tarjeta", "data": NumeroTarjeta,
                        "message": "Tarjeta no encontrada en base de datos Inntec"})
    if errores:
        raise ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [errores]})
    else:
        saldosTarjeta = get_SaldosPrueba(tarjetaId)
        return saldosTarjeta


def addAdministrative(company_id: int, instance: persona):
    grupoPersona.objects.create(
        empresa_id=company_id,
        person_id=instance.get_only_id(),
        nombre_grupo="Administrativo",
        relacion_grupo_id=3,
        is_admin=True
    )
    # AdminCueEjeAddGroup(instance=instance)


# (AAF 2021-11-30) Activa la persona dada
def Active_Person(person_id):
    try:
        persona.objects.filter(id=person_id).update(state=True)
        return True
    except:
        return False


# (JM 2021/12/06) Generar codigo para llamada
def CodeCall(email):
    code = random.randrange(1000, 9999, 3)
    cache.set(email, str(code), TIME)
    return cache.get(email)


# (JM 2021/12/06) separa el codigo por comas y realiza la llamada
def createCodeCallCache(instance):
    code = CodeCall(instance.email)
    code_call = []
    for number in str(code):
        comma_number = ",,,,,," + number
        code_call.append(comma_number)
    SendCallCode(code_call, instance)
    return


def MessageOK(mensaje, data, field):
    status = {
        "code": [
            201
        ],
        "status": [
            "OK"
        ],
        "detail": [
            {
                "field": field,
                "data": data,
                "message": mensaje
            }
        ]
    }
    return status

def MessageOkList(Lis_dic):
    status = {
    "code": [
        201
    ],
    "status": [
        "OK"
    ],
    "detail": Lis_dic
    }
    return status



###############################################################
def filter_ext_client(validated_data):
    centro_costos = validated_data['centro_costos_id']
    if 'client_name' in validated_data:
        client_name = validated_data['client_name']
    if 'cuenta' in validated_data:
        count = validated_data['cuenta']
    if 'clabe' in validated_data:
        clabe = validated_data['clabe']
    if 'estado' in validated_data:
        estado = validated_data['estado']
    if 'fecha_inicio' in validated_data:
        fecha_inicio = validated_data['fecha_inicio']
    if 'fecha_fin' in validated_data:
        fecha_fin = validated_data['fecha_fin']

    if clabe:  # FILTRO CLABE
        id_clabe_persona = cuenta.objects.values('persona_cuenta_id').filter(cuentaclave=str(clabe))
        id_clabe = id_clabe_persona[0]
        clientes_externos = grupoPersona.objects.values('person_id').filter(empresa_id=int(centro_costos),
                                                                            relacion_grupo_id__in=[11, 9],
                                                                            person_id=int(
                                                                                id_clabe['persona_cuenta_id']))
    if count:  # FILTRO CUENTA
        id_cuenta_persona = cuenta.objects.values('persona_cuenta_id').filter(cuenta=str(count))
        id_count = id_cuenta_persona[0]
        clientes_externos = grupoPersona.objects.values('person_id').filter(empresa_id=int(centro_costos),
                                                                            relacion_grupo_id=int(11), person_id=int(
                id_count['persona_cuenta_id']))
    if clabe is None and count is None:
        clientes_externos = grupoPersona.objects.values('person_id').filter(
            empresa_id=int(centro_costos),
            relacion_grupo_id__in=[11, 9],
        ).order_by('-person__date_joined')
    client_list = []

    for i in clientes_externos:

        id_cliente = int(i['person_id'])
        if client_name:  # FILTRO POR NOMBRE DEL CLIENTE
            sol_cliente = Solicitudes.objects.filter(personaSolicitud_id=id_cliente,
                                                     personaSolicitud_id__username=str(client_name))

        if estado:  # FILTRO POR ESTADO DE SOLICITUD
            sol_cliente = Solicitudes.objects.filter(
                personaSolicitud_id=id_cliente, estado_id__nombreEdo=str(estado))

        if fecha_inicio and fecha_fin:  # FILTRO FECHA

            date_inicio = str(fecha_inicio) + " 00:00:00"
            date_inicio = datetime.datetime.strptime(str(date_inicio), '%Y-%m-%d %H:%M:%S')
            date_fin = str(fecha_fin) + " 23:59:59"
            date_fin = datetime.datetime.strptime(str(date_fin), '%Y-%m-%d %H:%M:%S')
            sol_cliente = Solicitudes.objects.filter(personaSolicitud_id=id_cliente,
                                                     fechaSolicitud__range=[date_inicio, date_fin])

        if client_name is None and estado is None and fecha_inicio is None and fecha_fin is None:  # SIN FILTRO
            sol_cliente = Solicitudes.objects.filter(personaSolicitud_id=id_cliente)

        cuenta_cliente = cuenta.objects.get(persona_cuenta_id=id_cliente)

        for sol in sol_cliente:
            dict_client = {}

            dict_client['id_persona_CC'] = int(sol.personaSolicitud_id)
            dict_client['id_tabla_solicitud'] = int(sol.id)
            dict_client['cliente'] = str(sol.personaSolicitud.name)
            dict_client['estado'] = str(sol.estado.nombreEdo)
            dict_client['cuenta'] = str(cuenta_cliente.cuenta)
            dict_client['clabe'] = str(cuenta_cliente.cuentaclave)
            dict_client['fecha_captura'] = str(sol.fechaSolicitud)
            dict_client['tipo_persona_id'] = str(sol.personaSolicitud.tipo_persona_id)
            client_list.append(dict_client)
    return client_list


def ext_client(validated_data):
    cuenta_eje = validated_data['centro_costos_id']
    message_not_count = {
        "code": [400],
        "status": "ERROR",
        "detail": [
            {
                "data": "ERROR",
                "message": "No existe cuenta para los clientes externos de este centro de costos",
            }
        ]
    }
    centro_costos = grupoPersona.objects.values('person_id').filter(empresa_id=cuenta_eje, relacion_grupo_id=5)
    list_CC = []
    # print("centro de costos",centro_costos[0])
    for i in centro_costos:
        list_CC.append(i["person_id"])

    clientes_externos = grupoPersona.objects.values('person_id').filter(empresa_id__in=list_CC, relacion_grupo_id__in=[11, 9])
    # print("clientes_externos",clientes_externos)
    clientes_activos = persona.objects.values('id').filter(id__in=clientes_externos, state=True)
    # print("clientes_activos",clientes_activos)
    client_list = []

    for i in clientes_activos:
        # print("cliente", i)
        id_cliente = int(i['id'])
        sol_cliente = Solicitudes.objects.filter(personaSolicitud_id=id_cliente)
        try:
            cuenta_cliente = cuenta.objects.get(persona_cuenta_id=id_cliente)
        except Exception as e:
            raise ValidationError(message_not_count)
        for sol in sol_cliente:
            print("solicitud cliente", sol)
            dict_client = {}

            dict_client['id_persona_CC'] = int(sol.personaSolicitud_id)
            dict_client['id_tabla_solicitud'] = int(sol.id)
            dict_client['cliente'] = str(sol.personaSolicitud.name)
            dict_client['estado'] = str(sol.estado.nombreEdo)
            dict_client['cuenta'] = str(cuenta_cliente.cuenta)
            dict_client['clabe'] = str(cuenta_cliente.cuentaclave)
            dict_client['fecha_captura'] = str(sol.fechaSolicitud)
            dict_client['tipo_cliente'] = str(sol.personaSolicitud.tipo_persona_id)
            print(dict_client)
            client_list.append(dict_client)
    return client_list


def sol_ext_client(validated_data):
    centro_costos_id = validated_data['centro_costos_id']

    client_list = []

    sol_cliente = Solicitudes.objects.filter(
        personaSolicitud_id=centro_costos_id,
        tipoSolicitud_id__in=[1,22]).filter(
        Q(estado_id=1) |
        Q(estado_id=2) |
        Q(estado_id=4))

    for sol in sol_cliente:
        dict_client = {}
        dict_client['id_sol'] = sol.id
        dict_client['intentos'] = sol.intentos
        dict_client['id_cliente'] = sol.personaSolicitud_id
        dict_client['cliente'] = sol.personaSolicitud.name
        dict_client['t_persona'] = sol.personaSolicitud.tipo_persona_id
        dict_client['estado'] = sol.estado.nombreEdo
        dict_client['tipo'] = sol.tipoSolicitud.nombreSol
        dict_client['fecha'] = sol.fechaSolicitud
        client_list.append(dict_client)

    return client_list


def check_inntec_card_balance(card_number):
    errores = []
    token = None
    queryset = get_CardsAsignadas(token)
    TarjetaAsignadaPersonaExterna = None
    # tarjetaExisteLocal = False
    tarjetaExisteInntec = False
    if tarjeta.objects.filter(tarjeta=card_number, rel_proveedor_id=1).exists():
        tarjetaExisteLocal = True
    for i in queryset:
        inntec_number_card = i['NumeroTarjeta']
        if int(card_number) == int(inntec_number_card):
            tarjetaId = i['TarjetaId']
            tarjetaExisteInntec = True
            break
        else:
            continue
    # if tarjetaExisteLocal == False:
    #     errores.append({"field": "NumeroTarjeta", "data": card_number,
    #                     "message": "Tarjeta Inntec no encontrada en base de datos Polipay"})
    # else:
    #     if tarjeta.objects.filter(tarjeta=card_number, status="00").exists():
    #         TarjetaAsignadaPersonaExterna = True
    #     else:
    #         TarjetaAsignadaPersonaExterna = False
    if TarjetaAsignadaPersonaExterna == False:
        errores.append({"field": "NumeroTarjeta", "data": card_number,
                        "message": "Tarjeta no ha sido asignada a persona externa"})
    if tarjetaExisteInntec == False:
        errores.append({"field": "NumeroTarjeta", "data": card_number,
                        "message": "Tarjeta no encontrada en base de datos Inntec"})
    if errores:
        raise ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [errores]})
    else:
        saldosTarjeta = get_Saldos(tarjetaId)
        return saldosTarjeta


from apps.users.models import tarjeta
from polipaynewConfig.inntec import *


# Prueba de asignar a beneficiario
def TarjetaBeneficiario(Tarjeta, cuenta_eje_id, beneficiario):
    instanceTarjeta = tarjeta.objects.filter(tarjeta=Tarjeta, clientePrincipal_id=cuenta_eje_id,
                                             rel_proveedor_id=1).last()
    if instanceTarjeta == False:
        raise ValidationError({"code": ["400"], "status": ["error"],
                               "detail": [{"message": "No se pudo asignar la tarjeta"},
                                          {"field": "tarjeta", "message": "Tarjeta no encontrada",
                                           "data": Tarjeta}]})
    if instanceTarjeta.status != "04":
        raise ValidationError({"code": ["400"], "status": ["error"],
                               "detail": [{"message": "No se pudo asignar la tarjeta"},
                                          {"field": "tarjeta", "message": "Tarjeta ya asignada",
                                           "data": Tarjeta}]})

    instance_beneficiario = persona.objects.get(id=beneficiario)
    cuenta_id = cuenta.objects.get(persona_cuenta_id=beneficiario).get_only_id()

    apellidos = SepararApellidos(instanceP=instance_beneficiario)
    # Nuevo
    if instanceTarjeta.ClaveEmpleado == "":
        nueva_clave = ClaveEmpleadoIndividualPrueba(numero_tarjeta=instanceTarjeta.tarjeta)
        instanceTarjeta.ClaveEmpleado = nueva_clave
        instanceTarjeta.save()
    ###
    diccionario = [{
        "TarjetaId": instanceTarjeta.TarjetaId,
        "ClienteId": "C000022",
        "ProductoId": 56,
        "Nombre": instance_beneficiario.name,
        "ApellidoPaterno": "Paterno",
        "ApellidoMaterno": "Materno",
        "NombreCorto": "",
        "RFC": "AAAA010101AAA",
        "CURP": "",
        "CURP": "",
        "NSS": "",
        "Direccion": "",
        "NumeroTelefonoMovil": "9999999999",
        "NumeroTelefonoCasa": "9999999999",
        "NumeroTelefonoTrabajo": "",
        "Estado": "",
        "Municipio": "",
        "Ciudad": "",
        "Colonia": "",
        "CorreoElectronico": instance_beneficiario.email,
        "CodigoPostal": "",
        "MontoInicial": "0.0",
        "ClaveEstado": "",
        "NumeroEmpleado": instanceTarjeta.ClaveEmpleado,
        "CodigoRetenedora": ""
    }]
    print(diccionario)
    instanceTarjeta.status = "04"
    instanceTarjeta.is_active = True
    instanceTarjeta.cuenta_id = cuenta_id
    instanceTarjeta.save()
    AsignarTarjetaPersonaExternaInntecPrueba(diccionario)
    return


# def asignar_tarjeta_beneficiario(Tarjeta, cuenta_eje_id, beneficiario):
#     instanceTarjeta = tarjeta.objects.filter(tarjeta=Tarjeta, clientePrincipal_id=cuenta_eje_id,
#                                              rel_proveedor_id=1).last()
#     if instanceTarjeta == False:
#         raise ValidationError({"code": ["400"], "status": ["error"],
#                                "detail": [{"message": "No se pudo asignar la tarjeta"},
#                                           {"field": "tarjeta", "message": "Tarjeta no encontrada",
#                                            "data": Tarjeta}]})
#     if instanceTarjeta.status != "04":
#         raise ValidationError({"code": ["400"], "status": ["error"],
#                                "detail": [{"message": "No se pudo asignar la tarjeta"},
#                                           {"field": "tarjeta", "message": "Tarjeta ya asignada",
#                                            "data": Tarjeta}]})
#
#     instance_beneficiario = persona.objects.get(id=beneficiario)
#     cuenta_id = cuenta.objects.get(persona_cuenta_id=beneficiario).get_only_id()
#
#     apellidos = SepararApellidos(instanceP=instance_beneficiario)
#     # Nuevo ######
#     if instanceTarjeta.ClaveEmpleado == "":
#         nueva_clave = ClaveEmpleadoIndividualPrueba(numero_tarjeta=instanceTarjeta.tarjeta)
#         instanceTarjeta.ClaveEmpleado = nueva_clave
#         instanceTarjeta.save()
#     ###
#     diccionario = [{
#         "TarjetaId": instanceTarjeta.TarjetaId,
#         "ClienteId": "C000682",
#         "ProductoId": 56,
#         "Nombre": instance_beneficiario.name,
#         "ApellidoPaterno": "Colocar apellidos",  ##############
#         "ApellidoMaterno": "Colocar apellidos",  ###############
#         "NombreCorto": "",
#         "RFC": "AAAA010101AAA",
#         "CURP": "",
#         "CURP": "",
#         "NSS": "",
#         "Direccion": "",
#         "NumeroTelefonoMovil": "9999999999",
#         "NumeroTelefonoCasa": "9999999999",
#         "NumeroTelefonoTrabajo": "",
#         "Estado": "",
#         "Municipio": "",
#         "Ciudad": "",
#         "Colonia": "",
#         "CorreoElectronico": instance_beneficiario.email,
#         "CodigoPostal": "",
#         "MontoInicial": "0.0",
#         "ClaveEstado": "",
#         "NumeroEmpleado": instanceTarjeta.ClaveEmpleado,
#         "CodigoRetenedora": ""
#     }]
#     instanceTarjeta.status = "04"
#     instanceTarjeta.is_active = True
#     instanceTarjeta.cuenta_id = cuenta_id
#     instanceTarjeta.save()
#     AsignarTarjetaPersonaExternaInntec(diccionario)  # produccion de inntec
#     return


def create_account(clabe: str, idPersona: int, idProducto: int):
    cta = clabe[7:17]
    objCuenta = cuenta(
        cuenta=cta,
        is_active=True,
        persona_cuenta_id=idPersona,
        cuentaclave=clabe,
        rel_cuenta_prod_id=idProducto
    )
    objCuenta.save()
    return objCuenta


def separar_apellidos(last_name: str):
    paterno = 'NA'
    materno = 'NA'

    if "*" in last_name:
        first, last = last_name.split("*")
        return first, last
    return paterno, materno


# Prueba de asignar a beneficiario
def tarjeta_beneficiario(
        numero_tarjeta_beneficiario: str,
        cuenta_eje_id: int,
        beneficiario_id: int,
        prod: bool = False
):
    instance_tarjeta = tarjeta.objects.filter(
        tarjeta=numero_tarjeta_beneficiario,
        clientePrincipal_id=cuenta_eje_id,
        rel_proveedor_id=1).last()

    data_beneficiario = persona.objects.filter(id=beneficiario_id).values('name', 'last_name', 'email', 'rfc').first()
    cuenta_id = cuenta.objects.get(persona_cuenta_id=beneficiario_id).get_only_id()

    if instance_tarjeta is None:
        raise CardNotFound("Tarjeta no valida o no existe")

    if instance_tarjeta.status == "00":
        if instance_tarjeta.cuenta_id is None:
            instance_tarjeta.is_active = True
            instance_tarjeta.cuenta_id = cuenta_id
            instance_tarjeta.save()
            return True

        raise FailAssignedCard("No se pudo asignar la tarjeta. La Tarjeta ya fue asignada a otro beneficiario")

    if instance_tarjeta.ClaveEmpleado == "":
        nueva_clave = None

        if not prod:
            nueva_clave = ClaveEmpleadoIndividualPrueba()
        if prod:
            nueva_clave = ClaveEmpleado()

        instance_tarjeta.ClaveEmpleado = nueva_clave
        instance_tarjeta.save()

    paterno, manterno = separar_apellidos(data_beneficiario.get('last_name'))
    lista: List[Dict[str, Any]] = [
        {
            "TarjetaId": instance_tarjeta.TarjetaId,
            "ClienteId": "C000682" if prod else "C000022",
            "ProductoId": 56,
            "Nombre": data_beneficiario.get('name'),
            "ApellidoPaterno": paterno if paterno != '' else 'NA',
            "ApellidoMaterno": manterno if manterno != '' else 'NA',
            "NombreCorto": "",
            "RFC": data_beneficiario.get('rfc'),
            "CURP": "",
            "NSS": "",
            "Direccion": "",
            "NumeroTelefonoMovil": "9999999999",
            "NumeroTelefonoCasa": "9999999999",
            "NumeroTelefonoTrabajo": "",
            "Estado": "",
            "Municipio": "",
            "Ciudad": "",
            "Colonia": "",
            "CorreoElectronico": data_beneficiario.get('email'),
            "CodigoPostal": "",
            "MontoInicial": "0.0",
            "ClaveEstado": "",
            "NumeroEmpleado": instance_tarjeta.ClaveEmpleado,
            "CodigoRetenedora": ""
        }
    ]

    instance_tarjeta.status = "00"
    instance_tarjeta.is_active = True
    instance_tarjeta.cuenta_id = cuenta_id
    instance_tarjeta.save()

    if prod:
        # (ChrGil 2022-01-07) Producción
        AsignarTarjetaPersonaExternaInntec(lista)

    if not prod:
        print("pruebas")
        # (ChrGil 2022-01-07) Pruebas
        # AsignarTarjetaPersonaExternaInntecPrueba(lista)
    return


def concentrateFile(namefile: string, query: query, fecha_inicio: datetime, fecha_fin: datetime):
    workbook = load_workbook(filename="TEMPLATES/web/" + namefile + ".xlsx")
    sheet = workbook.active
    arial_font = Font(u'Arial', bold=True, size=11)
    red_text = Font(color="00FF0000")
    black_text = Font(color="00000000")
    fecha_inicio = fecha_inicio
    fecha_fin = fecha_fin
    fechactual = datetime.date.today()
    sheet['C7'] = fechactual
    sheet['C7'].alignment = Alignment(horizontal="left", vertical="center")
    fila = 19
    ingresos = 0
    egresos = 0
    for tupla in query:
        sheet["B" + str(fila)] = tupla['cuentaClaveRel']  # cuenta relacionada
        sheet['B' + str(fila)].alignment = Alignment(horizontal="left")
        sheet["C" + str(fila)] = tupla['cuenta_emisor']  # cuenta emisor
        sheet['C' + str(fila)].alignment = Alignment(horizontal="left")
        sheet["D" + str(fila)] = tupla['cuenta_emisor']  # clave emisor
        sheet['D' + str(fila)].alignment = Alignment(horizontal="left")
        sheet["E" + str(fila)] = tupla['cta_beneficiario']  # cuenta receptor
        sheet['E' + str(fila)].alignment = Alignment(horizontal="left")
        sheet["F" + str(fila)] = tupla['cta_beneficiario']  # clave receptor
        sheet['F' + str(fila)].alignment = Alignment(horizontal="left")
        sheet["G" + str(fila)] = tupla['fecha_creacion']  # fecha operacion
        sheet['G' + str(fila)].alignment = Alignment(horizontal="left")
        amount = f"{tupla['monto']:.2f}"
        if tupla['cuentaRel'] == tupla['cuenta_emisor'] or tupla['cuentaClaveRel'] == tupla['cuenta_emisor']:
            egresos += tupla['monto']
            sheet["H" + str(fila)].font = red_text
        if tupla['cuentaRel'] == tupla['cta_beneficiario'] or tupla['cuentaClaveRel'] == tupla['cta_beneficiario']:
            ingresos += tupla['monto']
            sheet["H" + str(fila)].font = black_text
        sheet["H" + str(fila)] = '$' + amount  # monto
        sheet['H' + str(fila)].alignment = Alignment(horizontal="left")
        sheet["I" + str(fila)] = tupla['referencia_numerica']  # numero de referencia
        sheet['I' + str(fila)].alignment = Alignment(horizontal="left")
        sheet["J" + str(fila)] = tupla['clave_rastreo']  # clave_rastreo
        sheet['J' + str(fila)].alignment = Alignment(horizontal="left")
        sheet["K" + str(fila)] = tupla['id']  # folio transferencia
        sheet['K' + str(fila)].alignment = Alignment(horizontal="left")
        sheet["L" + str(fila)] = tupla['concepto_pago']  # folio transferencia
        sheet['L' + str(fila)].alignment = Alignment(horizontal="left")
        fila += 1

    sheet['C9'] = '$' + f"{ingresos:.2f}"
    sheet['C10'] = '$' + f"{egresos:.2f}"
    workbook.save(filename="TMP/web/Estado_Cuentas/Excel/Reporte-Concentrado.xlsx")
    return workbook


def ActivaCuenta(idPersona: int):
    try:
        accounts = cuenta.objects.filter(persona_cuenta_id=idPersona)
        for account in accounts:
            account.is_active = True
            account.save()
        return accounts
    except:
        raise Exception("error al activa cuenta")

# (Jose 2022-01-25) Funcion para eliminar los pdf o excel creados en base64
def EliminarArchivo(dato_unico,ruta,tipo):
    # dato_unico = un valor unico para que no se sobre escriba el archivo
    # tipo = pdf o excel ====== .pdf  .xlsx etc
    # ruta = la ruta en donde se guardo el archivo
    try:
        os.remove(ruta + dato_unico + "." + tipo)
        return True
    except:
        pass


def MovimientosTarjetaInntecClienteExterno(NumeroTarjeta, FechaDesde, FechaHasta, tipo_inntec):
    errores = []
    token = None
    queryset = None
    FechaHasta_guion = FechaHasta
    FechaDesde_guion = FechaDesde
    if tipo_inntec in ["Pruebas", "Produccion"]:
        if tipo_inntec == "Produccion":
            queryset = get_CardsAsignadas(token)
        if tipo_inntec == "Pruebas":
            token, _ = get_tokenInntecPruebas()
            queryset = get_CardsAsignadasPrueba(token)
        FechaActual = datetime.date.today()
        if FechaDesde == "Null" and FechaHasta == "Null":
            FechaHasta = FechaActual
            FechaDesde = FechaActual - relativedelta(months=3)
        FechaDesde = str(FechaDesde).replace("-", "")
        FechaHasta = str(FechaHasta).replace("-", "")
        tarjetaExisteLocal = False
        tarjetaExisteInntec = False
        TarjetaAsignadaPersonaExterna = None
        if tarjeta.objects.filter(tarjeta=NumeroTarjeta, rel_proveedor_id=1).exists():
            tarjetaExisteLocal = True
        for i in queryset:
            NumeroTarjetaInntec = i['NumeroTarjeta']
            if int(NumeroTarjeta) == int(NumeroTarjetaInntec):
                tarjetaId = i['TarjetaId']
                tarjetaExisteInntec = True
                break
            else:
                continue
        FechaActual = str(FechaActual).replace("-", "")
        if int(FechaHasta) > int(FechaActual):
            errores.append(
                {"field": "FechaHasta", "data": FechaHasta_guion,
                 "message": "FechaHasta no puede ser mayor que la fecha actual"})
        if tarjetaExisteLocal == False:
            errores.append({"field": "Tarjeta", "data": NumeroTarjeta,
                            "message": "Tarjeta Inntec no encontrada en base de datos Polipay"})
        else:
            if tarjeta.objects.filter(tarjeta=NumeroTarjeta, status="00").exists():
                TarjetaAsignadaPersonaExterna = True
            else:
                TarjetaAsignadaPersonaExterna = False
        if TarjetaAsignadaPersonaExterna == False:
            errores.append({"field": "Tarjeta", "data": NumeroTarjeta,
                            "message": "Tarjeta no ha sido asignada a persona externa"})
        if tarjetaExisteInntec == False:
            errores.append({"field": "Tarjeta", "data": NumeroTarjeta,
                            "message": "Tarjeta no encontrada en base de datos Inntec"})
        if int(FechaDesde) > int(FechaHasta):
            errores.append(
                {"field": "FechaDesde", "data": FechaDesde_guion,
                 "message": "FechaDesde no puede ser mayor que FechaHasta"})
        MensajeError(error=errores)
        queryMovimientosTarjetaInntec = None
        if tipo_inntec == "Produccion":
            queryMovimientosTarjetaInntec = get_MovimientosTarjetas(tarjetaId, FechaDesde, FechaHasta)
        if tipo_inntec == "Pruebas":
            queryMovimientosTarjetaInntec = get_MovimientosTarjetasPruebas(tarjetaId, FechaDesde, FechaHasta)
        return queryMovimientosTarjetaInntec

    else:
        errores.append({"field": "Tipo", "data": tipo_inntec,
                        "message": "tipo no reconocido"})
        MensajeError(error=errores)


def MovimientosCuentaClienteExternoFisico(NumeroCuenta, FechaDesde, FechaHasta):
    errores = []
    if cuenta.objects.filter(cuenta=NumeroCuenta).exists():
        pass
    else:
        errores.append(
            {"field": "Cuenta", "data": NumeroCuenta, "message": "Esta cuenta no existe"})
    FechaActual = datetime.date.today()
    if FechaDesde == "Null" and FechaHasta == "Null":
        FechaHasta = FechaActual
        FechaDesde = FechaActual.replace(day=1) - relativedelta(months=3)
        FechaDesdeHora = str(FechaDesde) + " 00:00:00"
        FechaHastaHora = str(FechaHasta) + " 23:59:59"
        FechaDesde = datetime.datetime.strptime(FechaDesdeHora, "%Y-%m-%d %H:%M:%S")
        FechaHasta = datetime.datetime.strptime(FechaHastaHora, "%Y-%m-%d %H:%M:%S")
        return FechaDesde, FechaHasta
    if FechaDesde > FechaHasta:
        errores.append(
            {"field": "FechaDesde", "data": FechaDesde, "message": "FechaDesde no puede ser mayor que FechaHasta"})
    FechaActual = datetime.datetime.today().strftime('%Y%m%d')
    if FechaHasta.replace("-", "") > FechaActual:
        errores.append(
            {"field": "FechaHasta", "data": FechaHasta, "message": "FechaHasta no puede ser mayor que la fecha actual"})
    MensajeError(error=errores)
    FechaDesdeHora = FechaDesde + " 00:00:00"
    FechaHastaHora = FechaHasta + " 23:59:59"
    FechaDesde = datetime.datetime.strptime(FechaDesdeHora, "%Y-%m-%d %H:%M:%S")
    FechaHasta = datetime.datetime.strptime(FechaHastaHora, "%Y-%m-%d %H:%M:%S")
    return FechaDesde, FechaHasta
