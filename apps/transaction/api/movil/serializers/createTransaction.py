from django.core.exceptions import ObjectDoesNotExist
from reportlab.pdfbase.ttfonts import TTFont

from rest_framework import serializers

from polipaynewConfig.inntec import *
from apps.transaction.models import *
from apps.transaction.messages import *
from apps.users.models import *
from apps.contacts.models import contactos
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from MANAGEMENT.Users.get_id import get_id
from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog


class serialzierCreateTransaction(serializers.Serializer):
	tipo_pago = serializers.IntegerField()
	cta_beneficiario = serializers.CharField()
	nombre_beneficiario = serializers.CharField()
	# banco = serializers.IntegerField()
	monto = serializers.FloatField()
	concepto_pago = serializers.CharField()
	referencia_numerica = serializers.CharField()
	nombre_emisor = serializers.CharField()
	cuenta_emisor = serializers.CharField()
	cuentatransferencia = serializers.IntegerField()
	# banco_beneficiario = serializers.CharField()
	status_trans = serializers.IntegerField()
	transmitter_bank = serializers.IntegerField()
	receiving_bank = serializers.IntegerField()

	def validate_transmitter_bank(self, value):
		queryBancoEmisor = bancos.objects.filter(id=value).exists()
		if not queryBancoEmisor:
			idP = get_id(campo="idAccount", valorInt=self.initial_data.get("cuentatransferencia"))
			msg = LanguageRegisteredUser(idP, "Tra001BE")
			r = {"status": msg}
			RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
			raise serializers.ValidationError(r)
			# raise serializers.ValidationError({"status": "Banco emisor no existe"})
		return value

	def validate_receiving_bank(self, value):
		queryBancoReceptor = bancos.objects.filter(id=value).exists()
		if not queryBancoReceptor:
			idP = get_id(campo="idAccount", valorInt=self.initial_data.get("cuentatransferencia"))
			msg = LanguageRegisteredUser(idP, "Tra002BE")
			r = {"status": msg}
			RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
			raise serializers.ValidationError(r)
			# raise serializers.ValidationError({"status": "Banco beneficiario no existe"})
		return value

	# def validate_persona(self, value):
	#    queryExistePersona = persona.objects.filter(id=value).exists()
	#    if not queryExistePersona:
	#        idP = get_id(campo="idAccount", valorInt=self.initial_data.get("cuentatransferencia"))
	#        msg = LanguageRegisteredUser(idP, "Das012BE")
	#        raise serializers.ValidationError({"status": msg})
	#        #raise serializers.ValidationError({"status": "Persona no registrada."})
	#    return value

	def save(self, cuenta_beneficiario, cuenta_emisor, clientInstace):
		instanceTransaccion = transferencia.objects.create_transfer(**self.validated_data)
		r = {"montoAntesDeOperacion_emisor": str(cuenta_emisor.monto)}
		RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
		cuenta_emisor.monto -= instanceTransaccion.monto
		cuenta_emisor.save()
		r = {"montoDespuesDeOperacion_emisor": str(cuenta_emisor.monto)}
		RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
		queryTipo = tipo_transferencia.objects.get(id=instanceTransaccion.tipo_pago_id)
		# Entre cuentas Polipay
		if queryTipo.nombre_tipo == 'Polipay a Polipay':
			r = {"TipoMovimiento": "Polipay a Polipay", "saldo": cuenta_beneficiario.monto, "descripcion":"Saldo antes de sumar el monto"}
			RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
			cuenta_beneficiario.monto += instanceTransaccion.monto
			r = {"TipoMovimiento": "Polipay a Polipay", "saldo": cuenta_beneficiario.monto, "descripcion":"Saldo despues de sumar el monto"}
			RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
			cuenta_beneficiario.save()
			createMessageTransactionRecieved(cuenta_beneficiario, instanceTransaccion)
			r = {"TipoMovimiento": "Polipay a Polipay", "notificacion": "Se notifica via correo a beneficiario"}
			RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
		# Entre cuenta Polipay a Tarjeta Polipay
		if queryTipo.nombre_tipo == 'Interno':
			statusAmount = get_amount(instanceTransaccion.monto)
			r = {"TipoMovimiento": "Polipay a Tarjeta", "saldo_inntec": statusAmount[1], "monto_dispersar":instanceTransaccion.monto}
			RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
			if statusAmount[0] == False:
				r = {"TipoMovimiento":"Polipay a Tarjeta", "saldo": cuenta_emisor.monto, "descripcion":"Saldo antes de devolucion"}
				RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
				cuenta_emisor.monto += instanceTransaccion.monto
				cuenta_emisor.save()
				r = {"TipoMovimiento": "Polipay a Tarjeta", "saldo":cuenta_emisor.monto,"descripcion":"Se devuelve monto al saldo del emisor"}
				RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
				instanceTransaccion.delete()
				r	= {"status": ["Por el momento no se puede completar la transacción"]}
				RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
				raise serializers.ValidationError(r)
			response, statusCode = create_disper(cuenta_beneficiario.TarjetaId, instanceTransaccion.monto)
			r = {"TipoMovimiento": "Polipay a Tarjeta", "INNTEC": {"response": str(cuenta_emisor.monto), "statusCode":str(statusCode)}}
			RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
			# (mar 18.01.2021 Cambio la llave del mensaje de inntec de Message por Mensaje)
			# msg = response["Message"]
			msg = response["Mensaje"]
			errorEstatusProceso = response["EstatusProceso"]
			r = {"TipoMovimiento": "Polipay a Tarjeta", "INNTEC": {"mensaje": msg, "status":errorEstatusProceso}}
			RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
			if errorEstatusProceso == 0 or str(statusCode) == '400' or str(statusCode) == '401' or str(statusCode) == '500' or str(statusCode) != '200':
				r = {"TipoMovimiento": "Polipay a Tarjeta", "saldo": cuenta_emisor.monto, "descripcion":"Saldo antes de devolucion", "INNTEC": {"mensaje": msg, "status":"error"}}
				RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
				cuenta_emisor.monto += instanceTransaccion.monto
				cuenta_emisor.save()
				r = {"TipoMovimiento": "Polipay a Tarjeta", "saldo":cuenta_emisor.monto,"descripcion":"Se devuelve monto al saldo del emisor"}
				RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
				instanceTransaccion.delete()
				# if response['Message'] == "Datos Incorrectos":
				if len(msg) >= 1 or msg == "Datos Incorrectos":
					# response['Message'] = "La cuenta no existe o no pertenece\na Polipay, favor de verificar los datos."
					# idP = get_id(campo="idAccount", valorInt=self.initial_data.get("cuentatransferencia"))
					# msg = LanguageRegisteredUser(idP, "Tra003BE")
					if response.get("Message") != None:
						msg = response["Message"]
					if response.get("Mensaje") != None:
						msg = response["Mensaje"]
				r = {"status": str(msg)}
				RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
				raise serializers.ValidationError(r)
				# raise serializers.ValidationError({"status": response['Message']})
		r = {"notificacion": "Se notifica via correo a emisor"}
		RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
		createMessageTransactionSend(clientInstace, instanceTransaccion, instanceTransaccion)


