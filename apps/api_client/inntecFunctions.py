import requests
import itertools
import json
from django.conf import settings
from rest_framework import serializers
from apps.users.models import tarjeta
# Llaves de pruebas para Inntec
from polipaynewConfig.settings import CLIENT_ID_Test, CLIENT_SECRET_Test, USERNAME_Test, PASSWORD_Test, URL_POLIPAY_Test
"""
    A continuación, las siguientes dos funciones corresponden a info que se manjea con credenciales para la API de Inntec
"""
# Polipay data
URL_PROD = settings.URL_POLIPAY
clientid_PROD = settings.CLIENT_ID
clientsecret_PROD = settings.CLIENT_SECRET
username_PROD = settings.USERNAME
password_PROD = settings.PASSWORD
# Llaves de pruebas para Inntec
#URL_TEST = settings.URL_POLIPAY_Test
#clientid_TEST = settings.CLIENT_ID_Test
#clientsecret_TEST = settings.CLIENT_SECRET_Test
#username_TEST = settings.USERNAME_Test
#password_TEST = settings.PASSWORD_Test


def tipo_movimiento(movimiento):
    cargo = ['Comisiones Tarjeta', 'COMPRA POS', 'Ecommerce', 'Consulta Saldo', 'Retiro ATM', 'Compra con CashBack',
             'Contactless Saldos Internos', 'Compra POS (TPV/Ecomerce/Contactless)', 'Retiro en AMT',
             'Consulta de Saldo en ATM',
             'Compra con CashBack', 'Transferencia de saldo a Usuario', 'Decremento o Reverso', 'Envio de SPEI Tarjeta']

    abono = ['Devolucion por Vencimiento', 'Devolución', 'Anulación de Transacción Ecomerce',
             'Anulación de Transacción POS', 'Recepcion de SPEI Tarjeta',
             'Reverso Spei out', 'Ajuste de Aclaración', 'Recarga', 'Transferencia de saldo de Usuario',
             'Decremento MC Cargo COMPENSADA']

    if movimiento in cargo:
        return False
    if movimiento in abono:
        return True


def get_historial(tarjeta, date_from, date_end):
    token, _ = get_token_prod()
    url_account = URL_PROD + '/api/TarjetasMC/Movimientos/' + tarjeta + '/' + date_from + '/' + date_end
    headers = {'Authorization': 'Bearer ' + token}
    response = requests.get(url=url_account, headers=headers)
    response_json = response.json()
    return response_json, response.status_code


def get_token_prod():
    try:
        url_token = URL_PROD + 'token'
        data = {'grant_type': 'password', 'username': username_PROD, 'password': password_PROD,
                'client_id': clientid_PROD,
                'client_secret': clientsecret_PROD}
        headers = {'accept': 'application/json', 'content-type': 'application/x-www-form-urlencoded'}
        response = requests.post(url=url_token, data=data, headers=headers)
        response_json = response.json()
        token = response_json['access_token']
        expires = response_json['.expires']
        return token, expires
    except:
        return None


###----------------------Funciones de inntec para asignar tarjetas------------------------------------------###


def get_token_test():
    URL = "http://desarrolloinntecmp.azurewebsites.net/InntecAPI/"
    try:
        url_token = URL + 'token'
        data = {'grant_type': 'password', 'username': USERNAME_Test, 'password': PASSWORD_Test,
                'client_id': CLIENT_ID_Test,
                'client_secret': CLIENT_SECRET_Test}
        headers = {'accept': 'application/json', 'content-type': 'application/x-www-form-urlencoded'}
        response = requests.post(url=url_token, data=data, headers=headers)
        response_json = response.json()
        token = response_json['access_token']
        expires = response_json['.expires']
        return token, expires
    except:
        return None


### Separar apellidos para inntec
def separar_apellidos(instanceP):
    if "*" in instanceP.last_name:
        first, last = instanceP.last_name.split("*")
        return first, last
    else:
        first, last = instanceP.last_name.split()
        return first, last


