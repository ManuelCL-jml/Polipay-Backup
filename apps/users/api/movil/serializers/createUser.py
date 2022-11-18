from django.contrib.auth.hashers import make_password, check_password

# Modualos nativos
from rest_framework import serializers

# Modulos locales
from apps.users.models import *
from apps.users.management import *
from apps.users.messages import *
from apps.contacts.models import *
from apps.contacts.api.movil.serializers.Contacts_serializer import SerializerContactsOut




class serializerUserWalletIn(serializers.Serializer):
	name = serializers.CharField()
	email = serializers.CharField()
	password = serializers.CharField()
	fecha_nacimiento = serializers.DateField()
	phone = serializers.CharField()
	token = serializers.CharField(allow_null=True,allow_blank=True)
	tipo_persona = serializers.IntegerField()
	last_name = serializers.CharField()

	def validate(self, attrs):
		query = persona.objects.filter(email=attrs['email'])
		query_tpersona = t_persona.objects.filter(id=attrs['tipo_persona'])

		if len(query) != 0:
			raise serializers.ValidationError({"status": "Correo ya ha sido registrado"})
		if len(query_tpersona) == 0:
			raise serializers.ValidationError({"status": "Tipo de persona no encontrada"})
		else:
			return attrs

	def save(self):
		instance = persona.objects.create_client(**self.validated_data)
		return instance


class serializerCuentaWalletIn(serializers.Serializer):
	email = serializers.CharField()
	tarjeta = serializers.IntegerField()
	tipo_cuenta_id = serializers.IntegerField()
	cvc = serializers.CharField(allow_blank=True)
	fechaexp = serializers.DateField(allow_null=False, default=None)
	alias = serializers.CharField(allow_null=False)

	def validate(self, attrs):
		instance = persona.objects.get(email=attrs['email'])
		query = cuenta.objects.filter(tarjeta=attrs['tarjeta'])
		if len(query) != 0:
			counts = cuenta.objects.filter(persona_cuenta=instance)
			if len(counts) == 0:
				instance.delete()
			raise serializers.ValidationError({"status": "Tarjeta ya ha sido registrada"})
		return attrs

	def save(self, instance):
		try:
			instanceAccount = cuenta.objects.create(
				cuenta = Code_card(16),
				monto = 0,
				is_active = True,
				persona_cuenta_id = instance.id,
				tarjeta = self.validated_data.get('tarjeta'),
				nip = 1234,
				cuentaclave = Code_card(18),
				do = True,
				autorize = False,
				state = True,
				doaut = False,
				tipo_cuenta_id = self.validated_data.get('tipo_cuenta_id'),
				cvc = self.validated_data.get('cvc'),
				fechaexp = self.validated_data.get('fechaexp'),
				alias = self.validated_data.get('alias')
			)
			return instanceAccount
		except Exception as inst:
			counts = cuenta.objects.filter(persona_cuenta=instance)
			if len(counts) == 0:
				instance.delete()
			raise serializers.ValidationError({"Status": [inst]})

class serializerPutUserWalletChangeStatusIn(serializers.Serializer):
	status = serializers.BooleanField()

class serializerEditPasswordIn(serializers.Serializer):
	password = serializers.CharField()
	email = serializers.CharField()
	passwordNew = serializers.CharField()
	passwordNewConfirm = serializers.CharField()


	def validate(self,data):
		email = data["email"]
		password = data["password"]
		passwordNew = data["passwordNew"]
		passwordNewConfirm = data["passwordNewConfirm"]
		if passwordNew == passwordNewConfirm:
			emails = persona.objects.filter(email=email)
			if len(emails) > 0:
				pwd = emails[0].check_password(password)
				if pwd:
					return data
				else:
					raise serializers.ValidationError("datos erroneos")
			else:
				raise serializers.ValidationError("Email no encontrado")
		else:
			raise serializers.ValidationError("Contraseñas no coinciden")

	def update(self, instance, validated_data):
		instance.set_password(validated_data.get("passwordNew"))
		instance.save()
		return instance