class serializerTransferOut(serializers.Serializer):
	id = serializers.ReadOnlyField()
	# banco_beneficiario = serializers.SerializerMethodField()
	cta_beneficiario = serializers.CharField()
	# banco = serializers.SerializerMethodField()
	alias = serializers.SerializerMethodField()
	clave_rastreo = serializers.CharField()
	nombre_beneficiario = serializers.CharField()
	rfc_curp_beneficiario = serializers.CharField()
	tipo_pago = serializers.SerializerMethodField()
	tipo_pago_id = serializers.SerializerMethodField()
	tipo_cuenta = serializers.CharField()
	monto = serializers.SerializerMethodField()
	concepto_pago = serializers.CharField()
	referencia_numerica = serializers.CharField()
	# institucion_operante = serializers.CharField()
	empresa = serializers.CharField()
	# banco_emisor = serializers.CharField()
	nombre_emisor = serializers.CharField()
	cuenta_emisor = serializers.CharField()
	fecha_creacion = serializers.DateTimeField()
	transmitter_bank = serializers.SerializerMethodField()
	receiving_bank = serializers.SerializerMethodField()

	def get_alias(self, obj: alias):
		try:
			if self.context['type'] == 'i':
				pass

			if self.context['type'] == 'e':
				if obj.tipo_pago_id == 8:
					pass
				else:
					instance = tarjeta.objects.get(tarjeta=obj.cta_beneficiario)
					return instance.alias
		except ObjectDoesNotExist as e:
			return None

	def get_transmitter_bank(self, obj: transmitter_bank):
		instance = bancos.objects.get(id=obj.transmitter_bank_id)
		return instance.institucion

	def get_receiving_bank(self, obj: receiving_bank):
		"""
	    try:
            instance = bancos.objects.get(clabe=obj.receiving_bank)
            return instance.institucion
        except:
            instance = bancos.objects.get(institucion__contains=obj.receiving_bank)
            return instance.institucion
        """
		if obj.tipo_pago_id == 8:
			pass
		else:
			instance = bancos.objects.get(id=obj.receiving_bank_id)
			return instance.institucion

	def get_tipo_pago(self, obj: tipo_pago):
		instance = tipo_transferencia.objects.get(id=obj.tipo_pago_id)
		return instance.nombre_tipo

	def get_tipo_pago_id(self, obj: tipo_pago_id):
		instance = tipo_transferencia.objects.get(id=obj.tipo_pago_id)
		return instance.id

	def get_monto(self, obj: monto):
		if self.context['type'] == 'i':
			return obj.monto
		if self.context['type'] == 'e':
			return obj.monto * -1


