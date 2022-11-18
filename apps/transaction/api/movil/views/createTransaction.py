# -*- coding: utf-8 -*-
import threading
import numbers
import time

from django.http import HttpResponse
from django.template import loader
from django.db.models import Q

from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.transaction.management import *
from apps.transaction.api.movil.serializers.createTransaction import *
from apps.users.management import get_Object_orList_error
from apps.users.models import persona, cuenta, tarjeta
from apps.contacts.models import contactos
from apps.users.api.movil.serializers.user_serializer import serializerUserOut
from apps.transaction.models import transferencia
from MANAGEMENT.EncryptDecrypt.encdec_nip_cvc_token4dig import encdec_nip_cvc_token4dig
from MANAGEMENT.notifications.movil.notifyAppUser import notifyAppUser
from MANAGEMENT.MovementReport.MovementReportAccount import MovementReportAccount
from MANAGEMENT.MovementReport.MovementReportCard import MovementReportCard
from MANAGEMENT.MovementReport.MovementReportCards import MovementReportCards
from MANAGEMENT.MovementReport.MovementReportAccountCards import MovementReportAccountCards
from MANAGEMENT.notifications.any.SendEmail import SendEmail
from MANAGEMENT.Files.DeleteFile import DeleteFile
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from MANAGEMENT.Users.get_id import get_id
from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog


