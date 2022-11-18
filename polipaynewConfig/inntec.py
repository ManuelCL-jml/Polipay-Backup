import itertools
import re
from typing import List, Dict, Union, Any, ClassVar
import requests

from django.db.models import query
from django.db.models.query_utils import Q
import requests

from apps.transaction.exc import ErrorValidationInntec
from apps.users.models import tarjeta

import numpy as np
import requests
from django.conf import settings
import json
from Crypto.Hash import SHA256, HMAC
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
import base64

from rest_framework.exceptions import ValidationError

from polipaynewConfig.settings import CLIENT_ID_Test, CLIENT_SECRET_Test, USERNAME_Test, PASSWORD_Test, URL_POLIPAY_Test

ALGORITHM_NONCE_SIZE = 16
ALGORITHM_TAG_SIZE = 16
ALGORITHM_KEY_SIZE = 32
PBKDF2_SALT_SIZE = 16
PBKDF2_ITERATIONS = 32767
PBKDF2_LAMBDA = lambda x, y: HMAC.new(x, y, SHA256).digest()

# Polipay data
## Produccion
URL = settings.URL_POLIPAY
clientid = settings.CLIENT_ID
clientsecret = settings.CLIENT_SECRET
username = settings.USERNAME
password = settings.PASSWORD


def dispersion(data, token):
	try:
		url = URL + 'api/Id/TarjetasMC/Dispersiones'
		headers = {'accept': 'application/json', 'content-type': 'application/json', 'authorization': 'bearer ' + token}
		data_json = json.dumps(data)
		response = requests.post(url=url, data=data_json, headers=headers)
		return response.json()
	except:
		return None


def get_token():
	try:
		url_token = URL + 'token'
		data = {'grant_type': 'password', 'username': username, 'password': password, 'client_id': clientid,
				'client_secret': clientsecret}
		headers = {'accept': 'application/json', 'content-type': 'application/x-www-form-urlencoded'}
		response = requests.post(url=url_token, data=data, headers=headers)
		response_json = response.json()
		token = response_json['access_token']
		expires = response_json['.expires']
		return token, expires
	except:
		return None


def refresh_token(token):
	try:
		url_token = URL + 'token'
		data = {'refresh_token': token, 'grant_type': 'password', 'username': username, 'password': password,
				'client_id': clientid, 'client_secret': clientsecret}
		headers = {'accept': 'application/json', 'content-type': 'application/x-www-form-urlencoded'}
		response = requests.post(url=url_token, data=data, headers=headers)
		response_json = response.json()
		token = response_json['access_token']
		expires = response_json['.expires']
		return token, expires
	except:
		return None


def get_Counts():
	try:
		token, _ = get_token()
		url_account = URL + 'api/Id/ReportesTarjetaMC/Tarjetas/' + clientid + '/56'
		data = {'grant_type': 'password', 'username': username, 'password': password, 'client_id': clientid,
				'client_secret': clientsecret}
		headers = {'Authorization': 'Bearer ' + token}
		response = requests.get(url=url_account, headers=headers)
		response_json = response.json()
		return response_json
	except:
		return None


def get_status(tarjeta):
	try:
		token, _ = get_token()
		url_token = URL + 'api/ReportesTarjetaMC/Estatus'
		data1 = """[{"NumeroTarjeta": """ + tarjeta + """}]"""
		data = json.loads(data1)
		headers = {'Authorization': 'Bearer ' + token}
		response = requests.post(url=url_token, json=data, headers=headers)
		response_json = response.json()
		status = response_json[0]['EstatusActual']
		return status
	except Exception as e:
		print(e)
		return None


def get_Saldo(tarjeta):
	try:
		token, _ = get_token()
		url_token = URL + 'api/TarjetasMC/Saldos/' + tarjeta
		headers = {'Authorization': 'Bearer ' + token}
		response = requests.get(url=url_token, headers=headers)
		response_json = response.json()
		return response_json['Saldo']
	except:
		return None


def encrypt(plaintext, key):
	# Generate a 96-bit nonce using a CSPRNG.
	nonce = get_random_bytes(ALGORITHM_NONCE_SIZE)

	# Create the cipher.
	cipher = AES.new(key, AES.MODE_GCM, nonce)

	# Encrypt and prepend nonce.
	ciphertext, tag = cipher.encrypt_and_digest(plaintext)
	ciphertextAndNonce = nonce + ciphertext + tag

	return ciphertextAndNonce


