from rest_framework import serializers

from apps.contacts.api.movil.serializers.Group_serializer import serializerGrupoOutV2, serializerGrupoOutV1
from apps.contacts.models import *
from apps.contacts.serializer import serializerTipo_transferenciaOut
from apps.users.models import persona
from apps.transaction.models import tipo_transferencia
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser


class SerializerContactIn(serializers.Serializer):
    nombre = serializers.CharField()
    cuenta = serializers.CharField()
    banco = serializers.IntegerField(allow_null=True)
    alias = serializers.CharField(allow_null=True)

    def validate_banco(self,data):
        if data != None:
            Num_bancos = bancos.objects.filter(id=data)
            if len(Num_bancos) != 0:
                return data
            else:
                return serializers.ValidationError("Id de banco no encontrada")
        else:
            return data

    def createContact(self, validated_data, instanceP,instanceTC):
        contacto = contactos.objects.create(**validated_data, person=instanceP,tipo_contacto=instanceTC)
        return contacto


class SerializerContactsOut(serializers.Serializer):
    id = serializers.ReadOnlyField()
    nombre = serializers.CharField()
    cuenta = serializers.CharField()
    banco = serializers.IntegerField()
    alias = serializers.CharField()
    tipo_contacto = serializers.SerializerMethodField()

    def get_tipo_contacto(self,obj:tipo_contacto):
        queryTC = tipo_transferencia.objects.filter(contactos__id=obj.id)
        return serializerTipo_transferenciaOut(queryTC,many=True).data

class SerializerContactsOutV2(serializers.Serializer):
    contacts = serializers.SerializerMethodField()

    def get_contacts(self, obj:contacts):
        queryset = contactos.objects.filter(person_id=obj.id)
        return SerializerContactsOut(queryset, many=True).data


class SerializerEditContactIn(serializers.Serializer):
    id = serializers.ReadOnlyField()
    nombre = serializers.CharField()
    cuenta = serializers.CharField()
    banco = serializers.CharField(allow_null=True)
    tipo_contacto_id = serializers.IntegerField()
    alias = serializers.CharField(allow_null=True)

    def validate_banco(self,data):
        if data != None:
            Num_bancos = bancos.objects.filter(id=data)
            if len(Num_bancos) != 0:
                return data
            else:
                return serializers.ValidationError("Id de banco no encontrada")
        else:
            return data

    def validate_tipo_contacto_id(self,data):
        TCId = tipo_transferencia.objects.filter(id=data)
        if len(TCId) !=0:
            return data
        else:
            raise serializers.ValidationError("Id no encontrada")

    def update(self, instance, validated_data):

        instance.nombre = validated_data.get("nombre",instance.nombre)
        instance.cuenta = validated_data.get("cuenta",instance.cuenta)
        instance.banco = validated_data.get("banco",instance.banco)
        instance.alias = validated_data.get("alias",instance.alias)
        instance.tipo_contacto_id = validated_data.get("tipo_contacto_id", instance.tipo_contacto_id)
        instance.save()
        return instance



class SerializerPersonContactOut(serializers.Serializer):
    id = serializers.ReadOnlyField()
    email = serializers.CharField()
    username = serializers.CharField()
    is_superuser = serializers.BooleanField()
    is_client = serializers.BooleanField()
    genero = serializers.CharField()
    fecha_nacimiento = serializers.DateField()
    name = serializers.CharField()
    last_name = serializers.CharField()
    is_new = serializers.BooleanField()
    last_login = serializers.DateTimeField()
    date_joined = serializers.DateTimeField()
    contacts = serializers.SerializerMethodField()

    def get_contacts(self,obj:contacts):
        queryset = contactos.objects.filter(person_id=obj.id)
        return SerializerContactsOut(queryset, many=True).data

class SerializerPersonGroupOut(serializers.Serializer):
    id = serializers.ReadOnlyField()
    email = serializers.CharField()
    username = serializers.CharField()
    is_superuser = serializers.BooleanField()
    is_client = serializers.BooleanField()
    genero = serializers.CharField()
    fecha_nacimiento = serializers.DateField()
    name = serializers.CharField()
    last_name = serializers.CharField()
    is_new = serializers.BooleanField()
    last_login = serializers.DateTimeField()
    date_joined = serializers.DateTimeField()
    grupos = serializers.SerializerMethodField()


    def get_grupos(self,obj:grupos):
        queryset = contactos.objects.filter(person_id=obj.id)
        grupos_list = []
        for contac in queryset:
            querygrupocontac = grupoContacto.objects.filter(contacts_id=contac.id)
            for grupocontac in querygrupocontac:
                querygroup = grupo.objects.get(id=grupocontac.group_id)
                grupos_list.append(querygroup)
        return serializerGrupoOutV1(grupos_list,many=True).data



# -------- (ChrAvaBus Mar16.11.2021) v3 --------

class SerializerCreateFrequentAccounts(serializers.Serializer):
    nombre				= serializers.CharField()
    cuenta				= serializers.CharField()
    banco				= serializers.IntegerField(allow_null=True)
    email				= serializers.CharField(allow_null=True)
    is_favorite			= serializers.BooleanField(default=True)
    person				= serializers.IntegerField()
    alias				= serializers.CharField(allow_null=True)
    tipo_contacto		= serializers.IntegerField()
    rfc_beneficiario	= serializers.CharField(allow_null=True)
    is_active			= serializers.BooleanField(default=True)

    def validate_banco(self, value):
        if value != None:
            Num_bancos = bancos.objects.filter(id=value)
            if len(Num_bancos) != 0:
                return value
            else:
                msg = LanguageRegisteredUser(self.initial_data.get("person"), "Fre002BE")
                raise serializers.ValidationError({"status": msg})
                #return serializers.ValidationError("Id de banco no encontrada")
        else:
            return value

    def createFrequent(self, validated_data, instanceP,instanceTC):
        frequent	= contactos.objects.create(
		    nombre=validated_data["nombre"],
			cuenta=validated_data["cuenta"],
			banco=validated_data["banco"],
			email=validated_data["email"],
			is_favorite=validated_data["is_favorite"],
			person=instanceP,
			alias=validated_data["alias"],
			tipo_contacto=instanceTC,
			rfc_beneficiario=validated_data["rfc_beneficiario"],
			is_active=validated_data["is_active"]
		)
        return frequent

    def updateFrequent(self, validated_data, instance, instanceTC):
        instance.nombre			= validated_data.get("nombre",instance.nombre)
        instance.cuenta			= validated_data.get("cuenta",instance.cuenta)
        instance.banco			= validated_data.get("banco",instance.banco)
        instance.alias			= validated_data.get("alias",instance.alias)
        instance.tipo_contacto	= instanceTC
        instance.save()
        return instance