class createUserTransactionMovil(viewsets.GenericViewSet):
	serializer_class	= serialzierCreateTransaction
	queryset			= transferencia.objects.all()
	permission_classes	= [IsAuthenticated]
	#permission_classes = ()

	def create(self, request):
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)
		# Validación para parametrizar mensaje en get_Object_orList_error
		queryExistValOfInstance	= cuenta.objects.filter(id=request.data['cuentatransferencia']).exists()
		if not queryExistValOfInstance:
			msg = LanguageRegisteredUser(self.request.user.id, "BackEnd001")
			r	= {"status":msg}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_400_BAD_REQUEST)

		cuentaInstance = get_Object_orList_error(cuenta, id=request.data['cuentatransferencia'])

		# Validación para parametrizar mensaje en get_Object_orList_error
		queryExistValOfInstance = persona.objects.filter(id=cuentaInstance.persona_cuenta_id).exists()
		if not queryExistValOfInstance:
			msg = LanguageRegisteredUser(self.request.user.id, "BackEnd001")
			r = {"status": msg}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_400_BAD_REQUEST)

		clientInstace = get_Object_orList_error(persona, id=cuentaInstance.persona_cuenta_id)

		#idP = get_id(campo="idAccount", valorInt=request.data["cuentatransferencia"])
		#if not isinstance(idP, numbers.Number):
		#	return idP
		if str(request.data['tipo_pago']) == '1':

			# Validación para parametrizar mensaje en get_Object_orList_error
			queryExistValOfInstance = cuenta.objects.filter(cuenta=request.data['cta_beneficiario']).exists()
			if not queryExistValOfInstance:
				msg = LanguageRegisteredUser(self.request.user.id, "BackEnd001")
				r = {"status": msg}
				RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
				return Response(r, status=status.HTTP_400_BAD_REQUEST)

			countInstanceBenefe = get_Object_orList_error(cuenta, cuenta=request.data['cta_beneficiario'])
			if countInstanceBenefe.is_active == False:
				#msg = LanguageRegisteredUser(idP, "Tra004BE")
				#return Response({"status": [msg]}, status=status.HTTP_400_BAD_REQUEST)
				r	= {"status": ["Cuenta de beneficiario inactiva"]}
				RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
				return Response(r, status=status.HTTP_400_BAD_REQUEST)
		else:
			countInstanceBenefe = ''

		if str(request.data['tipo_pago']) == '3':
			# (2022.05.30 15:1500 - ChrAvaBus) Ya no se recuperan movimientos de la tarjeta desde la API
			# (2022.05.30 15:1500 - ChrAvaBus) de inntec, ahora se recuperan desde la bdd.
			"""
			ARRAY_CUENTAS_PERMITIDAS	= [
				"7180180044", "646180171801800447"
			]
			if str(request.data["cuenta_emisor"]) not in ARRAY_CUENTAS_PERMITIDAS:
				r = {"status": "¡Lo sentimos!\n\nPor el momento no se pudo realizar la operación,\nintente mas  tarde."}
				RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
				return Response(r, status=status.HTTP_400_BAD_REQUEST)
			"""

			# Validación para parametrizar mensaje en get_Object_orList_error
			queryExistValOfInstance = tarjeta.objects.filter(tarjeta=request.data['cta_beneficiario']).exists()
			if not queryExistValOfInstance:
				msg = LanguageRegisteredUser(self.request.user.id, "BackEnd001")
				r = {"status": msg}
				RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
				return Response(r, status=status.HTTP_400_BAD_REQUEST)

			countInstanceBenefe = get_Object_orList_error(tarjeta, tarjeta=request.data['cta_beneficiario'])
			if countInstanceBenefe.is_active == False:
				#msg = LanguageRegisteredUser(idP, "Tra004BE")
				#return Response({"status": [msg]}, status=status.HTTP_400_BAD_REQUEST)
				r	= {"status": ["Cuenta de beneficiario inactiva"]}
				RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
				return Response(r, status=status.HTTP_400_BAD_REQUEST)

		if cuentaInstance.is_active == False:
			#msg = LanguageRegisteredUser(idP, "Tra005BE")
			#return Response({"status": [msg]}, status=status.HTTP_400_BAD_REQUEST)
			r	= {"status": ["Cuenta inactiva"]}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_400_BAD_REQUEST)

		# Cifrado
		objJson	= encdec_nip_cvc_token4dig("1", "BE", request.data['token'])
		if str(clientInstace.token) != str(objJson["data"]):
			#msg = LanguageRegisteredUser(idP, "Tra006BE")
			# return Response({"status": ["Token de Seguridad Incorrecto,\npor favor ingrésalo de nuevo."]}, status=status.HTTP_400_BAD_REQUEST)
			msg = LanguageRegisteredUser(self.request.user.id, "Tra006BE")
			r	= {"status": [msg]}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_400_BAD_REQUEST)

		if cuentaInstance.monto < request.data['monto']:
			#msg = LanguageRegisteredUser(idP, "Tra007BE")
			#return Response({"status": [msg]}, status=status.HTTP_400_BAD_REQUEST)
			r	= {"status": ["Saldo insuficiente"]}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_400_BAD_REQUEST)

		serializer = self.serializer_class(data=request.data, context={"idUser":self.request.user.id, "url":get_info(request)})
		if serializer.is_valid(raise_exception=True):
			serializer.save(countInstanceBenefe, cuentaInstance, clientInstace)
			serialzierCount = serializerUserOut(clientInstace)
			if request.data['is_Frecuent']:
				serializerFrecuent = serializerFeecuentContact(data=request.data)
				if serializerFrecuent.is_valid(raise_exception=True):
					serializerFrecuent.save(clientInstace)

					# (ChrAvaBus - lun29.11.2021) Enviar notificación usuario wallet
					if str(request.data["tipo_pago"]) != "3":
						t = threading.Thread(target=notifyAppUserThread, args=(request.data, request.data["tipo_pago"],))
						t.start()
						# notifyAppUser(request.data, request.data["tipo_pago"])

					#msg = LanguageRegisteredUser(idP, "Tra002")
					#return Response({"status": msg, "data": serialzierCount.data}, status=status.HTTP_400_BAD_REQUEST)
					r	= {"status": "Transferencia creada y frecuente", "data": serialzierCount.data}
					RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
					return Response(r, status=status.HTTP_200_OK)

			#(ChrAvaBus - lun29.11.2021) Enviar notificación usuario wallet
			if str( request.data["tipo_pago"] ) != "3":
				t = threading.Thread(target=notifyAppUserThread, args=(request.data, request.data["tipo_pago"],) )
				t.start()
				#notifyAppUser(request.data, request.data["tipo_pago"])

			#msg = LanguageRegisteredUser(idP, "Tra001")
			#return Response({"status": msg, "data": serialzierCount.data}, status=status.HTTP_400_BAD_REQUEST)
			r	= {"status": "Transferencia creada", "data": serialzierCount.data}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_200_OK)

	def list(self, request):
		#RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)
		kward			= getKward(request.GET)

		# Validación para parametrizar mensaje en get_Object_orList_error
		queryExistValOfInstance = persona.objects.filter(id=self.request.query_params['id']).exists()
		if not queryExistValOfInstance:
			msg = LanguageRegisteredUser(self.request.user.id, "BackEnd001")
			r = {"status": msg}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_400_BAD_REQUEST)

		instance		= get_Object_orList_error(persona, id=self.request.query_params['id'])
		serialzier		= serializerUSertransactionesOut(instance, context=kward)
		return Response(serialzier.data, status=status.HTTP_200_OK)



