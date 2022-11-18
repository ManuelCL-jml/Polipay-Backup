import datetime

from rest_framework.serializers import *

from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.EndPoint.EndPointInfo import get_info
from apps.contacts.models import contactos, HistoricoContactos, CatOperaciones, grupoContacto
from apps.transaction.models import tipo_transferencia, bancos
from apps.users.management import get_Object_orList_error
from apps.users.models import persona


class SerializerFrecuentContacts(Serializer):
    nombre = CharField()
    cuenta = CharField()
    email = EmailField(allow_null=True, allow_blank=True)
    banco = IntegerField()
    rfc_beneficiario = CharField(allow_null=True, allow_blank=True)
    alias = CharField()
    is_favorite = BooleanField()

    def validate(self, attrs):
        contacto = contactos.objects.values('cuenta', 'id', 'nombre', 'is_active').filter(
            person_id=self.context['person_id'])
        for i in contacto:
            if str(attrs['cuenta']) == i['cuenta'] and i['is_active'] == False:
                R = {'code': 400,
                     'status': 'Error',
                     'messague': 'El contacto frecuente ya fue eliminado anteriormente, ¿Deseas Registrarlo de nuevo?',
                     'detail': i['id']}
                RegisterSystemLog(idPersona=self.context['user_log'], type=1, endpoint=self.context['endpoint'],
                                  objJsonRequest=R)
                raise ValidationError(R)

            if str(attrs['cuenta']) == i['cuenta'] and i['is_active'] == True:
                R = {'code': 400,
                     'status': 'Error',
                     'messague': 'Ya existe un contacto frecuente registrado con esta cuenta'}

                RegisterSystemLog(idPersona=self.context['user_log'], type=1, endpoint=self.context['endpoint'],
                                  objJsonRequest=R)
                raise ValidationError(R)
        return attrs

    def create(self, **kwargs):
        contacto = contactos.objects.create(
            nombre=self.validated_data.get('nombre'),
            cuenta=self.validated_data.get('cuenta'),
            email=self.validated_data.get('email'),
            banco=self.validated_data.get('banco'),
            rfc_beneficiario=self.validated_data.get('rfc_beneficiario'),
            alias=self.validated_data.get('alias'),
            person_id=self.context['person_id'],
            tipo_contacto_id=2,
            is_favorite=self.validated_data.get('is_favorite'),
        )

        return contacto


class AddFrecuentContactToGroup(Serializer):
    contacts_id = IntegerField(read_only=True)
    group_id = IntegerField()

    def validate(self, attrs):
        last_contacts = contactos.objects.last()
        attrs['contacts_id'] = last_contacts.id
        return attrs

    def create_contact_without_group(self, validated_data):
        return grupoContacto.objects.bulk_create(**validated_data)

    def create(self, lista_objects_contacts):
        return grupoContacto.objects.bulk_create(lista_objects_contacts)


class UpdateFrecuentContactToGroup(Serializer):
    contacts_id = IntegerField(read_only=True)
    group_id = IntegerField()

    def validate(self, attrs):
        attrs['contacts_id'] = self.context['contact']
        return attrs

    def create_contact_without_group(self, validated_data):
        return grupoContacto.objects.bulk_create(**validated_data)

    def create(self, lista_objects_contacts):
        return grupoContacto.objects.bulk_create(lista_objects_contacts)


class SerializerUpdateFrecuentConctact(Serializer):
    nombre = CharField()
    cuenta = CharField()
    email = EmailField(allow_blank=True, allow_null=True)
    banco = IntegerField()
    rfc_beneficiario = CharField(allow_blank=True, allow_null=True)
    alias = CharField()
    is_favorite = BooleanField()

    def update(self, instance, validated_data):
        instance.nombre = validated_data.get('nombre', instance.nombre)
        instance.cuenta = validated_data.get('cuenta', instance.cuenta)
        instance.email = validated_data.get('email', instance.email)
        instance.banco = validated_data.get('banco', instance.banco)
        instance.rfc_beneficiario = validated_data.get('rfc_beneficiario', instance.rfc_beneficiario)
        instance.alias = validated_data.get('alias', instance.alias)
        instance.is_favorite = validated_data.get('is_favorite', instance.is_favorite)
        instance.save()


class SerializerAddHistoryContact(Serializer):
    def create_history_contact(self, **kwargs):
        usuario = self.context['Usuario']
        operacion_create = CatOperaciones.objects.get(id=1)
        history_contact = HistoricoContactos.objects.create(
            usuario_id=usuario,
            datos='',
            operacion=operacion_create,
            contactoRel_id=self.context['contactoRel']
        )
        return history_contact

    def update_history_contact(self, instance, validated_data):
        operacion_update = CatOperaciones.objects.get(id=2)
        instance.fechaRegistro = datetime.datetime.now()
        instance.operacion_id = operacion_update
        instance.save()

    def delete_history_contact(self, instance, validated_data):
        operacion_delete = CatOperaciones.objects.get(id=3)
        instance.fechaRegistro = datetime.datetime.now()
        instance.operacion_id = operacion_delete
        instance.save()

    def reactivate_contact(self, instance, validated_data):
        operacion_delete = CatOperaciones.objects.get(id=4)
        instance.fechaRegistro = datetime.datetime.now()
        instance.operacion_id = operacion_delete
        instance.save()


class SerializerDeleteFrecuentContact(Serializer):
    is_active = BooleanField()

    def update(self, instance, validated_data):
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.save()


class SerializerMakeOrBreakFrecuentContact(Serializer):
    is_favorite = BooleanField()

    def update(self, instance, validated_data):
        instance.is_favorite = validated_data.get('is_favorite', instance.is_favorite)
        instance.save()


class SerializerDetailFrecuentContact(Serializer):
    id = IntegerField()
    nombre = CharField()
    cuenta = IntegerField()
    banco = SerializerMethodField()
    email = CharField()
    is_favorite = BooleanField()
    is_active = BooleanField()
    alias = CharField()
    rfc_beneficiario = CharField()

    def get_banco(self, obj: banco):
        bank_instance = get_Object_orList_error(bancos, id=obj.banco)
        return bank_instance.institucion