class serializerAccountOut(serializers.Serializer):
	id = serializers.ReadOnlyField()
	cuenta = serializers.CharField()
	fecha_creacion = serializers.DateTimeField()
	monto = serializers.FloatField()
	cuentaclave = serializers.CharField()
	is_active = serializers.BooleanField()
	egresos = serializers.SerializerMethodField()
	ingresos = serializers.SerializerMethodField()
	tarjetas = serializers.SerializerMethodField()

	def get_egresos(self, obj: egresos):
		kward = self.context
		kward['cuentatransferencia_id'] = obj.id
		query_set = transferencia.objects.filter(**kward).order_by('-fecha_creacion')
		if len(query_set) < 5:
			return serializerTransferOut(query_set, many=True, context={'type': 'e'}).data
		else:
			return serializerTransferOut(query_set[0:5], many=True, context={'type': 'e'}).data

	def get_ingresos(self, obj: ingresos):
		kward = self.context
		palabrasClave = {}
		palabrasClave['fecha_creacion__gte'] = kward['fecha_creacion__gte']
		palabrasClave['fecha_creacion__lte'] = kward['fecha_creacion__lte']
		palabrasClave['cta_beneficiario'] = obj.cuenta
		query_set = transferencia.objects.filter(**palabrasClave).order_by('-fecha_creacion')
		if len(query_set) < 5:
			return serializerTransferOut(query_set, many=True, context={'type': 'i'}).data
		else:
			return serializerTransferOut(query_set[0:5], many=True, context={'type': 'i'}).data

	def get_tarjetas(self, obj: tarjetas):
		query_set = tarjeta.objects.filter(cuenta_id=obj.id)
		return serializerTarjeta(query_set, many=True, context=self.context).data


class serializerTarjeta(serializers.Serializer):
	id = serializers.ReadOnlyField()
	tarjeta = serializers.CharField()
	is_active = serializers.BooleanField()
	monto = serializers.FloatField()
	status = serializers.CharField()
	TarjetaId = serializers.IntegerField()
	NumeroCuenta = serializers.CharField()
	cvc = serializers.CharField()
	fechaexp = serializers.DateField()
	alias = serializers.CharField()
	movimientos = serializers.SerializerMethodField()
	egresos = serializers.SerializerMethodField()
	ingresos = serializers.SerializerMethodField()

	def get_egresos(self, obj: egresos):
		egresos_list = []
		fecha1 = str(self.context['fecha_creacion__gte']).replace('-', '')
		fecha2 = str(self.context['fecha_creacion__lte']).replace('-', '')
		list, status = get_historial(obj.tarjeta, fecha1, fecha2)
		for movimiento in list:
			if tipo_movimiento(movimiento['Tipo']) == False:
				if len(egresos_list) < 6:
					egresos_list.append(movimiento)
				else:
					break
		query = sorted(egresos_list, key=lambda x: x['Fecha'], reverse=True)
		return query

	def get_ingresos(self, obj: ingresos):
		ingresos_list = []
		fecha1 = str(self.context['fecha_creacion__gte']).replace('-', '')
		fecha2 = str(self.context['fecha_creacion__lte']).replace('-', '')
		list, status = get_historial(obj.tarjeta, fecha1, fecha2)
		for movimiento in list:
			if tipo_movimiento(movimiento['Tipo']):
				if len(ingresos_list) < 6:
					ingresos_list.append(movimiento)
				else:
					break
		query = sorted(ingresos_list, key=lambda x: x['Fecha'], reverse=True)
		return query

	def get_movimientos(self, obj: movimientos):
		fecha1 = str(self.context['fecha_creacion__gte']).replace('-', '')
		fecha2 = str(self.context['fecha_creacion__lte']).replace('-', '')
		list, status = get_historial(obj.tarjeta, fecha1, fecha2)
		query = sorted(list, key=lambda x: x['Fecha'], reverse=True)
		if len(query) < 6:
			return query
		else:
			return query[0:5]