def encryptString(plaintext, password):
	# Generate a 128-bit salt using a CSPRNG.
	salt = get_random_bytes(PBKDF2_SALT_SIZE)

	# Derive a key using PBKDF2.
	key = PBKDF2(password, salt, ALGORITHM_KEY_SIZE, PBKDF2_ITERATIONS, PBKDF2_LAMBDA)

	# Encrypt and prepend salt.
	ciphertextAndNonce = encrypt(plaintext.encode('utf-8'), key)
	ciphertextAndNonceAndSalt = salt + ciphertextAndNonce

	# Return as base64 string.
	return base64.b64encode(ciphertextAndNonceAndSalt)


def change_nip(tarjeta, nip, fechexp):
	token, _ = get_token()
	encryptedTajeta = encryptString(tarjeta, token)
	encryptedNip = encryptString(nip, token)
	encryptedFecha = encryptString(fechexp, token)
	url_account = URL + '/api/Id/TarjetasMC/Actualizaciones/Nip'
	data = {"Tarjeta": encryptedTajeta,
			"Nip": encryptedNip,
			"FechaVencimiento": encryptedFecha
			}
	headers = {'Authorization': 'Bearer ' + token}
	response = requests.post(url=url_account, data=data, headers=headers)
	response_json = response.json()
	return response_json, response.status_code


def change_status(tarjeta, status, clave):
	token, _ = get_token()
	url_account = URL + '/api/Id/TarjetasMC/Actualizaciones/Estatus'
	data = {"TarjetaId": tarjeta,
			"EstatusNuevo": status,
			"Observacion": clave + ' por el cliente'
			}
	headers = {'Authorization': 'Bearer ' + token}
	response = requests.post(url=url_account, data=data, headers=headers)
	response_json = response.json()
	return response_json, response.status_code

def get_amount(saldoDispersar):
	token, _ = get_token()
	url_account = URL + '/api/OperacionMC/Monederos/'+ clientid + '/56'
	headers = {'Authorization': 'Bearer ' + token}
	response = requests.get(url=url_account, headers=headers)
	response_json = response.json()
	if response_json['SaldoActual'] < saldoDispersar:
		return [False, float(response_json['SaldoActual'])]
	else:
		return [True, float(response_json['SaldoActual'])]

def create_disper(tarjeta, monto):
	token, _ = get_token()
	arreglo = []
	diccionaio = {}
	diccionaio['TipoOperacion'] = 1
	diccionaio['TarjetaId'] = tarjeta
	diccionaio['Monto'] = monto
	arreglo.append(diccionaio)
	url_account = URL + '/api/Id/TarjetasMC/Dispersiones'
	headers = {'Authorization': 'Bearer ' + token}
	response = requests.post(url=url_account, json=arreglo, headers=headers)
	response_json = response.json()
	return response_json, response.status_code


def get_historial(tarjeta, date_from, date_end):
	token, _ = get_token()
	url_account = URL + '/api/TarjetasMC/Movimientos/' + tarjeta + '/' + date_from + '/' + date_end
	headers = {'Authorization': 'Bearer ' + token}
	response = requests.get(url=url_account, headers=headers)
	response_json = response.json()
	return response_json, response.status_code


def tipo_movimiento(movimiento):
	cargo = ['Comisiones Tarjeta', 'COMPRA POS', 'Ecommerce', 'Consulta Saldo', 'Retiro en ATM', 'Compra con CashBack',
			 'Contactless Saldos Internos', 'Compra POS (TPV/Ecomerce/Contactless)', 'Retiro en AMT',
			 'Consulta de Saldo en ATM',
			 'Compra con CashBack', 'Transferencia de saldo a Usuario', 'Decremento o Reverso', 'Envio de SPEI Tarjeta']

	abono = ['Devolucion por Vencimiento', 'Devolución', 'Anulación de Transacción Ecomerce',
			 'Anulación de Transacción POS', 'Recepcion de SPEI Tarjeta',
			 'Reverso Spei out', 'Ajuste de Aclaración', 'Recarga', 'Transferencia de saldo de Usuario',
			 'Decremento MC Cargo COMPENSADA']

	for tipo in cargo:
		if str(movimiento).lower() == tipo.lower():
			return False

	for tipo in abono:
		if str(movimiento).lower() == tipo.lower():
			return True