# ::: (mie25.08.2021 15:26 ChAvBu - Pendiente 001) Creación de endpoint y clase temporal para solicitar historial de movimientos de una tarjeta :::
class MovementHistory(viewsets.GenericViewSet):
	serializer_class	= serialzierCreateTransaction
	queryset			= transferencia.objects.all()
	permission_classes	= [IsAuthenticated]
	#permission_classes = ()

	def create(self, request):
		cuentaInstance = get_Object_orList_error(cuenta, id=request.data['cuentatransferencia'])
		clientInstace = get_Object_orList_error(persona, id=cuentaInstance.persona_cuenta_id)
		if str(request.data['tipo_pago']) == '1':
			countInstanceBenefe = get_Object_orList_error(cuenta, cuenta=request.data['cta_beneficiario'])
			if countInstanceBenefe.is_active == False:
				return Response({"status": ["Cuenta de beneficiario inactiva"]}, status=status.HTTP_400_BAD_REQUEST)
		else:
			countInstanceBenefe = ''

		if str(request.data['tipo_pago']) == '3':
			countInstanceBenefe = get_Object_orList_error(tarjeta, tarjeta=request.data['cta_beneficiario'])
			if countInstanceBenefe.is_active == False:
				return Response({"status": ["Cuenta de beneficiario inactiva"]}, status=status.HTTP_400_BAD_REQUEST)

		if cuentaInstance.is_active == False:
			return Response({"status": ["Cuenta inactiva"]}, status=status.HTTP_400_BAD_REQUEST)

		if str(clientInstace.token) != str(request.data['token']):
			return Response({"status": ["Token inválido"]}, status=status.HTTP_400_BAD_REQUEST)

		if cuentaInstance.monto < request.data['monto']:
			return Response({"status": ["Saldo insuficiente"]}, status=status.HTTP_400_BAD_REQUEST)

		serializer = self.serializer_class(data=request.data)
		if serializer.is_valid(raise_exception=True):
			serializer.save(countInstanceBenefe, cuentaInstance, clientInstace)
			serialzierCount = serializerUserOut(clientInstace)
			if request.data['is_Frecuent']:
				serializerFrecuent = serializerFeecuentContact(data=request.data)
				if serializerFrecuent.is_valid(raise_exception=True):
					serializerFrecuent.save(clientInstace)
					return Response({"status": "Transferencia creada y frecuente", "data": serialzierCount.data}, status=status.HTTP_200_OK)
			return Response({"status": "Transferencia creada", "data": serialzierCount.data}, status=status.HTTP_200_OK)

	def list(self, request):
		kward			= getKward(request.GET)
		instance		= get_Object_orList_error(persona, id=self.request.query_params['id'])
		kward["tarjeta"]	= request.GET.get("tarjeta")
		kward["type"]		= request.GET.get("type")
		serialzier		= serializerUSertransactionesOut_TmpP1(instance, context=kward)
		return Response(serialzier.data, status=status.HTTP_200_OK)



class getHistorial(viewsets.GenericViewSet):
	serializer_class	= serialzierCreateTransaction
	#queryset			= transferencia.objects.all()
	permission_classes = [IsAuthenticated]
	#permission_classes = ()



	def list(self, request):
		type				= self.request.query_params['type']
		tarjeta				= self.request.query_params['tarjeta']
		kwards				= getKward(request.GET)
		kwards["tarjeta"]	=  tarjeta
		if str(type) == 'card':
			# (2022.05.30 15:1500 - ChrAvaBus) Ya no se recuperan movimientos de la tarjeta desde la API
			# (2022.05.30 15:1500 - ChrAvaBus) de inntec, ahora se recuperan desde la bdd.
			"""
			fecha1				= str(kwards['fecha_creacion__gte']).replace('-', '')
			fecha2				= str(kwards['fecha_creacion__lte']).replace('-', '')
			response, statusR	= get_historial(tarjeta, fecha1, fecha2)
			query				= sorted(response, key=lambda x: x['Fecha'], reverse=True)
			"""
			instance		= get_Object_orList_error(persona, id=self.request.query_params['id'])
			kwards["type"]	= request.GET.get("type")
			serialzier		= serializerUSertransactionesOut_TmpP1(instance, context=kwards)
			#return Response(query, status=status.HTTP_200_OK)
			return Response(serialzier.data, status=status.HTTP_200_OK)
		if str(type) == 'account':
			instance = cuenta.objects.get(persona_cuenta_id=request.user.get_only_id())
			# instance	= get_Object_orList_error(cuenta, cuenta=tarjeta)
			serializer	= serializerAccountOutMoviltotals(instance, context=kwards)
			return Response(serializer.data, status=status.HTTP_200_OK)