class serializerUSertransactionesOut(serializers.Serializer):
	id = serializers.ReadOnlyField()
	name = serializers.CharField()
	last_name = serializers.CharField()
	accounts = serializers.SerializerMethodField()

	def get_accounts(self, obj: accounts):
		query_set = cuenta.objects.filter(persona_cuenta_id=obj.id)
		return serializerAccountOut(query_set, context=self.context, many=True).data


class serializerFeecuentContact(serializers.Serializer):
	tipo_pago = serializers.IntegerField()
	cta_beneficiario = serializers.CharField()
	nombre_beneficiario = serializers.CharField()
	banco = serializers.IntegerField()
	is_favorite = serializers.BooleanField()
	alias = serializers.CharField()

	def save(self, insatancePerson):
		banco = self.validated_data.get('banco')
		if str(banco) == '86':
			banco = '0'
		query = contactos.objects.filter(cuenta=self.validated_data.get('cta_beneficiario'))
		if len(query) > 0:
			query[0].nombre = self.validated_data.get('nombre_beneficiario')
			query[0].banco = banco
			query[0].is_favorite = self.validated_data.get('is_favorite')
			query[0].alias = self.validated_data.get('alias')
			query[0].tipo_contacto_id = self.validated_data.get('tipo_pago')
			query[0].save()
		else:
			if str(banco) == '86':
				banco = '0'
			contactos.objects.create(
				nombre=self.validated_data.get('nombre_beneficiario'),
				cuenta=self.validated_data.get('cta_beneficiario'),
				banco=banco,
				is_favorite=self.validated_data.get('is_favorite'),
				person=insatancePerson,
				alias=self.validated_data.get('alias'),
				tipo_contacto_id=self.validated_data.get('tipo_pago')
			)


class serializerAccountOutMoviltotals(serializers.Serializer):
	id = serializers.ReadOnlyField()
	cuenta = serializers.CharField()
	fecha_creacion = serializers.DateTimeField()
	monto = serializers.FloatField()
	cuentaclave = serializers.CharField()
	is_active = serializers.BooleanField()
	egresos = serializers.SerializerMethodField()
	ingresos = serializers.SerializerMethodField()

	def get_egresos(self, obj: egresos):
		kward = self.context
		kward['cuentatransferencia_id'] = obj.id
		# query_set	= transferencia.objects.filter(**kward).order_by('-fecha_creacion')
		# query_set = transferencia.objects.filter(cuentatransferencia_id=kward['cuentatransferencia_id'],
		#										 fecha_creacion__date__gte=kward["fecha_creacion__gte"],
		#										 fecha_creacion__date__lte=kward["fecha_creacion__lte"]).order_by(
		#										'-fecha_creacion')
		# query_set = transferencia.objects.filter(cuenta_emisor=kward["tarjeta"],
		# 										 fecha_creacion__date__gte=kward["fecha_creacion__gte"],
		# 										 fecha_creacion__date__lte=kward["fecha_creacion__lte"]).order_by(
		# 	'-fecha_creacion')

		query_set = transferencia.objects.filter(
			Q(cuenta_emisor__icontains=kward["tarjeta"]) |
			Q(cta_beneficiario__icontains=obj.cuenta) |
			Q(cta_beneficiario__icontains=obj.cuentaclave)
		).filter(
			fecha_creacion__date__gte=kward["fecha_creacion__gte"],
			fecha_creacion__date__lte=kward["fecha_creacion__lte"]
		).order_by('-fecha_creacion')

		return serializerTransferOut(query_set, many=True, context={'type': 'e'}).data

	def get_ingresos(self, obj: ingresos):
		kward = self.context
		palabrasClave = {}
		palabrasClave['fecha_creacion__gte'] = kward['fecha_creacion__gte']
		palabrasClave['fecha_creacion__lte'] = kward['fecha_creacion__lte']
		palabrasClave['cta_beneficiario'] = obj.cuenta
		# query_set		= transferencia.objects.filter(**palabrasClave).order_by('-fecha_creacion')
		# query_set = transferencia.objects.filter( cuentatransferencia_id=kward['cuentatransferencia_id'],
		#										 fecha_creacion__date__gte=kward["fecha_creacion__gte"],
		#										 fecha_creacion__date__lte=kward["fecha_creacion__lte"]).order_by(
		#										'-fecha_creacion')
		query_set = transferencia.objects.filter(
			Q(cta_beneficiario__icontains=obj.cuenta) |
			Q(cta_beneficiario__icontains=obj.cuentaclave)
		).filter(
			fecha_creacion__date__gte=kward["fecha_creacion__gte"],
			fecha_creacion__date__lte=kward["fecha_creacion__lte"]
		).order_by('-fecha_creacion')
		return serializerTransferOut(query_set, many=True, context={'type': 'i'}).data