#### Gerar Clave empleado para inntec despues del 6000
def clave_empleado():
    token, _ = get_token_prod()
    queryset = get_CardsAsignadas(token)
    queryset_db = tarjeta.objects.all()
    claveEmpleados = []
    for claveEmpleado in queryset:
        clave_empleados = ''.join(
            filter(str.isdigit, claveEmpleado['ClaveEmpleado']))  # Omite todas las que tengan una letra
        claveEmpleados.append(str(clave_empleados))
    for claveEmpleado in queryset_db:
        try:
            clave_empleados = ''.join(
                filter(str.isdigit, claveEmpleado.ClaveEmpleado))  # Omite todas las que tengan una letra
            claveEmpleados.append(str(clave_empleados))
        except:
            continue
    print(claveEmpleados)
    for claveEmpleado10000 in itertools.count(start=10000):
        if str(claveEmpleado10000) not in claveEmpleados:
            return claveEmpleado10000


#### Gerar Clave empleado para inntec despues del 10000 Prueba
def ClaveEmpleadoPrueba():
    token, _ = get_token_test()
    queryset = get_CardsAsignadasPrueba(token)
    queryset_db = tarjeta.objects.all()
    claveEmpleados = []
    for claveEmpleado in queryset:
        clave_empleados = ''.join(
            filter(str.isdigit, claveEmpleado['ClaveEmpleado']))  # Omite todas las que tengan una letra
        claveEmpleados.append(str(clave_empleados))
    for claveEmpleado in queryset_db:
        try:
            clave_empleados = ''.join(
                filter(str.isdigit, claveEmpleado.ClaveEmpleado))  # Omite todas las que tengan una letra
            claveEmpleados.append(str(clave_empleados))
        except:
            continue
    for claveEmpleado10000 in itertools.count(start=10000):
        if str(claveEmpleado10000) not in claveEmpleados:
            return claveEmpleado10000


## Tarjetas ya asignadas NOTA: clave de empleado y de producto cambian segun entorno de ejecución (pruebas/produccion)
def get_CardsAsignadas(token):
    URL = "https://www.inntecmp.com.mx/InntecAPI/"
    try:
        token, _ = get_token_prod()
        url_account = URL + 'api/Id/ReportesTarjetaMC/Tarjetas/C000682/56'
        headers = {'Authorization': 'Bearer ' + token}
        response = requests.get(url=url_account, headers=headers)
        response_json = response.json()
        return response_json
    except:
        return None


## Tarjetas ya asignadas Prueba
def get_CardsAsignadasPrueba(token):
    URL = "http://desarrolloinntecmp.azurewebsites.net/InntecAPI/"
    try:
        url_account = URL + 'api/Id/ReportesTarjetaMC/Tarjetas/C000022/56'
        headers = {'Authorization': 'Bearer ' + token}
        response = requests.get(url=url_account, headers=headers)
        response_json = response.json()
        return response_json
    except:
        return None


# Asignar Tarjetas de inntec a persona externa por medio de cuenta eje (Produccion)
def AsignarTarjetaPersonaExternaInntec(diccionario):
    URL = "https://www.inntecmp.com.mx/InntecAPI/api/Id/TarjetasMC/Asignaciones/"
    token, _ = get_token_prod()
    url_account = URL
    headers = {'Authorization': 'Bearer ' + token}
    response = requests.post(url=url_account, json=diccionario, headers=headers)
    response_json = response.json()
    if int(response_json["EstatusProceso"]) != 1:
        status = response_json["EstatusProceso"]
        mensaje = CategoriasInntecError(str(status))
        raise serializers.ValidationError({"code": ["400"], "status": ["error"],
                                           "detail": [{"message": "No se pudo dar de alta la tarjeta"},
                                                      {"field": "", "message": mensaje,
                                                       "data": ""}]})
    return response_json


