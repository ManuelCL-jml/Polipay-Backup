import binascii
from os import remove
from typing import Tuple, NoReturn, Any, Dict

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files import File

from rest_framework.serializers import *

from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Utils.utils import create_file
from apps.transaction.exc import CardAlreadyExists, AccountAlreadyExists
from apps.users.models import persona, cuenta, grupoPersona, TDocumento, documentos, tarjeta


# (ChrGil 2021-12-07) Creación de la cuenta clabe de una razón social
class SerializerCreateAccount(Serializer):
    cuenta = CharField()
    persona_cuenta_id = IntegerField()
    numero_tarjeta = CharField(write_only=True)
    cuentaclave = CharField()

    def validate_numero_tarjeta(self, value: str) -> str:
        cuenta_beneficiario: Dict[str, Any] = tarjeta.objects.filter(tarjeta=value).values('cuenta_id').first()

        if cuenta_beneficiario:
            if cuenta_beneficiario.get('cuenta_id') is not None:
                raise CardAlreadyExists('Tarjeta ya asignada')
        return value

    def validate_cuentaclave(self, value: str) -> str:
        if cuenta.objects.filter(cuentaclave=value).exists():
            raise AccountAlreadyExists('La cuenta clave ya existe')
        return value

    def validate(self, attrs):
        return attrs

    def create(self, **kwargs) -> NoReturn:
        self.validated_data.pop('numero_tarjeta')
        cuenta.objects.create(**self.validated_data)


class SerializerAltaBeneficiario(Serializer):
    name = CharField()
    last_name = CharField(allow_null=True)
    birth_date = DateField()
    rfc = CharField()
    mail = EmailField()
    description_activities = CharField(allow_null=True)
    password = CharField()

    def validate_mail(self, value: str) -> str:
        if persona.objects.filter(email=value).exists():
            err = MyHttpError(message='Dirección de correo electrico no valido o ya existe', real_error=None)
            raise ValidationError(err.standard_error_responses())
        return value

    def validate(self, attrs):
        return attrs

    def create(self, **kwargs) -> int:
        return persona.objects.create_personal_externo(**self.validated_data)


class CreateGrupoPersona(Serializer):
    empresa_id = IntegerField()
    person_id = IntegerField()
    nombre_grupo = CharField()
    relacion_grupo_id = IntegerField()

    def validate(self, attrs):
        return attrs

    def create(self, **kwargs):
        grupoPersona.objects.create(**self.validated_data)


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
