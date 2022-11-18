import datetime
import json
from os import remove

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files import File
from typing import Dict, Any

from rest_framework.serializers import *
from MANAGEMENT.Utils.utils import create_file
from MANAGEMENT.Utils.utils import PDFBase64File, random_password
from apps.solicitudes.management import get_number_attempts
from apps.solicitudes.models import Solicitudes
from apps.transaction.models import bancos
from apps.users.management import filter_data_or_return_none
from apps.users.models import persona, grupoPersona, domicilio, documentos, cuenta, TDocumento, tarjeta
from rest_framework import serializers
from drf_extra_fields.fields import Base64FileField


# from MANAGEMENT.Utils.utils import random_password
# from apps.users.management import generate_password, filter_object_if_exist


# (ChrGil 2022-03-02) creacion de solicitudes genericas
from polipaynewConfig.inntec import get_actual_state
from polipaynewConfig.settings import rfc_Bec


class SerializerDocumentsOut(Serializer):
    id = CharField()
    documento = FileField()


# (ChrGil 2022-03-02) Serializador para la creación de un cliente externo fisico
class SerializerClienteExternoFisico(Serializer):
    name = CharField()
    apellido_paterno = CharField(write_only=True)
    apellido_materno = CharField(write_only=True)
    last_name = CharField(read_only=True)
    email = CharField()
    rfc = CharField(allow_null=True)
    phone = CharField()

    def validate_name(self, value: str) -> str:
        return value.title()

    def validate_last_name(self, value: str) -> str:
        return value.title()

    def validate_email(self, value: str) -> str:
        if persona.objects.filter(email=value).exists():
            raise ValidationError('Dirección de correo electronico no valido o ya existe')

        return value.lower()

    def validate_rfc(self, value: str) -> str:
        _rfc_default: str = rfc_Bec
        if value is None:
            return _rfc_default
        elif len(value) != 13:
            raise ValidationError("Para una persona física, el RFC debe contener 13 caracteres alfanumericos.")
        return value

    def validate(self, attrs):
        apellido_paterno = (attrs['apellido_paterno'])
        apellido_materno = (attrs['apellido_materno'])

        attrs['last_name'] = f'{apellido_paterno} {apellido_materno}'
        return attrs

    def create(self, **kwargs) -> persona:
        self.validated_data.pop('apellido_paterno')
        self.validated_data.pop('apellido_materno')
        return persona.objects.create_cliente_externo_fisico(**self.validated_data)


# (ChrGil 2022-03-02) Crear domicilio de un cliente fisico
class SerializerCreateAddressClienteFisico(Serializer):
    codigopostal = IntegerField()
    colonia = CharField()
    alcaldia_mpio = CharField()
    estado = CharField()
    calle = CharField()
    pais = CharField()
    no_exterior = CharField(allow_null=True, allow_blank=True)
    no_interior = CharField(allow_null=True, allow_blank=True)

    def validate(self, attrs):
        return attrs

    def create(self, person_id: int) -> None:
        domicilio.objects.create_address(**self.validated_data, person_id=person_id)

    def update(self, instance, *args, **kwargs):
        instance.codigopostal = self.validated_data.get('codigopostal', instance.codigopostal)
        instance.colonia = self.validated_data.get('colonia', instance.colonia)
        instance.alcaldia_mpio = self.validated_data.get('alcaldia_mpio', instance.alcaldia_mpio)
        instance.estado = self.validated_data.get('estado', instance.estado)
        instance.calle = self.validated_data.get('calle', instance.calle)
        instance.no_exterior = self.validated_data.get('no_exterior', instance.no_exterior)
        instance.no_interior = self.validated_data.get('no_interior', instance.no_interior)
        instance.pais = self.validated_data.get('pais', instance.pais)
        instance.save()
        return instance


# (ChrGil 2022-03-02) Crear cuenta de un cliente fisico
class SerializerCreateAccountClienteFisico(Serializer):
    person_id = IntegerField()
    product_id = IntegerField()
    clabe = CharField()
    cuenta = CharField(read_only=True)

    def validate(self, attrs):
        attrs['cuenta'] = attrs.get('clabe')[7:17]
        return attrs

    def create(self, **kwargs) -> None:
        cuenta.objects.create_account(**self.validated_data)


# (ChrGil 2022-03-02) serializador para crear un documento de documentos
class SerializerDocumentClienteExternoFisicoIn(Serializer):
    documento = PDFBase64File(allow_null=False, required=True)
    tdocumento_id = IntegerField(required=False)
    person_id = IntegerField(read_only=True)

    def validate(self, attrs):
        attrs['person_id'] = self.context.get('person_id')
        attrs['status'] = "C"
        attrs['authorization'] = 1
        attrs['dateauth'] = datetime.datetime.now()
        attrs['userauth_id'] = self.context.get('user_authorize_id')
        return attrs

    def create(self, **kwargs) -> documentos:
        return documentos.objects.create(**self.validated_data)