# Asignar Tarjetas de inntec a persona externa por medio de cuenta eje (Pruebas)
def AsignarTarjetaPersonaExternaInntecPrueba(diccionario):
    URL = "http://desarrolloinntecmp.azurewebsites.net/InntecAPI/api/Id/TarjetasMC/Asignaciones/"
    token, _ = get_token_test()
    url_account = URL
    headers = {'Authorization': 'Bearer ' + token}
    response = requests.post(url=url_account, json=diccionario, headers=headers)
    response_json = response.json()
    if int(response_json["EstatusProceso"]) != 1:
        status = response_json["EstatusProceso"]
        mensaje = CategoriasInntecError(str(status))
        raise serializers.ValidationError({"code": ["400"], "status": ["error"],
                                           "detail": [{"message": "No se pudo dar de alta la tarjeta"},
                                                      {"field": "", "message": mensaje,
                                                       "data": ""}]})
    return response_json


### Categorias inntec
def CategoriasInntecError(status):
    codigos = {
        "0": "Error General: No fue posible Asignar la tarjeta.",
        "1": "La tarjeta fue asignada con éxito.",
        "2": "Tarjeta No registrada.",
        "3": "La tarjeta a procesar ya fue asignada previamente.",
        "4": "La cuenta ya se encuentra asignada.",
        "10": "No supero validaciones.",
        "11": "Tarjeta No Disponible.",
        "12": "La clave de empleado ya existe en el Sistema.",
        "13": "Código Retenedora Incorrecto.",
    }
    mensaje = codigos.get(status)
    return mensaje


# --------------------------------------------------------Etapa de pruebas para obtener tarjetas---------------
###Buscar tarjetas en stock
def listCard(numero_tarjeta):
    queryset = get_CardsStock()
    cardsDB = []
    for i in tarjeta.objects.filter(rel_proveedor_id=1):
        cardsDB.append(i.tarjeta)
    cards = []
    for i in queryset:
        if str(numero_tarjeta) in str(i['NumeroTarjeta']):
            if str(i['NumeroTarjeta']) not in cardsDB:
                cards.append(i)
    return cards


## Buscar tarjetas en stock inntec (Pruebas)
def listCardPrueba(numero_tarjeta):
    queryset = get_CardsStockPrueba()
    cardsDB = []
    for i in tarjeta.objects.filter(rel_proveedor_id=1):
        cardsDB.append(i.tarjeta)
    cards = []
    for i in queryset:
        if str(numero_tarjeta) in str(i['NumeroTarjeta']):
            if str(i['NumeroTarjeta']) not in cardsDB:
                cards.append(i)
    return cards


### Tarjetas que estan en stock (Produccion)
def get_CardsStock():
    URL = "https://www.inntecmp.com.mx/InntecAPI/"
    try:
        token, _ = get_token_prod()
        url_account = URL + 'api/Id/ReportesTarjetaMC/Tarjetas/C000682/57'
        headers = {'Authorization': 'Bearer ' + token}
        response = requests.get(url=url_account, headers=headers)
        response_json = response.json()
        return response_json
    except:
        return None


### Tarjetas que estan en stock (Prueba)
def get_CardsStockPrueba():
    URL = "http://desarrolloinntecmp.azurewebsites.net/InntecAPI/"
    try:
        token, _ = get_token_test()
        url_account = URL + 'api/Id/ReportesTarjetaMC/Tarjetas/C000022/57'
        headers = {'Authorization': 'Bearer ' + token}
        response = requests.get(url=url_account, headers=headers)
        response_json = response.json()
        return response_json
    except:
        return None


