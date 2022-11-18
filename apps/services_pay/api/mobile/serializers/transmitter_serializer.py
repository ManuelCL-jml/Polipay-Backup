from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers
from MANAGEMENT.ComissionPay.comission import RegistraOrdenSTP
from apps.logspolipay.manager import RegisterLog
from apps.services_pay.models import *
from apps.transaction.models import transferencia
from polipaynewConfig.redefectiva import *
from apps.users.models import cuenta, persona, grupoPersona
from apps.services_pay.management import generate_ticket
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.EncryptDecrypt.encdec_nip_cvc_token4dig import encdec_nip_cvc_token4dig


class SerializerFee(serializers.Serializer):
    description = serializers.CharField()
    amount = serializers.FloatField()


class SerializerTransmitter(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    family = serializers.CharField()
    id_transmitter = serializers.IntegerField()
    name_transmitter = serializers.CharField()
    short_name = serializers.CharField()
    description = serializers.CharField()
    presence = serializers.CharField()
    acept_partial_payment = serializers.BooleanField()
    max_amount = serializers.FloatField()
    image = serializers.FileField(allow_null=True, required=False)
    fees = SerializerFee(many=True)

    def validate(self, attrs):
        query = Transmitter.objects.filter(id_transmitter=attrs['id_transmitter'])
        if len(query) > 0:
            raise serializers.ValidationError({"status": [
                {
                    "code": 400,
                    "status": "Error",
                    "field": "",
                    "data": "",
                    "message": "Id Emisor duplicado"
                }]})
        else:
            return attrs

    def save(self):
        fee_list = self.validated_data.pop('fees')
        instance = Transmitter.objects.create(**self.validated_data)
        for feeobject in fee_list:
            Fee.objects.create(
                transmitter=instance,
                description=feeobject['description'],
                amount=feeobject['amount'])

    def update(self, instance, validated_data):
        instance.family = validated_data.get('family')
        instance.id_transmitter = validated_data.get('id_transmitter')
        instance.name_transmitter = validated_data.get('name_transmitter')
        instance.short_name = validated_data.get('short_name')
        instance.description = validated_data.get('description')
        instance.presence = validated_data.get('presence')
        instance.acept_partial_payment = validated_data.get('acept_partial_payment')
        instance.max_amount = validated_data.get('max_amount')
        instance.image = validated_data.get('image')
        instance.save()


class SerializerTransmitterHaveReferenceOut(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()
    type = serializers.CharField()
    length = serializers.IntegerField()
    length_required = serializers.BooleanField()
    required = serializers.BooleanField()
    reference = serializers.SerializerMethodField()

    def get_reference(self, obj: reference):
        return obj.reference.name


class SerializerTransmitterOut(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    family = serializers.CharField()
    id_transmitter = serializers.IntegerField()
    name_transmitter = serializers.CharField()
    short_name = serializers.CharField()
    description = serializers.CharField()
    presence = serializers.CharField()
    acept_partial_payment = serializers.BooleanField()
    max_amount = serializers.FloatField()
    image = serializers.FileField(allow_null=True, required=False)
    fees = serializers.SerializerMethodField()
    reference = serializers.SerializerMethodField()
    trantype = serializers.SerializerMethodField()

    def get_reference(self, obj: reference):
        query = TransmitterHaveReference.objects.filter(transmitter_id=obj.id)
        return SerializerTransmitterHaveReferenceOut(query, many=True).data

    def get_fees(self, obj: fees):
        query = Fee.objects.filter(transmitter_id=obj.id)
        return SerializerFee(query, many=True).data

    def get_trantype(self, obj: trantype):
        query = TransmitterHaveTypes.objects.filter(transmitter_id=obj.id).values('type__number')
        List = [data['type__number'] for data in query]
        return List


class SerializerRefrence(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField()

    def save(self):
        Reference.objects.create(**self.validated_data)

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name')
        instance.save()


class SerializerTransmitterHaveReference(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    description = serializers.CharField()
    type = serializers.CharField()
    length = serializers.IntegerField()
    length_required = serializers.BooleanField()
    required = serializers.BooleanField()
    reference_id = serializers.IntegerField()
    transmitter_id = serializers.IntegerField()

    def save(self):
        TransmitterHaveReference.objects.create(**self.validated_data)

    def update(self, instance, validated_data):
        instance.description = validated_data.get('description')
        instance.type = validated_data.get('type')
        instance.length = validated_data.get('length')
        instance.length_required = validated_data.get('length_required')
        instance.required = validated_data.get('required')
        instance.save()


# class SerializerPayTransmitter(serializers.Serializer):
# 	cuenta = serializers.CharField()
# 	Emisor = serializers.IntegerField()
# 	trantype = serializers.IntegerField()
# 	monto = serializers.FloatField()
# 	Comision = serializers.IntegerField(required=False, allow_null=True)
# 	Cargo = serializers.IntegerField(required=False, allow_null=True)
# 	token = serializers.CharField()
# 	reference = serializers.CharField()
# 	is_frequent = serializers.BooleanField()
#
# 	def validate(self, attrs):
# 		instance_emisor = Transmitter.objects.filter(id_transmitter=attrs['Emisor'])
# 		if len(instance_emisor) <= 0:	#Verificamos que exista en el emisor en nuestra DB
# 			message_not_found_transmmitter = {
# 				"status": "Id Emisor no encontrado"
# 			}
# 			RegisterSystemLog(idPersona=self.context["person_id"], type=1,
# 							  endpoint=self.context["endpoint"],
# 							  objJsonResponse=message_not_found_transmmitter)
# 			raise serializers.ValidationError(message_not_found_transmmitter)
# 		info_transmitter = solicita({
# 			"TranType": 32,
# 			"Emisor": attrs['Emisor']
# 		})
# 		try:
# 			longitud_obligatoria = info_transmitter.info3["Servicio"]["Ref1"]['@Req']
# 		except:
# 			message_redfectiva_error = {
# 				"status": "Error al consultar informacion del servicio con red efectiva"
# 			}
# 			raise serializers.ValidationError(message_redfectiva_error)
# 			#Verificamos que la longitud de la referencia es obligatoria
# 		if longitud_obligatoria == "1":
# 			# Verificamos si cumple con la logitud de la referencia
# 			if len(attrs['reference']) != int(info_transmitter.info3["Servicio"]["Ref1"]['@Len']):
# 				message_wrong_length = {
# 					"status": "La referencia tiene que tener una longitud de " + info_transmitter.info3["Servicio"]["Ref1"]['@Len']
# 				}
# 				RegisterSystemLog(idPersona=self.context["person_id"], type=1,
# 									endpoint=self.context["endpoint"],
# 									objJsonResponse=message_wrong_length)
# 				raise serializers.ValidationError(message_wrong_length)
# 		#verificamos que el monto no sea negativo
# 		if attrs['monto'] <= 0:
# 			message_invalid_amount = {
# 				"status": "Ingrese un monto valido"
# 			}
#
# 			RegisterSystemLog(idPersona=self.context["person_id"], type=1,
# 							  endpoint=self.context["endpoint"],
# 							  objJsonResponse=message_invalid_amount)
# 			raise serializers.ValidationError(message_invalid_amount)
# 		#Verificar si es un pago de servicio o una recarga de saldo
# 		comision = 0
# 		cargo = 0
# 		if attrs['trantype'] == 10:#Recarga
# 			monto_total = attrs['monto']*100
# 		elif attrs['trantype'] == 31:#Pago de servicio
# 			#verificamos si el Trantype 32 regresa la comision y el cargo, si no lo hace ponemos la comision y el cargo en 0
# 			if 'Comision' in info_transmitter.info3["Servicio"]:
# 				comision = int(info_transmitter.info3["Servicio"]["Comision"]) #transformamos sus centavos a pesos
# 				comision = int(comision/100)
# 			if 'Cargo' in info_transmitter.info3["Servicio"]:
# 				cargo = int(info_transmitter.info3["Servicio"]["Cargo"])
# 				cargo = int(cargo/100)
# 			monto_total = attrs['monto'] + comision
# 		else:
# 			message_invalid_trantype = {
# 				"status": "Ingresa un Trantype valido"
# 			}
#
# 			RegisterSystemLog(idPersona=self.context["person_id"], type=1,
# 							  endpoint=self.context["endpoint"],
# 							  objJsonResponse=message_invalid_trantype)
# 			raise serializers.ValidationError(message_invalid_trantype)
# 		self.Cargo = cargo
# 		self.Comision = comision
#
# 		instance_cuenta = cuenta.objects.filter(cuenta=attrs['cuenta'])
# 		#verificar que el usuario tiene el dinero suficiente
# 		if monto_total > instance_cuenta[0].monto:
# 			message_not_enough_funds = {
# 				"status": "La cuenta no tiene fondos suficientes para el pago"
# 			}
#
# 			RegisterSystemLog(idPersona=self.context["person_id"], type=1,
# 							  endpoint=self.context["endpoint"],
# 							  objJsonResponse=message_not_enough_funds)
# 			raise serializers.ValidationError(message_not_enough_funds)
# 		#Verificar que el Token sea el mismo de la BD
# 		instance_persona = persona.objects.get(id=instance_cuenta[0].persona_cuenta_id)
# 		#deciframos el token de la base de datos
# 		decrypt_token = encdec_nip_cvc_token4dig(accion="2", area="BE", texto=instance_persona.token)
# 		if attrs['token'] != decrypt_token['data']:
# 			message_wrong_token = {
# 				"status": "Token incorrecto"
# 			}
# 			RegisterSystemLog(idPersona=self.context["person_id"], type=1,
# 							  endpoint=self.context["endpoint"],
# 							  objJsonResponse=message_wrong_token)
# 			raise serializers.ValidationError(message_wrong_token)
# 		return attrs
#
# 	def create(self, validated_data):
# 		comision = 0
# 		cargo = 0
# 		instance_emisor = Transmitter.objects.filter(id_transmitter=validated_data['Emisor']).first()
# 		importe = int(validated_data['monto'] * 100)
# 		if validated_data['trantype'] == 10:  # Recarga
# 			response = solicita({
# 				"TranType": 10,
# 				"Emisor": validated_data['Emisor'],
# 				"Importe": importe,
# 				"sRef1": validated_data['reference']
# 			})
# 		elif validated_data['trantype'] == 31:
# 			comision = self.Comision*100
# 			cargo = self.Cargo*100
# 			response = solicita({
# 				"TranType": 31,
# 				"Emisor": validated_data['Emisor'],
# 				"Importe": importe,
# 				"Comision": comision,
# 				"Cargo": cargo,
# 				"sRef1": validated_data['reference']
# 			})
#
# 		instance_cuenta = cuenta.objects.filter(cuenta=validated_data['cuenta']).first()
# 		#verificamos que la transaccion es exitosa para descontar el dinero
# 		if response.solicitaResult == 0:
# 			# Descontar el monto total de la cuenta
# 			monto_total = validated_data['monto'] + comision / 100
# 			instance_cuenta.monto = instance_cuenta.monto - monto_total  # Cobro del servicio
# 			instance_cuenta.save()
#
# 		instance_code_efectiva = CodeEfectiva.objects.filter(code=response.solicitaResult)
# 		if len(instance_code_efectiva) <= 0:
# 			code_efectiva = 22
# 		else:
# 			code_efectiva = instance_code_efectiva[0].id
# 		#guardar el registro del pago en LogEfectiva
# 		instance_log_efectiva = LogEfectiva.objects.create(folio=response.Folio,
# 														   autorization=response.Autorizacion,
# 														   ticket=generate_ticket(),
# 														   correspondent=438,#Variable global
# 														   transmitterid=validated_data['Emisor'],
# 														   reference_one=validated_data['reference'],
# 														   amount=validated_data['monto']*100,
# 														   commission=comision,
# 														   charge=cargo,
# 														   code_id=code_efectiva,
# 														   transmitter_rel_id=instance_emisor.id,
# 														   user_rel_id=instance_cuenta.persona_cuenta_id)
# 		#guardar el registro de la transaccion
# 		instance_persona = persona.objects.get(id=instance_cuenta.persona_cuenta_id)
# 		dict_transference = {
# 			"nombre_servicio": instance_emisor.name_transmitter,
# 			"monto": validated_data['monto'],
# 			"referencia": validated_data['reference'],
# 			"nombre_emisor": instance_persona.get_full_name(),
# 			"cuenta": instance_cuenta.cuenta,
# 			"cargo": cargo,
# 			"comision": comision/100,
# 			"cuentatransferencia": instance_cuenta,
# 			"solicitaResult": response.solicitaResult,
# 			"email": instance_persona.email,
# 			"saldoRemanente": instance_cuenta.monto
#
# 		}
# 		create_transference_register(dict_transference)
# 		#guardar como servicio frecuente si is_frequent esta en true
# 		if validated_data['is_frequent']:
# 			#checamos si ya esta marcado como favorito
# 			instance_frequent = Frequents.objects.filter(transmmiter_Rel_id=instance_emisor.id,
# 														 user_rel_id=instance_cuenta.persona_cuenta_id)
# 			if len(instance_frequent) <= 0:#si no esta registrado lo guardamos como favorito
# 				Frequents.objects.create(transmmiter_Rel_id=instance_emisor.id,
# 										 user_rel_id=instance_cuenta.persona_cuenta_id)
# 		return response


def revert_account_user(data: Dict, instance: transferencia):
    instance.cuenta_emisor = data.get("cuenta")
    instance.save()


class GetInfoUser:
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.empresa = self.get_cuenta_eje
        self.empresa_cuenta = self.get_account
        self.empresa_stp = self._empresa_stp.get("empresa__name_stp")

    @property
    def get_cost_center(self) -> Dict[str, Any]:
        return grupoPersona.objects.filter(
            person_id=self.data.get("user_id"),
            relacion_grupo_id__in=[6, 9]
        ).values(
            "empresa_id"
        ).first()

    @property
    def get_cuenta_eje(self) -> grupoPersona:
        try:
            return grupoPersona.objects.get(
                person_id=self.get_cost_center.get("empresa_id"),
                relacion_grupo_id=5
            )
        except ObjectDoesNotExist as e:
            return grupoPersona.objects.get(
                empresa_id=self.get_cost_center.get("empresa_id"),
                relacion_grupo_id=1
            )

    @property
    def get_account(self) -> Dict[str, Any]:
        return cuenta.objects.filter(
            persona_cuenta=self.empresa.empresa
        ).values(
            "id",
            "cuentaclave"
        ).first()

    @property
    def _empresa_stp(self) -> Dict[str, Any]:
        return grupoPersona.objects.get_name_cuenta_eje(person_id=self.data.get("user_id"))


# (ChrGil 2022-05-09) Guarda en una varible de clase la información del centro de costos de red efectiva
class CECORedEfectiva:
    def __init__(self):
        self.ceco_red_efectiva = self.validate_exists_cost_center_red_efectiva

        if not self.ceco_red_efectiva:
            raise ValueError('No existe el centro de costos donde se le transferira la comisión')

    @property
    def validate_exists_cost_center_red_efectiva(self) -> Dict[str, Any]:
        return cuenta.objects.filter(
            persona_cuenta__name__icontains='POLIPAY RED EFECTIVA').values(
            'id',
            'cuentaclave',
            'persona_cuenta__name',
            'monto'
        ).first()


class CreateTransactionRedEfectiva:
    """ Se crea movimiento cuando el cliente realiza un pago de servicio """

    CAT_TRANT_TYPE_RED_EFECTIVA: ClassVar[Dict[str, Any]] = {
        "10": "ABONO TIEMPO AIRE",
        "30": "CONSULTA DE SALDO",
        "31": "PAGO DE SERVICIO",
        "32": "INFORMACIÓN DE SERVICIO",
    }

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.instance = self.create_transaction_red_efectiva(**self._data)

    @property
    def _data(self):
        return {
            "tipo": self.CAT_TRANT_TYPE_RED_EFECTIVA.get(str(self.data.get('tipo'))),
            "nombre_servicio": self.data.get('nombre_servicio'),
            "cuenta": self.data.get('cuentatransferencia'),
            "referencia": self.data.get('referencia'),
            "nombre_emisor": self.data.get('nombre_emisor'),
            "cuenta_emisor": self.data.get('cuenta'),
            "monto": self.data.get('monto'),
            "comision": self.data.get('comision'),
        }

    @staticmethod
    def create_transaction_red_efectiva(**kwargs):
        return transferencia.objects.create_transaction_red_efectiva(**kwargs)


class CreateTransactionRedEfectivaComission:
    """ Si el usuario tiene cuenta clabe, el usuario realizara la transacción a STP """

    _registra_orden: ClassVar[RegistraOrdenSTP] = RegistraOrdenSTP

    def __init__(
            self,
            data: Dict[str, Any],
            ceco: CECORedEfectiva,
            emisor: GetInfoUser,
            log: RegisterLog,
            efectiva: CreateTransactionRedEfectiva
    ):
        self.data = data
        self.ceco = ceco
        self.emisor = emisor

        if "X" not in data.get("cuenta"):
            instance = self.create_transaction_comission_red_efectiva(**self._data)
            self._registra_orden(instance, demo_bool=True, log=log, transaction_reference=efectiva.instance)
            # self.deposit_amount_comission()
            revert_account_user(data, instance)

    @property
    def _saldo_remanente(self) -> float:
        return round(self.ceco.ceco_red_efectiva.get('monto') + self.data.get('comision'), 4)

    @property
    def _data(self):
        return {
            "empresa": self.emisor.empresa_stp,
            "nombre_beneficiario": self.ceco.ceco_red_efectiva.get('persona_cuenta__name'),
            "cta_beneficiario": self.ceco.ceco_red_efectiva.get('cuentaclave'),
            "cuentatransferencia_id": self.data.get('cuenta_emisor_id'),
            "nombre_emisor": self.data.get('nombre_emisor'),
            "cuenta_emisor": self.data.get('cuentaclave'),
            "monto": self.data.get('comision'),
            "concepto_pago": "POLIPAY COMISION RED EFECTIVA",
            "saldo_remanente_beneficiario": self._saldo_remanente,
            "status_trans_id": 3,
        }

    @staticmethod
    def create_transaction_comission_red_efectiva(**kwargs):
        return transferencia.objects.tranfer_to_polipay_comission(**kwargs)

    def deposit_amount_comission(self):
        c: cuenta = cuenta.objects.get(id=self.ceco.ceco_red_efectiva.get('id'))
        c.monto += round(self.data.get('comision'), 2)
        c.save()


class CreateTransactionRedEfectivaComissionSinClabe:
    """ Si el usuario no tiene cuenta clabe, la cuenta eje o centro de costos realizara la transacción """

    _registra_orden: ClassVar[RegistraOrdenSTP] = RegistraOrdenSTP

    def __init__(
            self,
            data: Dict[str, Any],
            ceco: CECORedEfectiva,
            emisor: GetInfoUser,
            log: RegisterLog,
            efectiva: CreateTransactionRedEfectiva
    ):
        self.data = data
        self.ceco = ceco
        self.emisor = emisor

        if "X" in data.get("cuenta"):
            instance = self.create_transaction_comission_red_efectiva(**self._data)
            self._registra_orden(instance, demo_bool=False, log=log, transaction_reference=efectiva.instance)
            # self.deposit_amount_comission()
            revert_account_user(data, instance)

    @property
    def _saldo_remanente(self) -> float:
        return round(self.ceco.ceco_red_efectiva.get('monto') + self.data.get('comision'), 4)

    @property
    def _data(self):
        return {
            "empresa": self.emisor.empresa_stp,
            "nombre_beneficiario": self.ceco.ceco_red_efectiva.get('persona_cuenta__name'),
            "cta_beneficiario": self.ceco.ceco_red_efectiva.get('cuentaclave'),
            "cuentatransferencia_id": self.data.get('cuenta_emisor_id'),
            "nombre_emisor": self.data.get('nombre_emisor'),
            "cuenta_emisor": self.emisor.empresa_cuenta.get('cuentaclave'),
            "monto": self.data.get('comision'),
            "concepto_pago": "POLIPAY COMISION RED EFECTIVA",
            "saldo_remanente_beneficiario": self._saldo_remanente,
            "status_trans_id": 3,
        }

    @staticmethod
    def create_transaction_comission_red_efectiva(**kwargs):
        return transferencia.objects.tranfer_to_polipay_comission(**kwargs)

    def deposit_amount_comission(self):
        c: cuenta = cuenta.objects.get(id=self.ceco.ceco_red_efectiva.get('id'))
        c.monto += round(self.data.get('comision'), 2)
        c.save()


class SerializerPayTransmitter(serializers.Serializer):
    cuenta = serializers.CharField()
    Emisor = serializers.IntegerField()
    trantype = serializers.IntegerField()
    monto = serializers.FloatField()
    Comision = serializers.IntegerField(required=False, allow_null=True)
    Cargo = serializers.IntegerField(required=False, allow_null=True)
    token = serializers.CharField()
    reference = serializers.CharField()
    is_frequent = serializers.BooleanField()

    def validate(self, attrs):
        instance_emisor = Transmitter.objects.filter(id_transmitter=attrs['Emisor'])
        if len(instance_emisor) <= 0:  # Verificamos que exista en el emisor en nuestra DB
            message_not_found_transmmitter = {
                "status": "Id Emisor no encontrado"
            }
            RegisterSystemLog(idPersona=self.context["person_id"], type=1,
                              endpoint=self.context["endpoint"],
                              objJsonResponse=message_not_found_transmmitter)
            raise serializers.ValidationError(message_not_found_transmmitter)

        info_transmitter = None

        if attrs["trantype"] != 10:
            info_transmitter, ticket = solicita({
                "TranType": 32,
                "Emisor": attrs['Emisor']
            })

            try:
                longitud_obligatoria = info_transmitter.info3["Servicio"]["Ref1"]['@Req']
            except Exception as e:
                print(e)
                message_redfectiva_error = {
                    "status": "Error al consultar informacion del servicio con red efectiva"
                }
                raise serializers.ValidationError(message_redfectiva_error)

            if longitud_obligatoria == "1":
                # Verificamos si cumple con la logitud de la referencia
                if len(attrs['reference']) != 10:
                    if len(attrs['reference']) != int(info_transmitter.info3["Servicio"]["Ref1"]['@Len']):
                        message_wrong_length = {
                            "status": "La referencia tiene que tener una longitud de " +
                                      info_transmitter.info3["Servicio"]["Ref1"]['@Len']
                        }
                        RegisterSystemLog(idPersona=self.context["person_id"], type=1,
                                          endpoint=self.context["endpoint"],
                                          objJsonResponse=message_wrong_length)
                        raise serializers.ValidationError(message_wrong_length)

                    if attrs['trantype'] == "10":
                        if len(attrs['reference']) != 10:
                            message_wrong_length = {
                                "status": "La referencia tiene que tener una longitud de 10 dígitos"
                            }
                            RegisterSystemLog(idPersona=self.context["person_id"], type=1,
                                              endpoint=self.context["endpoint"],
                                              objJsonResponse=message_wrong_length)
                            raise serializers.ValidationError(message_wrong_length)

        # verificamos que el monto no sea negativo
        if attrs['monto'] <= 0:
            message_invalid_amount = {
                "status": "Ingrese un monto valido"
            }

            RegisterSystemLog(idPersona=self.context["person_id"], type=1,
                              endpoint=self.context["endpoint"],
                              objJsonResponse=message_invalid_amount)
            raise serializers.ValidationError(message_invalid_amount)
        # Verificar si es un pago de servicio o una recarga de saldo
        comision = 0
        cargo = 0
        if attrs['trantype'] == 10:  # Recarga
            monto_total = attrs['monto'] * 100
        elif attrs['trantype'] == 31:  # Pago de servicio
            # verificamos si el Trantype 32 regresa la comision y el cargo, si no lo hace ponemos la comision y el cargo en 0
            if 'Comision' in info_transmitter.info3["Servicio"]:
                comision = int(info_transmitter.info3["Servicio"]["Comision"])  # transformamos sus centavos a pesos
                comision = int(comision / 100)
            if 'Cargo' in info_transmitter.info3["Servicio"]:
                cargo = int(info_transmitter.info3["Servicio"]["Cargo"])
                cargo = int(cargo / 100)
            monto_total = attrs['monto'] + comision
        else:
            message_invalid_trantype = {
                "status": "Ingresa un Trantype valido"
            }

            RegisterSystemLog(idPersona=self.context["person_id"], type=1,
                              endpoint=self.context["endpoint"],
                              objJsonResponse=message_invalid_trantype)
            raise serializers.ValidationError(message_invalid_trantype)

        self.Cargo = cargo
        self.Comision = comision

        instance_cuenta = cuenta.objects.filter(cuenta=attrs['cuenta'])

        if attrs['trantype'] == 10:  # Recarga
            if (monto_total / 100) > instance_cuenta[0].monto:
                message_not_enough_funds = {
                    "status": "La cuenta no tiene fondos suficientes para el pago"
                }

                RegisterSystemLog(idPersona=self.context["person_id"], type=1,
                                  endpoint=self.context["endpoint"],
                                  objJsonResponse=message_not_enough_funds)
                raise serializers.ValidationError(message_not_enough_funds)

        if attrs['trantype'] == 31:  # Recarga
            # verificar que el usuario tiene el dinero suficiente
            if monto_total > instance_cuenta[0].monto:
                message_not_enough_funds = {
                    "status": "La cuenta no tiene fondos suficientes para el pago"
                }

                RegisterSystemLog(idPersona=self.context["person_id"], type=1,
                                  endpoint=self.context["endpoint"],
                                  objJsonResponse=message_not_enough_funds)
                raise serializers.ValidationError(message_not_enough_funds)

        # Verificar que el Token sea el mismo de la BD
        instance_persona = persona.objects.get(id=instance_cuenta[0].persona_cuenta_id)
        # deciframos el token de la base de datos
        decrypt_token = encdec_nip_cvc_token4dig(accion="2", area="BE", texto=instance_persona.token)
        if attrs['token'] != decrypt_token['data']:
            message_wrong_token = {
                "status": "Token incorrecto"
            }
            RegisterSystemLog(idPersona=self.context["person_id"], type=1,
                              endpoint=self.context["endpoint"],
                              objJsonResponse=message_wrong_token)
            raise serializers.ValidationError(message_wrong_token)
        return attrs

    def create(self, validated_data):
        comision = 0
        cargo = 0
        ticket = 0
        instance_emisor = Transmitter.objects.filter(id_transmitter=validated_data['Emisor']).first()
        importe = int(validated_data['monto'] * 100)
        if validated_data['trantype'] == 10:  # Recarga
            response, ticket = solicita({
                "TranType": 10,
                "Emisor": validated_data['Emisor'],
                "Importe": importe,
                "sRef1": validated_data['reference']
            })
        elif validated_data['trantype'] == 31:
            comision = self.Comision * 100
            cargo = self.Cargo * 100
            response, ticket = solicita({
                "TranType": 31,
                "Emisor": validated_data['Emisor'],
                "Importe": importe,
                "Comision": comision,
                "Cargo": cargo,
                "sRef1": validated_data['reference']
            })

        instance_cuenta: cuenta = cuenta.objects.filter(cuenta=validated_data['cuenta']).first()
        # verificamos que la transaccion es exitosa para descontar el dinero
        if response.solicitaResult == 0:
            # Descontar el monto total de la cuenta
            monto_total = validated_data['monto'] + comision / 100
            instance_cuenta.monto = instance_cuenta.monto - monto_total  # Cobro del servicio
            instance_cuenta.save()

        instance_code_efectiva = CodeEfectiva.objects.filter(code=response.solicitaResult)
        if len(instance_code_efectiva) <= 0:
            code_efectiva = 22
        else:
            code_efectiva = instance_code_efectiva[0].id

        # guardar el registro del pago en LogEfectiva
        log_efectiva_obj = LogEfectiva.objects.create_object(
            folio=response.Folio,
            autorization=response.Autorizacion,
            ticket=ticket,
            correspondent=438,  # Variable global
            transmitterid=validated_data['Emisor'],
            reference_one=validated_data['reference'],
            amount=validated_data['monto'] * 100,
            commission=comision,
            charge=cargo,
            code_id=code_efectiva,
            transmitter_rel_id=instance_emisor.id,
            user_rel_id=instance_cuenta.persona_cuenta_id
        )

        if response.solicitaResult == 0:
            # guardar el registro de la transaccion
            instance_persona = persona.objects.get(id=instance_cuenta.persona_cuenta_id)
            dict_transference = {
                "tipo": validated_data['trantype'],
                "nombre_servicio": instance_emisor.name_transmitter,
                "monto": validated_data['monto'],
                "referencia": validated_data['reference'],
                "nombre_emisor": instance_persona.get_full_name(),
                "cuentaclave": instance_cuenta.cuentaclave,
                "cuenta": instance_cuenta.cuenta,
                "cargo": cargo,
                "comision": comision / 100,
                "cuentatransferencia": instance_cuenta,
                "solicitaResult": response.solicitaResult,
                "email": instance_persona.email,
                "saldoRemanente": instance_cuenta.monto,
                "cuenta_emisor_id": instance_cuenta.id,
                "user_id": instance_cuenta.persona_cuenta_id,
            }

            # create_transference_register(dict_transference)
            # Crear movimientos transaccionales en el sistema Polipay
            emisor = GetInfoUser(dict_transference)
            ceco = CECORedEfectiva()
            efectiva = CreateTransactionRedEfectiva(dict_transference)
            CreateTransactionRedEfectivaComission(dict_transference, ceco, emisor, self.context.get("log"), efectiva)
            CreateTransactionRedEfectivaComissionSinClabe(dict_transference, ceco, emisor, self.context.get("log"),
                                                          efectiva)

        # guardar como servicio frecuente si is_frequent esta en true
        if validated_data['is_frequent']:
            # checamos si ya esta marcado como favorito
            instance_frequent = Frequents.objects.filter(transmmiter_Rel_id=instance_emisor.id,
                                                         user_rel_id=instance_cuenta.persona_cuenta_id)
            if len(instance_frequent) <= 0:  # si no esta registrado lo guardamos como favorito
                Frequents.objects.create(transmmiter_Rel_id=instance_emisor.id,
                                         user_rel_id=instance_cuenta.persona_cuenta_id)

        return response, log_efectiva_obj


class SerializerFrequentTransmitterOut(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    family = serializers.CharField()
    id_transmitter = serializers.IntegerField()
    name_transmitter = serializers.CharField()
    short_name = serializers.CharField()
    description = serializers.CharField()
    presence = serializers.CharField()
    acept_partial_payment = serializers.BooleanField()
    max_amount = serializers.FloatField()
    image = serializers.FileField(allow_null=True, required=False)
    fees = serializers.SerializerMethodField()
    reference = serializers.SerializerMethodField()
    trantype = serializers.SerializerMethodField()

    def get_reference(self, obj: reference):
        query = TransmitterHaveReference.objects.filter(transmitter_id=obj.id)
        return SerializerTransmitterHaveReferenceOut(query, many=True).data

    def get_fees(self, obj: fees):
        query = Fee.objects.filter(transmitter_id=obj.id)
        return SerializerFee(query, many=True).data

    def get_trantype(self, obj: trantype):
        query = TransmitterHaveTypes.objects.filter(transmitter_id=obj.id).values('type__number')
        List = [data['type__number'] for data in query]
        return List


class SerializerCheckBalanceRedEfectiva(serializers.Serializer):
    TranType = serializers.IntegerField()
    Emisor = serializers.CharField()
    sRef1 = serializers.CharField(required=False, allow_null=True)

    def validate(self, attrs):
        url: str = self.context["endpoint"]
        instance_emisor = Transmitter.objects.filter(id_transmitter=attrs['Emisor'])

        # Verifica que exista en el emisor en nuestra DB
        if len(instance_emisor) <= 0:
            err = {"status": "Id Emisor no encontrado"}
            RegisterSystemLog(idPersona=self.context["person_id"], type=1, endpoint=url, objJsonResponse=err)
            raise serializers.ValidationError(err)

        if attrs['TranType'] != 30:
            err = {"status": "Ingresa un Trantype valido"}
            RegisterSystemLog(idPersona=self.context["person_id"], type=1, endpoint=url, objJsonResponse=err)
            raise serializers.ValidationError(err)
        return attrs

    def create(self, **kwargs):
        return solicita({
            "TranType": self.validated_data['TranType'],
            "Emisor": self.validated_data['Emisor'],
            "sRef1": self.validated_data['sRef1']
        })


class SerializerCheckCommissionRedEfectiva(serializers.Serializer):
    TranType = serializers.IntegerField()
    Emisor = serializers.CharField()

    def validate(self, attrs):
        url: str = self.context["endpoint"]
        instance_emisor = Transmitter.objects.filter(id_transmitter=attrs['Emisor'])

        # Verifica que exista en el emisor en nuestra DB
        if len(instance_emisor) <= 0:
            err = {"status": "Id Emisor no encontrado"}
            # RegisterSystemLog(idPersona=self.context["person_id"], type=1, endpoint=url, objJsonResponse=err)
            raise serializers.ValidationError(err)

        if attrs['TranType'] != 32:
            err = {"status": "Ingresa un Trantype valido"}
            # RegisterSystemLog(idPersona=self.context["person_id"], type=1, endpoint=url, objJsonResponse=err)
            raise serializers.ValidationError(err)

        return attrs

    def create(self, **kwargs):
        return solicita({
            "TranType": self.validated_data['TranType'],
            "Emisor": self.validated_data['Emisor']
        })