# def get_tokenInntec():
#     URL = "http://desarrolloinntecmp.azurewebsites.net/InntecAPI/"
#     # username_produccion = "Polimentes_"
#     # password_produccion  = "f0dR60QXExGHmxIx2Bcx"
#     # clientid_produccion  = "C000682"
#     # clientsecret_produccion  = "47FF1C09-617E-4AB3-BF8D-583488D4CECA"
#     try:
#         url_token = URL + 'token'
#         data = {'grant_type': 'password', 'username': username_produccion , 'password': password_produccion , 'client_id': clientid_produccion ,
#                 'client_secret': clientsecret_produccion }
#         headers = {'accept': 'application/json', 'content-type': 'application/x-www-form-urlencoded'}
#         response = requests.post(url=url_token, data=data, headers=headers)
#         response_json = response.json()
#         token = response_json.get('access_token')
#         expires = response_json.get('.expires')
#         return token, expires
#     except:
#         return None


### Tarjetas que estan en stock (Produccion)
def get_CardsStock():
	URL = "https://www.inntecmp.com.mx/InntecAPI/"
	try:
		token, _ = get_token()
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
		token, _ = get_tokenInntecPruebas()
		url_account = URL + 'api/Id/ReportesTarjetaMC/Tarjetas/C000022/57'
		headers = {'Authorization': 'Bearer ' + token}
		response = requests.get(url=url_account, headers=headers)
		response_json = response.json()
		return response_json
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


# (Jose 2022-01-06) Tarjetas que estan en stock Masivo (Produccion)
def get_CardsStockMasivo(token):
	URL = "https://www.inntecmp.com.mx/InntecAPI/"
	try:
		url_account = URL + 'api/Id/ReportesTarjetaMC/Tarjetas/C000682/57'
		headers = {'Authorization': 'Bearer ' + token}
		response = requests.get(url=url_account, headers=headers)
		response_json = response.json()
		return response_json
	except:
		return None


## Tarjetas ya asignadas Produccion
def get_CardsAsignadas(token):
	URL = "https://www.inntecmp.com.mx/InntecAPI/"
	try:
		token, _ = get_token()
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
		print(response_json)
		return response_json
	except:
		return None


###Buscar tarjetas en stock inntec (Produccion)
def listCard(numero_tarjeta):
	queryset = get_CardsStock()
	cardsDB = []
	cards = []
	if numero_tarjeta != "":
		for i in tarjeta.objects.filter(rel_proveedor_id=1):
			cardsDB.append(i.tarjeta)
		for i in queryset:
			if str(numero_tarjeta) in str(str(i['NumeroTarjeta'])):
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


# (Jose 2022-01-06 )  Comparar tarjetas sin pedir "n" veces el token
def listCardMasivoPrueba(numero_tarjeta, queryset):
	cardsDB = []
	for i in tarjeta.objects.filter(rel_proveedor_id=1):
		cardsDB.append(i.tarjeta)
	cards = []
	cards_inntec = []
	for i in queryset:
		cards.append(i['NumeroTarjeta'])

		if str(numero_tarjeta) in cards_inntec:
			if str(i['NumeroTarjeta']) not in cardsDB:
				cards.append(i)
	return cards


def listCardMasivo(numero_tarjeta, queryset):
	cards = []
	for i in queryset:
		if str(numero_tarjeta) in str(i['NumeroTarjeta']):
			cards.append(i)
	return cards


### Buscar saldos de tarjetas inntec
def get_Saldos(tarjetaId):
	URL = "https://www.inntecmp.com.mx/InntecAPI/"
	try:
		token, _ = get_token()
		url_account = URL + 'api/Id/TarjetasMC/Saldos/' + str(tarjetaId)
		headers = {'Authorization': 'Bearer ' + token}
		response = requests.get(url=url_account, headers=headers)
		response_json = response.json()
		return response_json
	except:
		return None

	### Buscar saldos de tarjetas inntec prueba


def get_SaldosPrueba(tarjetaId):
	URL = "http://desarrolloinntecmp.azurewebsites.net/InntecAPI/"
	try:
		token, _ = get_tokenInntecPruebas()
		# url_account = URL + 'api/Id/TarjetasMC/Saldos/178683' ## https://www.inntecmp.com.mx/InntecAPI/api/Id/TarjetasMC/Saldos/178683
		url_account = URL + 'api/Id/TarjetasMC/Saldos/' + str(tarjetaId)
		headers = {'Authorization': 'Bearer ' + token}
		response = requests.get(url=url_account, headers=headers)
		response_json = response.json()
		return response_json
	except:
		return None


