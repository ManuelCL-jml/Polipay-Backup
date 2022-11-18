import datetime as dt
from os import remove
from typing import Dict, Any

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files import File
from django.db.models import Q
from rest_framework.serializers import *

from django.db import transaction

from MANAGEMENT.AlgSTP.algorithm_stp import GenerateNewClabeSTP
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Utils.utils import create_file, strftime, random_password
from apps.solicitudes.management import get_number_attempts
from apps.solicitudes.models import Solicitudes
from polipaynewConfig.exceptions import add_list_errors, ErrorsList
from apps.users.messages import createMessageWelcome
from apps.users.models import domicilio, persona, grupoPersona, cuenta, TDocumento, documentos
from apps.users.management import filter_object_if_exist, generate_password, get_Object_orList_error


class SerializerDomicilioIn(Serializer):
    codigopostal = IntegerField()
    colonia = CharField()
    alcaldia_mpio = CharField()
    estado = CharField()
    calle = CharField()
    pais = CharField(default=None, allow_null=True)
    no_exterior = CharField(allow_null=True, allow_blank=True)
    no_interior = CharField(allow_null=True, allow_blank=True)

    def create(self, **kwargs):
        return self.validated_data

    def create_address(self):
        domicilio.objects.create_address(**self.validated_data)

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


class SerializerRepresentanteLegalWebIn(Serializer):
    """
    Serializador de entrada de Representante Legal

    """

    name = CharField()
    a_paterno = CharField()
    a_materno = CharField(allow_null=True, default=None)
    email = EmailField()
    password = CharField(read_only=True)
    fecha_nacimiento = DateField()
    rfc = CharField()
    homoclave = CharField()
    phone = CharField()
    domicilio = SerializerDomicilioIn()
    is_admin = BooleanField(default=False)
    is_superuser = BooleanField(default=False)
    is_staff = BooleanField(default=False)

    def validate_name(self, value: str) -> str:
        return value.title()

    def validate_a_paterno(self, value: str) -> str:
        return value.title()

    def validate_a_materno(self, value: str) -> str:
        return value.title()

    def validate_email(self, value: str) -> str:
        return value.lower()

    def validate_rfc(self, value: str) -> str:
        return value.upper()

    def validate(self, attrs):
        list_errors = []
        attrs['password'] = random_password()

        if filter_object_if_exist(persona, email=attrs['email']):
            add_list_errors({'email': 'Dirección de correo electronico ya asignado'}, list_errors)

        if self.context['len_doc_rl'] != 3:
            add_list_errors({'documents': 'Faltan documentos para el representante legal'}, list_errors)

        if not self.context['is_admin_rl']:
            if self.context['num_admin'] == 0:
                add_list_errors({'admin': 'Como minimo debe de registrar un administrativo'}, list_errors)

        if self.context['is_admin_rl']:
            if self.context['num_admin'] > 4:
                add_list_errors({'email': 'Se llego al limite permitido de administradores'}, list_errors)

        if not self.context['is_admin_rl']:
            if self.context['num_admin'] > 5:
                add_list_errors({'email': 'Se llego al limite permitido de administradores'}, list_errors)

        if len(list_errors) > 0:
            raise ValidationError({'status': list_errors})

        return attrs

    def create(self, validated_data):
        return validated_data


class SerializerGeneralGrupoPersonaIn(Serializer):
    """
    Serializador de genral de entrada para grupo de persona

    """

    id = IntegerField(read_only=True)
    person_id = IntegerField(read_only=True)
    empresa_id = IntegerField(read_only=True)
    is_admin = BooleanField()
    nombre_grupo = CharField(read_only=True)
    relacion_grupo_id = IntegerField(read_only=True)
    addworker = BooleanField()
    delworker = BooleanField(read_only=True)

    def validate(self, attrs):
        attrs['person_id'] = self.context['instance_rl']
        attrs['empresa_id'] = self.context['instance']['id']
        attrs['nombre_grupo'] = self.context['instance']['name']
        #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
        #       Para la Cuenta Eje (PPCE)
        if int(self.context['type']) == 0:
            attrs['relacion_grupo_id']  = 1
        #       Para el centro de costos concentrador (ccc)
        else:
            attrs['relacion_grupo_id']  = 4
        attrs['delworker'] = True
        return attrs


# (ChrGil 2021-10-18) Se crea una solicitud de apertura de centro de costos
class SerializerCrearSolicitudIn(Serializer):
    nombre = CharField()
    tipoSolicitud_id = IntegerField()
    personaSolicitud_id = IntegerField()
    estado_id = IntegerField(default=1)
    intentos = IntegerField(read_only=True)

    def validate(self, attrs):
        attrs["intentos"] = get_number_attempts(attrs['personaSolicitud_id'], Solicitudes, attrs['tipoSolicitud_id'])
        return attrs

    def create(self, **kwargs):
        return Solicitudes.objects.create(**self.validated_data)


# (ChrGil 2021-12-07) Crear un grupo persona para relacionar la razón social y el representante legal
# (ChrGil 2021-12-07) y relacionar el centro de costos y el cliente moral
class SerializerGrupoPersona(Serializer):
    person_id = IntegerField()
    empresa_id = IntegerField()
    nombre_grupo = CharField()
    relacion_grupo_id = IntegerField()

    def validate(self, attrs):
        return attrs

    def create(self, **kwargs):
        grupoPersona.objects.create(**self.validated_data)