# FUNCION PARA DISPERSIONES INDIVIDUALES---------------------------------
def create_disper(tarjeta, monto):
    try:
        token, _ = get_token_test()
        arreglo = []
        diccionaio = {}
        diccionaio['TipoOperacion'] = 1
        diccionaio['TarjetaId'] = tarjeta
        diccionaio['Monto'] = monto
        arreglo.append(diccionaio)
        url_account = URL_POLIPAY_Test + '/api/Id/TarjetasMC/Dispersiones'
        headers = {'Authorization': 'Bearer ' + token}
        response = requests.post(url=url_account, json=arreglo, headers=headers)
        response_json = response.json()
        return response_json, response.status_code
    except:
        message_inntec_error = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "message": "Inntec error, please get in touch"
                }
            ]
        }
        raise serializers.ValidationError(message_inntec_error)


def get_Saldo(tarjeta):
    try:
        token, _ = get_token_test()
        url_token = URL_POLIPAY_Test + 'api/TarjetasMC/Saldos/' + tarjeta
        headers = {'Authorization': 'Bearer ' + token}
        response = requests.get(url=url_token, headers=headers)
        response_json = response.json()
        return response_json['Saldo']
    except:
        return None


def get_status(tarjeta):
    try:
        token, _ = get_token_test()
        url_token = URL_POLIPAY_Test + 'api/ReportesTarjetaMC/Estatus'
        data1 = """[{"NumeroTarjeta": """ + tarjeta + """}]"""
        data = json.loads(data1)
        headers = {'Authorization': 'Bearer ' + token}
        response = requests.post(url=url_token, json=data, headers=headers)
        response_json = response.json()
        status = response_json[0]['EstatusActual']
        return status
    except:
       return None

# (Jose 2022-01-06) Tarjetas que estan en stock Masivo (Prueba)
def get_CardsStockMasivoPrueba(token):
    URL = "http://desarrolloinntecmp.azurewebsites.net/InntecAPI/"
    try:
        url_account = URL + 'api/Id/ReportesTarjetaMC/Tarjetas/C000022/57'
        headers = {'Authorization': 'Bearer ' + token}
        response = requests.get(url=url_account, headers=headers)
        response_json = response.json()
        return response_json
    except:
        return None

# (Jose 2022-01-06 )  Comparar tarjetas sin pedir "n" veces el token
def listCardMasivoPrueba(numero_tarjeta,queryset):
    cardsDB = []
    for i in tarjeta.objects.filter(rel_proveedor_id=1):
        cardsDB.append(i.tarjeta)
    cards = []
    for i in queryset:
        if str(numero_tarjeta) in str(i['NumeroTarjeta']):
            if str(i['NumeroTarjeta']) not in cardsDB:
                cards.append(i)
    return cards

#### Gerar Clave empleado para inntec masivo despues del 10000 (Prueba)
def ClaveEmpleadoMasivoPrueba(token,datos_tarjeta_inntec):
    queryset = get_CardsAsignadasPrueba(token)
    queryset_db = tarjeta.objects.all()
    claveEmpleados = []
    diccionario = []
    for claveEmpleado in queryset:
        clave_empleados = ''.join(filter(str.isdigit, claveEmpleado['ClaveEmpleado'])) # Omite todas las que tengan una letra
        claveEmpleados.append(str(clave_empleados))
    for claveEmpleado in queryset_db:
        try:
            clave_empleados = ''.join(filter(str.isdigit, claveEmpleado.ClaveEmpleado)) # Omite todas las que tengan una letra
            claveEmpleados.append(str(clave_empleados))
        except:
            continue

    for claveEmpleado10000 in itertools.count(start=10000):
        if str(claveEmpleado10000) not in claveEmpleados:
            claveEmpleado = int(claveEmpleado10000)
            for datos in datos_tarjeta_inntec:
                dato = datos[0]
                dic = {
                    "tarjeta":dato.get("NumeroTarjeta"),
                    "ClaveEmpleado": str(claveEmpleado),
                    "TarjetaId":dato.get("TarjetaId"),
                    "NumeroCuenta":dato.get("NumeroCuenta"),
                }
                diccionario.append(dic)
                claveEmpleado = int(claveEmpleado) + 1
            return diccionario