class prueba(viewsets.GenericViewSet):
	permission_classes = ()
	serializer_class = serialzierCreateTransaction
	queryset = transferencia.objects.all()

	def list(self, request):
		hoa = get_amount(50000)
		print(hoa)
		return Response(status=status.HTTP_200_OK)


class lisTransactionTemplate(viewsets.GenericViewSet):
	permission_classes = ()
	serializer_class = serialzierCreateTransaction
	queryset = transferencia.objects.all()

	def list(self, request):
		latest_question_list = transferencia.objects.all().order_by('-fecha_creacion')
		template = loader.get_template('transaction.html')
		context = {
			'trans': latest_question_list,
		}
		return HttpResponse(template.render(context, request))



# -------- (ChrAvaBus Sab18.12.2021) v3 --------

def notifyAppUserThread(data1, data2):
	time.sleep(10)
	notifyAppUser(data1, data2)



class SendMovementReport(viewsets.GenericViewSet):
	serializer_class	= None
	permission_classes	= [IsAuthenticated]
	#permission_classes = ()


	def list(self, request):
		from apps.users.models import tarjeta

		objJson_cuenta			= {}
		objJson_tarjeta			= {}
		objJson_tarjetas		= []
		objJson_cuentaTarjetas	= []

		nombre					= ""
		correo					= ""
		mov_nombreBeneficiario	= ""
		mov_cuentaBeneficiario	= ""
		mov_fechaHora			= ""
		mov_monto				= ""
		mov_concepto 			= ""
		mov_referencia			= ""
		arrayMovimientos1		= []
		arrayMovimientos2		= []
		result					= {}

		pk			= self.request.query_params["id"]
		dateStart	= self.request.query_params["date_start"]
		dateEnd		= self.request.query_params["date_end"]
		tipo		= self.request.query_params["type"]
		valor		= self.request.query_params["number"]

		if pk == False or pk == None or pk == "":
			msg = LanguageRegisteredUser(pk, "RepMov001BE")
			result = {"status": msg}
			#result = {"status": "Debes proporcionar un id."}
			return Response(result, status=status.HTTP_400_BAD_REQUEST)

		queryExistePersona = persona.objects.filter(id=pk).exists()
		if not queryExistePersona:
			msg = LanguageRegisteredUser(pk, "RepMov002BE")
			result = {"status": msg}
			#result = {"status": "No existe Persona."}
			return Response(result, status=status.HTTP_400_BAD_REQUEST)

		queryPersona	= persona.objects.filter(id=pk).values("id", "name", "last_name", "email")
		nombre			= str(queryPersona[0]["name"]) + " " + str(queryPersona[0]["last_name"])
		correo			= str(queryPersona[0]["email"])

		queryCuenta		= cuenta.objects.filter(persona_cuenta_id=pk).values("id", "cuenta", "cuentaclave")
		personaCuentaId	= queryCuenta[0]["id"]
		personaCuenta	= str(queryCuenta[0]["cuenta"])
		personaClabe	= str(queryCuenta[0]["cuentaclave"])

		# Escenario 1: Reporte de Cuenta
		if str(tipo) == "account":
			queryMovimientos	= transferencia.objects.filter( Q(cuenta_emisor=personaCuenta) | Q(cta_beneficiario=personaCuenta),
				fecha_creacion__date__gte=dateStart, fecha_creacion__date__lte=dateEnd).order_by('-fecha_creacion',).values("id", "monto",
				"referencia_numerica", "concepto_pago", "fecha_creacion", "nombre_beneficiario", "cta_beneficiario")

			for movimiento in queryMovimientos:
				movimiento["fecha"] 		= movimiento.pop("fecha_creacion")
				movimiento["concepto"]		= movimiento.pop("concepto_pago")
				movimiento["referencia"]	= movimiento.pop("referencia_numerica")
				arrayMovimientos1.append(movimiento)

			objJson_cuenta["valor"]			= personaCuenta
			objJson_cuenta["movimientos"]	= arrayMovimientos1

		# Escenario 2: Reporte de Tarjeta
		elif str(tipo) == "card":

			queryPerteneceTarjeta	= tarjeta.objects.filter(tarjeta=valor, cuenta_id=personaCuentaId).exists()
			if not queryPerteneceTarjeta:
				msg = LanguageRegisteredUser(pk, "RepMov003BE")
				result = {"status": msg}
				#result = {"status": "Tarjeta no pertenece a usuario."}
				return Response(result, status=status.HTTP_400_BAD_REQUEST)

			queryMovimientos = transferencia.objects.filter(Q(cuenta_emisor=valor) | Q(cta_beneficiario=valor),
				fecha_creacion__date__gte=dateStart, fecha_creacion__date__lte=dateEnd).order_by('-fecha_creacion').values("id", "monto",
				"referencia_numerica", "concepto_pago", "fecha_creacion")

			for movimiento in queryMovimientos:
				movimiento["fecha"] 		= movimiento.pop("fecha_creacion")
				movimiento["concepto"]		= movimiento.pop("concepto_pago")
				movimiento["referencia"]	= movimiento.pop("referencia_numerica")
				arrayMovimientos1.append(movimiento)

			queryTarjeta = tarjeta.objects.filter(cuenta_id=personaCuentaId, tarjeta=valor).values("id", "tarjeta", "alias")

			objJson_tarjeta["valor"]		= queryTarjeta[0]["tarjeta"]
			objJson_tarjeta["alias"]		= queryTarjeta[0]["alias"]
			objJson_tarjeta["movimientos"]	= arrayMovimientos1

		# Escenario 3: Reporte de Tarjetas
		elif str(tipo) == "cards":
			queryTarjetas	= tarjeta.objects.filter(cuenta_id=personaCuentaId).values("id", "tarjeta", "alias")
			for tarjeta in queryTarjetas:
				queryMovimientos = transferencia.objects.filter(Q(cuenta_emisor=tarjeta["tarjeta"]) | Q(cta_beneficiario=tarjeta["tarjeta"]),
					fecha_creacion__date__gte=dateStart, fecha_creacion__date__lte=dateEnd).order_by('-fecha_creacion').values("id", "monto",
					"referencia_numerica", "concepto_pago", "fecha_creacion")


				for movimiento in queryMovimientos:
					movimiento["fecha"] 		= movimiento.pop("fecha_creacion")
					movimiento["concepto"] 		= movimiento.pop("concepto_pago")
					movimiento["referencia"]	= movimiento.pop("referencia_numerica")
					arrayMovimientos1.append(movimiento)

				objJson_tarjeta["valor"] 		= tarjeta["tarjeta"]
				objJson_tarjeta["alias"] 		= tarjeta["alias"]
				objJson_tarjeta["movimientos"]	= arrayMovimientos1
				objJson_tarjetas.append(objJson_tarjeta)
				arrayMovimientos1				= []
				objJson_tarjeta					= {}


		# Escenario 4: Reporte de Cuenta-Tarjetas
		elif str(tipo) == "both":
			# Movimientos de Cuenta
			queryMovimientos = transferencia.objects.filter(Q(cuenta_emisor=personaCuenta) | Q(cta_beneficiario=personaCuenta),
				fecha_creacion__date__gte=dateStart, fecha_creacion__date__lte=dateEnd).order_by('-fecha_creacion', ).values("id", "monto",
				"referencia_numerica", "concepto_pago", "fecha_creacion", "nombre_beneficiario", "cta_beneficiario")

			for movimiento in queryMovimientos:
				movimiento["fecha"]			= movimiento.pop("fecha_creacion")
				movimiento["concepto"]		= movimiento.pop("concepto_pago")
				movimiento["referencia"]	= movimiento.pop("referencia_numerica")
				arrayMovimientos1.append(movimiento)

			objJson_cuenta["valor"]			= personaCuenta
			objJson_cuenta["movimientos"]	= arrayMovimientos1
			arrayMovimientos1				= []

			# Movimientos de Tarjeta
			queryTarjetas = tarjeta.objects.filter(cuenta_id=personaCuentaId).values("id", "tarjeta", "alias")
			for tarjeta in queryTarjetas:
				queryMovimientos = transferencia.objects.filter(Q(cuenta_emisor=tarjeta["tarjeta"]) | Q(cta_beneficiario=tarjeta["tarjeta"]),
					fecha_creacion__date__gte=dateStart, fecha_creacion__date__lte=dateEnd).order_by('-fecha_creacion').values("id", "monto",
					"referencia_numerica", "concepto_pago", "fecha_creacion")

				for movimiento in queryMovimientos:
					movimiento["fecha"] = movimiento.pop("fecha_creacion")
					movimiento["concepto"] = movimiento.pop("concepto_pago")
					movimiento["referencia"] = movimiento.pop("referencia_numerica")
					arrayMovimientos2.append(movimiento)

				objJson_tarjeta["valor"] 		= tarjeta["tarjeta"]
				objJson_tarjeta["alias"] 		= tarjeta["alias"]
				objJson_tarjeta["movimientos"]	= arrayMovimientos2
				objJson_tarjetas.append(objJson_tarjeta)
				arrayMovimientos2				= []
				objJson_tarjeta 				= {}

			arrayTmp1CT	= {"cuenta":objJson_cuenta}
			arrayTmp2CT	= {"tarjetas": objJson_tarjetas}
			objJson_cuentaTarjetas.append(arrayTmp1CT)
			objJson_cuentaTarjetas.append(arrayTmp2CT)
			objJson_cuenta			= {}
			objJson_tarjetas		= []

		else:
			msg = LanguageRegisteredUser(pk, "RepMov004BE")
			result = {"status": msg}
			#result = {"status": "Valor incorrecto para tipo, nada por hacer."}
			return Response(result, status=status.HTTP_400_BAD_REQUEST)

		result = {
			"nombre": str(nombre),
			"correo": str(correo),
			"fechaini": str(dateStart),
			"fechafin": str(dateEnd),
			"tipo":{
				"cuenta": objJson_cuenta,
				"tarjeta": objJson_tarjeta,
				"tarjetas": objJson_tarjetas,
				"cuenta_tarjetas": objJson_cuentaTarjetas
			}
		}

		reporteEnviarPorCorreo	= ""

		# Escenario 1: Reporte de Cuenta
		if str(tipo) == "account":
			reporteEnviarPorCorreo	= MovementReportAccount(result)
		# Escenario 2: Reporte de Tarjeta
		elif str(tipo) == "card":
			reporteEnviarPorCorreo	= MovementReportCard(result)
		# Escenario 3: Reporte de Tarjetas
		elif str(tipo) == "cards":
			reporteEnviarPorCorreo	= MovementReportCards(result)
		# Escenario 4: Reporte de Cuenta-Tarjetas
		elif str(tipo) == "both":
			reporteEnviarPorCorreo	= MovementReportAccountCards(result)

		# Envia correo
		if str(tipo) == "account":
				tipo	= "Reporte de mi Cuenta"
		elif str(tipo) == "card":
				tipo	= "Reporte de Tarjeta"
		elif str(tipo) == "cards":
				tipo	= "Reporte de todas mis Tarjetas"
		elif str(tipo) == "both":
				tipo	= "Reporte de mi Cuenta y Tarjetas"
		objJsonCorreo = {"nombre": str(nombre), "email": str(correo)}
		errorAlEnviar	= SendEmail("MovementReport", reporteEnviarPorCorreo, objJsonCorreo)
		if errorAlEnviar:
			msg = LanguageRegisteredUser(pk, "RepMov005BE")
			# Elimina reporte
			errorAlEliminar				= DeleteFile(reporteEnviarPorCorreo)
			#msgErrorAlEliminarReporte	= ""
			if errorAlEliminar:
				msg = LanguageRegisteredUser(pk, "RepMov006BE")
				#msgErrorAlEliminarReporte	= "\nNo se pudo eliminar reporte."

			result = {"status": msg}
			#result = {"status": "No se pudo enviar el reporte de movimeitnos por correo." + str(msgErrorAlEliminarReporte)}
			return Response(result, status=status.HTTP_400_BAD_REQUEST)

		# Elimina reporte
		msg = LanguageRegisteredUser(pk, "RepMov007BE")
		errorAlEliminar = DeleteFile(reporteEnviarPorCorreo)
		#msgErrorAlEliminarReporte = ""
		if errorAlEliminar:
			msg = LanguageRegisteredUser(pk, "RepMov008BE")
			#msgErrorAlEliminarReporte = "\nNo se pudo eliminar reporte."

		result = {"status": msg}
		#result = {"status":"Tu reporte se envió correctamente al correo con el que estas registrado." + str(msgErrorAlEliminarReporte)}
		return Response(result, status=status.HTTP_200_OK)