#### Gerar Clave empleado para inntec despues del 10000 Produccion
def ClaveEmpleado():
	token, _ = get_token()
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
	for claveEmpleado10000 in itertools.count(start=10000):
		if str(claveEmpleado10000) not in claveEmpleados:
			return claveEmpleado10000


### Generar clave empleado para inntec individual despues del 10000
def ClaveEmpleadoIndividualPrueba():
	token, _ = get_tokenInntecPruebas()
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


#### Gerar Clave empleado para inntec masivo despues del 10000 (Prueba)
def ClaveEmpleadoMasivoPrueba(token, datos_tarjeta_inntec):
	queryset = get_CardsAsignadasPrueba(token)
	queryset_db = tarjeta.objects.all()
	claveEmpleados = []
	diccionario = []
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
			claveEmpleado = int(claveEmpleado10000)
			# for datos in datos_tarjeta_inntec:
			#     dato = datos[0]
			#     print(dato)
			#     dic = {
			#         "tarjeta":dato.get("NumeroTarjeta"),
			#         "ClaveEmpleado": str(claveEmpleado),
			#         "TarjetaId":dato.get("TarjetaId"),
			#         "NumeroCuenta":dato.get("NumeroCuenta"),
			#     }
			#     diccionario.append(dic)
			#     claveEmpleado = int(claveEmpleado) + 1
			for dato in datos_tarjeta_inntec:
				# dato = datos[0]
				print(dato)
				dic = {
					"tarjeta": dato,
					"ClaveEmpleado": str(claveEmpleado),
					"TarjetaId": str(claveEmpleado),
					"NumeroCuenta": str(claveEmpleado),
				}
				diccionario.append(dic)
				claveEmpleado = int(claveEmpleado) + 1
			return diccionario


#### Gerar Clave empleado para inntec masivo despues del 10000 (Produccion)
def ClaveEmpleadoMasivo(token, datos_tarjeta_inntec):
	queryset = get_CardsAsignadas(token)
	queryset_db = tarjeta.objects.all()
	claveEmpleados = []
	diccionario = []
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
			claveEmpleado = int(claveEmpleado10000)
			for datos in datos_tarjeta_inntec:
				dato = datos[0]
				dic = {
					"tarjeta": dato.get("NumeroTarjeta"),
					"ClaveEmpleado": str(claveEmpleado),
					"TarjetaId": dato.get("TarjetaId"),
					"NumeroCuenta": dato.get("NumeroCuenta"),
				}
				diccionario.append(dic)
				claveEmpleado = int(claveEmpleado) + 1
			return diccionario


### Separar apellidos para inntec
def SepararApellidos(instanceP):
	if "*" in instanceP.last_name:
		first, last = instanceP.last_name.split("*")
		return first, last
	else:
		first, last = instanceP.last_name, "NA"
		return first, last


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


### Token de inntec de pruebas
def get_tokenInntecPruebas():
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


# Asignar Tarjetas de inntec a persona externa por medio de cuenta eje (Produccion)
def AsignarTarjetaPersonaExternaInntec(diccionario):
	URL = "https://www.inntecmp.com.mx/InntecAPI/api/Id/TarjetasMC/Asignaciones/"
	token, _ = get_token()
	url_account = URL
	headers = {'Authorization': 'Bearer ' + token}
	response = requests.post(url=url_account, json=diccionario, headers=headers)
	response_json = response.json()
	print(response_json)
	if int(response_json["EstatusProceso"]) != 1:
		status = response_json["EstatusProceso"]
		mensaje = CategoriasInntecError(str(status))
		raise ErrorValidationInntec("No fue posible dar de alta su tarjeta", detail=mensaje)
	return response_json


# Asignar Tarjetas de inntec a persona externa por medio de cuenta eje (Pruebas)
def AsignarTarjetaPersonaExternaInntecPrueba(diccionario):
	URL = "http://desarrolloinntecmp.azurewebsites.net/InntecAPI/api/Id/TarjetasMC/Asignaciones/"
	token, _ = get_tokenInntecPruebas()
	url_account = URL
	headers = {'Authorization': 'Bearer ' + token}
	response = requests.post(url=url_account, json=diccionario, headers=headers)
	response_json = response.json()
	if int(response_json["EstatusProceso"]) != 1:
		status = response_json["EstatusProceso"]
		mensaje = CategoriasInntecError(str(status))
		raise ErrorValidationInntec("No fue posible dar de alta su tarjeta", detail=mensaje)
	return response_json