# --------------------------- (mie 25.08.2021 ChAvBu PENDIENTE001) Clases temporales y por mejorar -----------------------------------------
class serializerTarjeta_TmpP1(serializers.Serializer):
	id = serializers.ReadOnlyField()
	tarjeta = serializers.CharField()
	is_active = serializers.BooleanField()
	monto = serializers.FloatField()
	status = serializers.CharField()
	TarjetaId = serializers.IntegerField()
	NumeroCuenta = serializers.CharField()
	cvc = serializers.CharField()
	fechaexp = serializers.DateField()
	alias = serializers.CharField()
	movimientos	= serializers.SerializerMethodField()
	egresos = serializers.SerializerMethodField()
	ingresos = serializers.SerializerMethodField()

	# (ChrAva 06.09.2021) Se agrega por optimizacion en el tiempo de consulta (reducir los 6-8seg)
	respList = None
	respStatus = None

	def get_egresos(self, obj: egresos):
		egresos_list = []
		# (2022.05.30 15:1500 - ChrAvaBus) Ya no se recuperan movimientos de la tarjeta desde la API
		# (2022.05.30 15:1500 - ChrAvaBus) de inntec, ahora se recuperan desde la bdd.
		"""
		fecha1 = str(self.context['fecha_creacion__gte']).replace('-', '')
		fecha2 = str(self.context['fecha_creacion__lte']).replace('-', '')
		"""
		fecha1 = str(self.context['fecha_creacion__gte'])
		fecha2 = str(self.context['fecha_creacion__lte'])
		# (ChrAva 06.09.2021) Se agrega por optimizacion en el tiempo de consulta (reducir los 6-8seg)
		list = self.respList
		status = self.respStatus
		for movimiento in list:
			# (2022.05.30 15:1500 - ChrAvaBus) Ya no se recuperan movimientos de la tarjeta desde la API
			# (2022.05.30 15:1500 - ChrAvaBus) de inntec, ahora se recuperan desde la bdd.
			#if tipo_movimiento(movimiento['Tipo']) == False:
			#if str(movimiento["NumeroTarjeta"]) == str(obj.tarjeta):
			if ( str(movimiento["NumeroTarjeta"]) == str(obj.tarjeta) ) and ( "cta_beneficiario" in movimiento ):
				if len(egresos_list) < 6:
					egresos_list.append(movimiento)
				else:
					break

		# (2022.05.30 15:1500 - ChrAvaBus) Ya no se recuperan movimientos de la tarjeta desde la API
		# (2022.05.30 15:1500 - ChrAvaBus) de inntec, ahora se recuperan desde la bdd.
		"""
		query = sorted(egresos_list, key=lambda x: x['Fecha'], reverse=True)
		# return query	# original (por borrar)
		# (ChrAva 13.09.2021) Se agrega por mejora, regresa los primeros 5 registros
		if len(query) < 5:
			return query
		else:
			return query[0:5]
		"""
		return egresos_list

	def get_ingresos(self, obj: ingresos):
		ingresos_list = []
		# (2022.05.30 15:1500 - ChrAvaBus) Ya no se recuperan movimientos de la tarjeta desde la API
		# (2022.05.30 15:1500 - ChrAvaBus) de inntec, ahora se recuperan desde la bdd.
		"""
		fecha1 = str(self.context['fecha_creacion__gte']).replace('-', '')
		fecha2 = str(self.context['fecha_creacion__lte']).replace('-', '')
		"""
		fecha1 = str(self.context['fecha_creacion__gte'])
		fecha2 = str(self.context['fecha_creacion__lte'])
		# (ChrAva 13.09.2021) Se agrega por mejora, regresa los primeros 5 registros
		list = self.respList
		status = self.respStatus
		for movimiento in list:
			# (2022.05.30 15:1500 - ChrAvaBus) Ya no se recuperan movimientos de la tarjeta desde la API
			# (2022.05.30 15:1500 - ChrAvaBus) de inntec, ahora se recuperan desde la bdd.
			#if tipo_movimiento(movimiento['Tipo']):
			if ( str(movimiento["NumeroTarjeta"]) == str(obj.tarjeta) ) and  ("cuenta_emisor" in movimiento):
				if len(ingresos_list) < 6:
					ingresos_list.append(movimiento)
				else:
					break

		# (2022.05.30 15:1500 - ChrAvaBus) Ya no se recuperan movimientos de la tarjeta desde la API
		# (2022.05.30 15:1500 - ChrAvaBus) de inntec, ahora se recuperan desde la bdd.
		"""
		query = sorted(ingresos_list, key=lambda x: x['Fecha'], reverse=True)
		# return query	# original (por borrar)
		# (ChrAva 13.09.2021) Se agrega por mejora, regresa los primeros 5 registros
		if len(query) < 5:
			return query
		else:
			return query[0:5]
		"""
		return ingresos_list

	def get_movimientos(self, obj: movimientos):
		# (2022.05.30 15:1500 - ChrAvaBus) Ya no se recuperan movimientos de la tarjeta desde la API
		# (2022.05.30 15:1500 - ChrAvaBus) de inntec, ahora se recuperan desde la bdd.
		"""
		fecha1 = str(self.context['fecha_creacion__gte']).replace('-', '')
		fecha2 = str(self.context['fecha_creacion__lte']).replace('-', '')

		list, status = get_historial(obj.tarjeta, fecha1, fecha2)
		"""
		fecha1 = str(self.context['fecha_creacion__gte'])
		fecha2 = str(self.context['fecha_creacion__lte'])

		list	= transferencia.objects.filter(
			Q(cta_beneficiario=obj.tarjeta) | Q(cuenta_emisor=obj.tarjeta),
			Q(tipo_cuenta="inntec_movimientos_rev1") | Q(tipo_cuenta="inntec_movimientos_auto"),
			fecha_creacion__date__gte = fecha1,
			fecha_creacion__date__lte = fecha2
		).values("id", "cta_beneficiario", "nombre_beneficiario", "cuenta_emisor", "nombre_emisor",
				 "monto", "fecha_creacion", "date_modify", "rfc_curp_beneficiario", "status_trans_id", "tipo_pago_id",
				 "concepto_pago", "clave_rastreo", "cuentatransferencia_id", "receiving_bank_id", "transmitter_bank_id",
				 "tipo_cuenta"
				 ).order_by("-fecha_creacion")[0:5]
		status	= 200

		# (ChrAva 06.09.2021) Se agrega por optimizacion en el tiempo de consulta (reducir los 6-8seg)
		self.respStatus = status

		# (2022.05.30 15:1500 - ChrAvaBus) Ya no se recuperan movimientos de la tarjeta desde la API
		# (2022.05.30 15:1500 - ChrAvaBus) de inntec, ahora se recuperan desde la bdd.
		"""
		query = sorted(list, key=lambda x: x['Fecha'], reverse=True)
		if len(query) < 5:
			self.respList = query
			return query
		else:
			self.respList = query[0:5]
			return query[0:5]
		"""
		self.respList	= list
		#print("TAM[" + str(len(list)) + "]")
		for movimiento in list:
			if str(movimiento["cta_beneficiario"]) == str(obj.tarjeta):
				movimiento["NumeroTarjeta"]		= movimiento.pop("cta_beneficiario")
			elif str(movimiento["cuenta_emisor"]) == str(obj.tarjeta):
				movimiento["NumeroTarjeta"]		= movimiento.pop("cuenta_emisor")

			movimiento["MontoMonendaLocal"] = movimiento.pop("monto")
			movimiento["Fecha"]				= movimiento.pop("fecha_creacion")
			movimiento["Comercio"]			= movimiento.pop("concepto_pago")
			movimiento["Estatus"]			= movimiento.pop("rfc_curp_beneficiario")
			movimiento["Tipo"]				= movimiento.pop("status_trans_id")
			if str(movimiento["tipo_cuenta"]) == "inntec_movimientos_rev1":
				arrayTmpStatus			= str(movimiento["Estatus"]).split("__")
				movimiento["Estatus"]	= arrayTmpStatus[0]
				movimiento["Tipo"]		= arrayTmpStatus[1]

			# Catalogo temporal
			if str(movimiento["Tipo"]) == "Recarg":
				movimiento["Tipo"]	= "recarga"
			elif str(movimiento["Tipo"]) == "COMPRA":
				movimiento["Tipo"]	= "compra pos"
			elif str(movimiento["Tipo"]) == "RETIRO":
				movimiento["Tipo"] = "retiro"
			elif str(movimiento["Tipo"]) == "Compra":
				movimiento["Tipo"] = " ecommerce"
			elif str(movimiento["Tipo"]) == "CONSUL":
				movimiento["Tipo"] = "consulta de saldo en atm"
			elif str(movimiento["Tipo"]) == "Contac":
				movimiento["Tipo"] = "contactless saldos internos"
			elif str(movimiento["Tipo"]) == "Decrem":
				movimiento["Tipo"] = "decremento o reverso"
			elif str(movimiento["Tipo"]) == "DEVOLU":
				movimiento["Tipo"] = "devolución"
			elif str(movimiento["Tipo"]) == "Retiro":
				movimiento["Tipo"] = "retiro en atm"
			elif str(movimiento["Tipo"]) == "REVERS":
				movimiento["Tipo"] = "reverso devolución"

		#print("---------------------- movimientos ----------------------")
		#print(list)
		return list