class SerializerUpdateExternoFisico(Serializer):
    name = CharField()
    apellido_paterno = CharField(write_only=True)
    apellido_materno = CharField(write_only=True)
    last_name = CharField(read_only=True)
    email = CharField()
    rfc = CharField(allow_null=True)
    phone = CharField()

    def validate_name(self, value: str) -> str:
        return value.title()

    def validate_last_name(self, value: str) -> str:
        return value.title()

    def validate_rfc(self, value: str) -> str:
        _rfc_default: str = rfc_Bec
        if value is None:
            return _rfc_default
        elif len(value) != 13:
            raise ValidationError("Para una persona física, el RFC debe contener 13 caracteres alfanumericos.")
        return value

    def validate(self, attrs):
        apellido_paterno = (attrs['apellido_paterno'])
        apellido_materno = (attrs['apellido_materno'])

        attrs['last_name'] = f'{apellido_paterno} {apellido_materno}'
        return attrs

    def update(self, instance):
        self.validated_data.pop('apellido_paterno')
        self.validated_data.pop('apellido_materno')

        instance.name = self.validated_data.get('name', instance.name)
        instance.last_name = self.validated_data.get('last_name', instance.last_name)
        instance.email = self.validated_data.get('email', instance.email)
        instance.rfc = self.validated_data.get('email', instance.rfc)
        instance.phone = self.validated_data.get('email', instance.phone)
        instance.save()
        return instance


class SerializerEditDocumentClienteExternoFisico(Serializer):
    document_id = IntegerField()
    owner = IntegerField()
    base64_file = CharField(allow_null=True)

    def validate(self, attrs):
        if attrs["base64_file"]:
            file_name = create_file(attrs['base64_file'], attrs['owner'])
            attrs['base64_file'] = file_name
        return attrs

    def amend(self, **kwargs):
        file = self.validated_data.pop('base64_file')

        if file:
            document_id = self.validated_data.pop('document_id')
            instance = documentos.objects.get(id=document_id)

            with open(file, 'rb') as document:
                instance.documento = File(document)
                instance.status = "C"
                instance.save()
            remove(file)


class SerializerDeleteClienteExterno(Serializer):
    motivo = CharField(allow_null=False, allow_blank=False, max_length=1000)

    def delete_extern_client(self, cliente, admin_company):
        documentos.objects.filter(person_id=cliente.id).update(historial=True)
        instance_cuenta = cuenta.objects.get(persona_cuenta_id=cliente.id)
        tarjeta.objects.filter(cuenta_id=instance_cuenta.id).update(statusInterno_id=6)
        cuenta.objects.filter(persona_cuenta_id=cliente.id).update(is_active=False)

        for query in admin_company:
            query.delete()

        cliente.motivo = str(cliente.motivo) + " Motivo: " + str(self.validated_data.get("motivo"))
        cliente.is_active = False
        cliente.state = False
        cliente.date_modify = datetime.datetime.now()
        cliente.save()
        return

class SerializerDetailPersonaExternaOut(Serializer):
    CostCenterInfo = SerializerMethodField()
    ExternClientInfo = SerializerMethodField()
    AccountInfo = SerializerMethodField()
    CardsInfo = SerializerMethodField()
    Documents = SerializerMethodField()

    def get_CostCenterInfo(self, obj: CostCenterInfo):
        person_instance = persona.objects.get(id=obj.empresa_id)
        account_instance = cuenta.objects.get(persona_cuenta=person_instance.id)
        return {
            'id': person_instance.id,
            'name': person_instance.name,
            'saldoDisponible': account_instance.monto,
            'Cuenta': account_instance.cuenta,
            'Clabe': person_instance.clave_traspaso
        }

    def get_ExternClientInfo(self, obj: ExternClientInfo):
        person_instance =persona.objects.get(id=obj.person_id)
        return {
            'id': person_instance.id,
            'Nombre': person_instance.name,
            'apellido': person_instance.last_name,
            'rfc': person_instance.rfc,
            'fechaNacimiento': person_instance.fecha_nacimiento,
            'email': person_instance.email,
        }

    def get_AccountInfo(self, obj: AccountInfo):
        person_instance = persona.objects.get(id=obj.person_id)
        account_instance =cuenta.objects.get(persona_cuenta=person_instance.id)
        return {
            'NumeroCuenta': account_instance.cuenta,
            'CuentaClabe': account_instance.cuentaclave,
            'SaldoCuenta': account_instance.monto
        }

    def get_CardsInfo(self, obj: CardsInfo):
        person_instance = persona.objects.get(id=obj.person_id)
        account_instance = cuenta.objects.get(persona_cuenta=person_instance.id)
        tarjeta_instance = tarjeta.objects.filter(cuenta_id=account_instance.id)

        lista = []
        for c in tarjeta_instance:
            data = {
                'id':c.id,
                'tarjeta': c.tarjeta,
                'status': c.is_active,
                "status_inntec": get_actual_state({"TarjetaID": c.TarjetaId})[0].get("Detalle"),
                "was_eliminated": c.was_eliminated,
                "deletion_date": c.deletion_date
            }
            lista.append(data)
        return lista

    def get_Documents(self, obj: Documents):
        instance = documentos.objects.filter(person_id=obj.person_id, historial=False, tdocumento_id=12)
        return SerializerDocumentsOut(instance, many=True).data