# (Jose 2022-01-05) End point para asignar tarjeta de manera masiva
def AsignarTarjetaPersonaExternaInntecPruebaMasivo(diccionario):
	try:
		URL = "http://desarrolloinntecmp.azurewebsites.net/InntecAPI/api/Id/TarjetasMC/Asignaciones/"
		token, _ = get_tokenInntecPruebas()
		url_account = URL
		headers = {'Authorization': 'Bearer ' + token}
		response = requests.post(url=url_account, json=diccionario, headers=headers)
		response_json = response.json()
		if int(response_json["EstatusProceso"]) != 1:
			status = response_json["EstatusProceso"]
			mensaje = CategoriasInntecError(status)
			raise ValidationError({"code": ["400"], "status": ["error"],
								   "detail": [{"message": "No se pudo dar de alta la tarjeta"},
											  {"field": "", "message": mensaje,
											   "data": ""}]})
		return response_json
	except:
		raise ValidationError({"code": ["400"], "status": ["error"],
							   "detail": [{"message": "No se pudo dar de alta la tarjeta"},
										  {"field": "", "message": response_json,
										   "data": ""}]})


# (Jose 2022-01-05) End point para asignar tarjeta de manera masiva Produccion
def AsignarTarjetaPersonaExternaInntecMasivo(diccionario):
	try:
		URL = "https://www.inntecmp.com.mx/InntecAPI/api/Id/TarjetasMC/Asignaciones/"
		token, _ = get_token()
		url_account = URL
		headers = {'Authorization': 'Bearer ' + token}
		response = requests.post(url=url_account, json=diccionario, headers=headers)
		response_json = response.json()
		if int(response_json["EstatusProceso"]) != 1:
			status = response_json["EstatusProceso"]
			mensaje = CategoriasInntecError(status)
			raise ValidationError({"code": ["400"], "status": ["error"],
								   "detail": [{"message": "No se pudo dar de alta la tarjeta"},
											  {"field": "", "message": mensaje,
											   "data": ""}]})
		return response_json
	except:
		raise ValidationError({"code": ["400"], "status": ["error"],
							   "detail": [{"message": "No se pudo dar de alta la tarjeta"},
										  {"field": "", "message": response_json,
										   "data": ""}]})


## Ver movimientos de tarjeta inntec (Produccion)
def get_MovimientosTarjetas(tarjetaId, FechaDesde, FechaHasta):
	URL = "https://www.inntecmp.com.mx/InntecAPI/"
	try:
		token, _ = get_token()
		url_account = URL + 'api/Id/TarjetasMC/Movimientos/' + str(tarjetaId) + '/' + str(FechaDesde) + '/' + str(
			FechaHasta)
		headers = {'Authorization': 'Bearer ' + token}
		response = requests.get(url=url_account, headers=headers)
		response_json = response.json()
		return response_json
	except:
		return None


def get_MovimientosTarjetasPruebas(tarjetaId, FechaDesde, FechaHasta):
	URL = "http://desarrolloinntecmp.azurewebsites.net/InntecAPI/"
	try:
		token, _ = get_tokenInntecPruebas()
		url_account = URL + 'api/Id/TarjetasMC/Movimientos/' + str(tarjetaId) + '/' + str(FechaDesde) + '/' + str(
			FechaHasta)
		headers = {'Authorization': 'Bearer ' + token}
		response = requests.get(url=url_account, headers=headers)
		response_json = response.json()
		return response_json
	except:
		return None


# (ChrGil 2022-01-28) Regresa el estado actual de una tarjeta
def get_actual_state(tarjeta_id: Dict[str, int]) -> List[Dict[str, Any]]:
	list_folio = []
	session = requests.Session()
	session.verify = True
	token, _ = get_token()
	session.headers['Authorization'] = f"Bearer {token}"
	endpoint = "https://www.inntecmp.com.mx/InntecAPI/api/Id/ReportesTarjetaMC/Estatus"
	try:
		list_folio.append(tarjeta_id)
		response = session.request('POST', endpoint, json=list_folio)
		return response.json()
	except Exception as e:
		print(e)