class serializerTransferOut_TmpP1(serializers.Serializer):
	id = serializers.ReadOnlyField()
	# banco_beneficiario = serializers.SerializerMethodField()
	cta_beneficiario = serializers.CharField()
	# banco = serializers.SerializerMethodField()
	alias = serializers.SerializerMethodField()
	clave_rastreo = serializers.CharField()
	nombre_beneficiario = serializers.CharField()
	rfc_curp_beneficiario = serializers.CharField()
	tipo_pago = serializers.SerializerMethodField()
	tipo_pago_id = serializers.SerializerMethodField()
	tipo_cuenta = serializers.CharField()
	monto = serializers.SerializerMethodField()
	concepto_pago = serializers.CharField()
	referencia_numerica = serializers.CharField()
	# institucion_operante = serializers.CharField()
	empresa = serializers.CharField()
	# banco_emisor = serializers.CharField()
	nombre_emisor = serializers.CharField()
	cuenta_emisor = serializers.CharField()
	fecha_creacion = serializers.DateTimeField()
	transmitter_bank = serializers.SerializerMethodField()
	receiving_bank = serializers.SerializerMethodField()

	def get_alias(self, obj: alias):
		try:
			if self.context['type'] == 'i':
				pass

			if self.context['type'] == 'e':
				if obj.tipo_pago_id == 8:
					pass
				else:
					instance = tarjeta.objects.get(tarjeta=obj.cta_beneficiario)
					return instance.alias
		except ObjectDoesNotExist as e:
			return None

	def get_transmitter_bank(self, obj: transmitter_bank):
		instance = bancos.objects.get(id=obj.transmitter_bank_id)
		return instance.institucion

	def get_receiving_bank(self, obj: receiving_bank):
		"""
        try:
            instance = bancos.objects.get(clabe=obj.receiving_bank)
            return instance.institucion
        except:
            instance = bancos.objects.get(institucion__contains=obj.receiving_bank)
            return instance.institucion
        """

		if obj.tipo_pago_id == 8:
			pass
		else:
			instance = bancos.objects.get(id=obj.receiving_bank_id)
			return instance.institucion

	def get_tipo_pago(self, obj: tipo_pago):
		instance = tipo_transferencia.objects.get(id=obj.tipo_pago_id)
		return instance.nombre_tipo

	def get_tipo_pago_id(self, obj: tipo_pago):
		# instance = tipo_transferencia.objects.get(id=obj.tipo_pago_id)
		return obj.tipo_pago_id

	def get_monto(self, obj: monto):
		if self.context['type'] == 'i':
			return obj.monto
		if self.context['type'] == 'e':
			return obj.monto * -1