# (ChrGil 2021-12-07) Creación de la cuenta clabe de una razón social
class SerializerCreateAccount(Serializer):
    cuenta = CharField(read_only=True)
    persona_cuenta_id = IntegerField()
    cuentaclave = CharField(read_only=True)

    def validate(self, attrs):
        try:
            clabe = GenerateNewClabeSTP(self.context['empresa_id']).clabe
        except (ValueError, Exception) as e:
            err = MyHttpError("Se llego al limite permitido de cuentas clabe", str(e))
            raise ValidationError(err.standard_error_responses())
        else:
            attrs['cuentaclave'] = clabe
            attrs['cuenta'] = clabe[7:17]
            return attrs

    def create(self, **kwargs):
        return cuenta.objects.create(**self.validated_data)


# (ChrGil 2021-12-07) Serializador para la creación de un documento tipo PDF
class SerializerDocuments(Serializer):
    tipo = IntegerField()
    owner = IntegerField()
    comment = CharField(allow_null=True)
    base64_file = CharField()

    def validate(self, attrs):
        try:
            obj: TDocumento = TDocumento.objects.get(id=attrs['tipo'])
        except (ObjectDoesNotExist, FieldDoesNotExist, MultipleObjectsReturned) as e:
            err = MyHttpError('Tipo de documento no valido', str(e))
            raise ValidationError(err.standard_error_responses())
        else:
            if attrs['comment'] is None:
                attrs['comment'] = obj.descripcion

            file_name = create_file(attrs['base64_file'], attrs['owner'])
            attrs['base64_file'] = file_name

        return attrs

    def create(self, **kwargs):
        file = self.validated_data.pop('base64_file')
        instance = documentos.objects.create_document(**self.validated_data)

        with open(file, 'rb') as document:
            instance.documento = File(document)
            instance.save()
        remove(file)


# (ChrGil 2021-12-07) Serializador para la creación de un representante legal que es una persona Fisica
class SerializerRepresentanteLegal(Serializer):
    nombre = CharField(max_length=80)
    paterno = CharField(max_length=80)
    materno = CharField(max_length=80, allow_null=True, default=None)
    nacimiento = DateField()
    rfc = CharField(max_length=13)
    homoclave = CharField(max_length=4, allow_null=True, default=None)
    email = CharField(max_length=254)
    telefono = CharField(max_length=14)
    list_errors = ErrorsList()

    def errors_list_clear(self) -> None:
        self.list_errors.clear_list()

    def validate_email(self, value: str) -> str:
        self.errors_list_clear()

        person_info = persona.objects.filter(email=value).values('email').first()
        if person_info:
            if person_info.get('email') == value:
                return value

        if persona.objects.filter(email=value).exists():
            ErrorsList('email', value, message='Asegúrese de que su email sea valido o que no este registrado')
        return value

    def validate_telefono(self, value: str) -> str:
        # if not ("+" in value):
        #     ErrorsList('telefono', value, message='Asegúrese de que la LADA sea valida')
        return value

    def validate(self, attrs):
        if len(self.list_errors.show_errors_list()) > 0:
            raise ValidationError(self.list_errors.standard_error_responses())
        return attrs

    def create(self, **kwargs) -> int:
        return persona.objects.create_representante(**self.validated_data).get_only_id()


# (ChrGil 2021-12-07) Serializador que se encarga de crear la razón social de un cliente Moral
class SerializerRazonSocial(Serializer):
    razon_social = CharField(max_length=80)
    giro = CharField(max_length=30, allow_null=True, default=None)
    rfc = CharField(max_length=13)
    fecha_constitucion = DateField(allow_null=True, default=dt.date.today())
    clb_interbancaria_uno = CharField(max_length=18, allow_null=True, default=None)
    clabeinterbancaria_dos = CharField(max_length=18, allow_null=True, default=None)
    centro_costos_name = CharField(max_length=80, allow_null=True, default=None)
    list_errors = ErrorsList()

    def errors_list_clear(self) -> None:
        self.list_errors.clear_list()

    def validate_razon_social(self, value: str) -> str:
        self.errors_list_clear()

        # if persona.objects.filter(name=value).exists():
        #     message = 'Asegúrese de que el nombre de la razón social sea valido o que no este registrado'
        #     ErrorsList('razon_social', value, message=message)
        return value

    def validate_clb_interbancaria(self, value: str) -> str:
        # if persona.objects.filter(Q(clabeinterbancaria_uno=value) | Q(clabeinterbancaria_dos=value)).exists():
        #     ErrorsList('clb_interbancaria', value, message='Asegúrese de que su clabe interbancaria sea valida')
        return value

    def validate(self, attrs):
        if len(self.list_errors.show_errors_list()) > 0:
            raise ValidationError(self.list_errors.standard_error_responses())
        return attrs

    def create(self, **kwargs) -> Dict[str, Any]:
        return persona.objects.create_razon_social_v2(**self.validated_data).get_cuenta_eje()


# (ChrGil 2021-10-12) Nueva versión del serializador para crear un domicilio
class SerializerCreateAddress(Serializer):
    codigopostal = IntegerField()
    colonia = CharField()
    alcaldia_mpio = CharField()
    estado = CharField()
    calle = CharField()
    pais = CharField()
    no_exterior = CharField(allow_null=True, allow_blank=True)
    no_interior = CharField(allow_null=True, allow_blank=True)
    domicilioPersona_id = IntegerField()

    def validate(self, attrs):
        return attrs

    def create(self, **kwargs) -> None:
        domicilio.objects.create(**self.validated_data)

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