# (ChrAva 02.09.2021 PENDIENTE001) Se agrega por mejora type=card|account
class serializerAccountOutTypeAccount_TmpP1(serializers.Serializer):
	id = serializers.ReadOnlyField()
	cuenta = serializers.CharField()
	fecha_creacion = serializers.DateTimeField()
	monto = serializers.FloatField()
	cuentaclave = serializers.CharField()
	is_active = serializers.BooleanField()
	egresos = serializers.SerializerMethodField()
	ingresos = serializers.SerializerMethodField()

	def get_egresos(self, obj: egresos):
		kward = self.context
		kward.pop("tarjeta")
		kward.pop("type")
		kward['cuentatransferencia_id'] = obj.id
		# query_set = transferencia.objects.filter(cuenta_emisor=obj.cuenta).order_by('-fecha_creacion')

		# query_set = transferencia.objects.filter(cuenta_emisor=obj.cuenta,
		# 										 fecha_creacion__date__gte=kward["fecha_creacion__gte"],
		# 										 fecha_creacion__date__lte=kward["fecha_creacion__lte"]).order_by(
		# 	'-fecha_creacion')

		query_set = transferencia.objects.filter(
			Q(cuenta_emisor__icontains=obj.cuenta) |
			Q(cuenta_emisor__icontains=obj.cuentaclave)
		).filter(
			fecha_creacion__date__gte=kward["fecha_creacion__gte"],
			fecha_creacion__date__lte=kward["fecha_creacion__lte"]
		).order_by('-fecha_creacion')

		if len(query_set) < 5:
			return serializerTransferOut_TmpP1(query_set, many=True, context={'type': 'e'}).data
		else:
			return serializerTransferOut_TmpP1(query_set[0:5], many=True, context={'type': 'e'}).data

	def get_ingresos(self, obj: ingresos):
		kward = self.context
		# palabrasClave = {}
		# palabrasClave['fecha_creacion__gte'] = kward['fecha_creacion__gte']
		# palabrasClave['fecha_creacion__lte'] = kward['fecha_creacion__lte']
		# palabrasClave['cta_beneficiario'] = obj.cuenta
		# query_set = transferencia.objects.filter(**palabrasClave).order_by('-fecha_creacion')

		query_set = transferencia.objects.filter(cta_beneficiario=obj.cuenta,
												 fecha_creacion__date__gte=kward["fecha_creacion__gte"],
												 fecha_creacion__date__lte=kward["fecha_creacion__lte"]).order_by(
			'-fecha_creacion')

		query_set = transferencia.objects.filter(
			Q(cta_beneficiario__icontains=obj.cuenta) |
			Q(cta_beneficiario__icontains=obj.cuentaclave)
		).filter(
			fecha_creacion__date__gte=kward["fecha_creacion__gte"],
			fecha_creacion__date__lte=kward["fecha_creacion__lte"]
		).order_by('-fecha_creacion')

		# (ChrAva 01.09.2021) Se agrega para regresar los ingresos de la cuenta [PENDIENTE]
		# ---------------------------------------------------------------------------
		if len(query_set) < 5:
			return serializerTransferOut_TmpP1(query_set, many=True, context={'type': 'i'}).data
		else:
			return serializerTransferOut_TmpP1(query_set[0:5], many=True, context={'type': 'i'}).data


# (ChrAva 02.09.2021 PENDIENTE001)	Se agrega por mejora
class serializerAccountOutTypeCard_TmpP1(serializers.Serializer):
	tarjetas = serializers.SerializerMethodField()

	def get_tarjetas(self, obj: tarjetas):
		kward = self.context
		query_set = tarjeta.objects.filter(cuenta_id=obj.id, tarjeta=kward["tarjeta"])
		return serializerTarjeta_TmpP1(query_set, many=True, context=self.context).data


class serializerUSertransactionesOut_TmpP1(serializers.Serializer):
	accounts = serializers.SerializerMethodField()

	def get_accounts(self, obj: accounts):
		# Recupera infromacion de la cuenta (relacion persona con cuenta)
		query_set = cuenta.objects.filter(persona_cuenta_id=obj.id)
		serializer = None

		if self.context["type"] == "card":
			serializer = serializerAccountOutTypeCard_TmpP1(query_set, context=self.context, many=True).data
		elif self.context["type"] == "account":
			serializer = serializerAccountOutTypeAccount_TmpP1(query_set, context=self.context, many=True).data

		return serializer

# -----------------------------------------------------------------------------------------------------
