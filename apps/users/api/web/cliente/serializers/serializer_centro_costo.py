import datetime
import json
from os import remove
from typing import Any, Dict

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from django.core.files import File
from django.db.transaction import atomic

from rest_framework import serializers
from rest_framework.serializers import *
from MANAGEMENT.Utils.utils import create_file


# from apps.solicitudes.management import get_number_attempts
# from apps.solicitudes.models import Solicitudes
from MANAGEMENT.Utils.utils import PDFBase64File, create_file
from apps.solicitudes.models import Solicitudes
from apps.users.messages import sendNotificationEditFiscalAddress, sendNotificationEditClaveTraspaso
from polipaynewConfig.exceptions import ErrorsList, filter_Object_Or_Error
from apps.transaction.models import bancos
from apps.users.management import create_pdf_data, generate_password, get_Object_orList_error, \
    filter_all_data_or_return_none
from apps.users.models import persona, grupoPersona, domicilio, documentos, TDocumento
from MANAGEMENT.Language.LanguageUnregisteredUser import LanguageUnregisteredUser
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.EndPoint.EndPointInfo import get_info


# (ChrGil 2021-12-08) Se comenta de manera temporal
# class CreateBankAccount(Serializer):
#     cuenta = CharField(read_only=True)
#     is_active = BooleanField(read_only=True)
#     persona_cuenta_id = IntegerField()
#     cuentaclave = CharField(read_only=True)
#
#     def validate(self, attrs):
#         list_errors = ErrorsList()
#         list_errors.clear_list()
#
#         new_cuentaclave, is_valid = generate_cuentaclave(cuenta_eje_id=self.context['empresa_id'])
#
#         if not is_valid:
#             ErrorsList('cuentaclave', None, message='Se llego al limite de clabes interbancarias')
#
#         if is_valid:
#             attrs['cuentaclave'] = new_cuentaclave
#             attrs['cuenta'] = get_account(new_cuentaclave)
#             attrs['is_active'] = False
#
#         return attrs
#
#     def create(self, **kwargs):
#         return cuenta.objects.create(**self.validated_data)

# (ChrGil 2021-12-08) Se comenta de manera temporal
# class SerializerGrupoPersona(Serializer):
#     person_id = IntegerField()
#     empresa_id = IntegerField()
#     is_admin = BooleanField(default=False)
#     nombre_grupo = CharField()
#     relacion_grupo_id = IntegerField()
#     addworker = BooleanField(default=False)
#     delworker = BooleanField(default=False)
#
#     def create(self, **kwargs):
#         return grupoPersona.objects.create(**self.validated_data).get_only_id_empresa()


# (AAF 2021-12-08) modificado para la vista updateCentroCostos
class SerializerDocument(Serializer):
    tdocumento_id = IntegerField(required=False)
    documento = CharField()
    comentario = CharField(allow_null=True, allow_blank=True, default=None)
    person_id = IntegerField(required=False)
    # status = CharField(required=False)
    id = IntegerField(required=False)

    def validate(self, attrs):
        return attrs

    def create(self, **kwargs):
        try:
            with atomic():
                instance_document = documentos.objects.create(**self.validated_data)
                file = self.validated_data.get("documento")

                create_pdf_data(file)
                with open('TEMPLATES/Files/file.pdf', 'rb') as document:
                    instance_document.documento = File(document)
                    instance_document.save()
                return instance_document
        except TypeError as e:
            raise ValidationError({
                "error": "Ocurrio un error durante el proceso de creación del domicilio",
                "detail": f"{e}"
            })

    # (AAF 2021-12-08)
    def update(self, validated_data):
        try:
            instance_document = documentos.objects.get(id=validated_data['id'])
        except TypeError as e:
            raise ValidationError({
                "error": "Ocurrio un error al actualizar el documento",
                "detail": f"{e}"
            })
        if 'documento' in validated_data:
            with open('TEMPLATES/Files/file.pdf', 'rb') as document:
                instance_document.documento = File(document)
        instance_document.status = 'P'
        instance_document.comentario = ''
        instance_document.load = datetime.datetime.today()
        instance_document.dateupdate = datetime.datetime.today()
        instance_document.save()
        return True


# (ChrGil 2021-10-12) Serializador para la validación y creacion de un representante legal
# (ChrGil 2021-12-08) Se comenta codigo temporalmente
# class SerializerLegalRepresentative(Serializer):
#     name = CharField()
#     a_paterno = CharField(write_only=True)
#     a_materno = CharField(write_only=True)
#     email = EmailField()
#     password = CharField(read_only=True)
#     last_name = CharField(read_only=True)
#     fecha_nacimiento = DateField()
#     rfc = CharField()
#     homoclave = CharField()
#     phone = CharField()
#     list_errors = ErrorsList()
#
#     def errors_list_clear(self):
#         self.list_errors.clear_list()
#
#     def validate_email(self, value):
#         self.errors_list_clear()
#         exists = persona.objects.filter(email=value).exists()
#         if exists:
#             ErrorsList('Email', value, message='Dirección de correo electronico ya registrado')
#
#         if len(value) > 253:
#             ErrorsList('Email', value, message='Longitud maxima de 253 caracteres')
#         return value
#
#     def validate_rfc(self, value):
#         exists = persona.objects.filter(rfc=value).exists()
#         if exists:
#             ErrorsList('rfc', value, message='Asegúrese de que este campo no haya sido registrado.')
#
#         if len(value) > 13:
#             ErrorsList('rfc', value, message='Asegúrese de que este campo no tenga más de 13 caracteres.')
#         return value
#
#     def validate_phone(self, value):
#         exists = persona.objects.filter(phone=value).exists()
#         if exists:
#             ErrorsList('phone', value, message='Numero telefonico no valido o ya fue registrado.')
#
#         if len(value) > 14:
#             ErrorsList('phone', value, message='Longitud maxima de 10 caracteres')
#         return value
#
#     def validate_homoclave(self, value):
#         if len(value) > 4:
#             ErrorsList('homoclave', value, message='Longitud maxima de 4 caracteres')
#         return value
#
#     def validate(self, attrs):
#         if len(self.list_errors.show_errors_list()) > 0:
#             raise ValidationError(self.list_errors.standard_error_responses())
#
#         attrs['last_name'] = f"{attrs['a_paterno']} {attrs['a_materno']}"
#         attrs['password'] = generate_password(attrs['last_name'], attrs['phone'])
#         self.list_errors.clear_list()
#         return attrs
#
#     def create(self, validated_data):
#         return persona.objects.create_representante_legal(**validated_data).get_only_id()


# (ChrGil 2021-10-11) Serializador para validar y crear un centro de costos
# (ChrGil 2021-12-08) Se comenta codigo temporalmente
# class SerializerCostCenter(Serializer):
#     centro_costo = CharField()
#     razon_social = CharField()
#     rfc = CharField()
#     banco_clabe = CharField()
#     clave_traspaso = CharField()
#     list_errors = ErrorsList()
#
#     def errors_list_clear(self):
#         self.list_errors.clear_list()
#
#     def validate_centro_costo(self, value):
#         self.errors_list_clear()
#         exists = persona.objects.filter(name=value).exists()
#         if exists:
#             ErrorsList('name', value, message='El nombre del centro de costos ya existe')
#
#         if len(value) > 80:
#             ErrorsList('name', value, message='Asegúrese de que este campo no tenga más de 80 caracteres.')
#         return value
#
#     def validate_rfc(self, value):
#         exists = persona.objects.filter(rfc=value).exists()
#         if exists:
#             ErrorsList('rfc', value, message='Este RFC ya ha sido registrado.')
#
#         if len(value) > 13:
#             ErrorsList('banco_clabe', value, message='Asegúrese de que este campo no tenga más de 13 caracteres.')
#         return value
#
#     def validate_banco_clabe(self, value):
#         exists = bancos.objects.filter(clabe=value).exists()
#         if not exists:
#             ErrorsList('banco_clabe', value, message='Banco no valido o no encontrado.')
#
#         if len(value) > 13:
#             ErrorsList('banco_clabe', value, message='Asegúrese de que este campo no tenga más de 13 caracteres.')
#         return value
#
#     def validate_clave_traspaso(self, value):
#         exists = persona.objects.filter(clave_traspaso=value).exists()
#         if exists:
#             ErrorsList('clabe_traspaso', value, message='Esta clave ya ha sido registrada.')
#
#         if len(value) > 16:
#             ErrorsList('clave_traspaso', value, message='Asegúrese de que este campo no tenga más de 16 caracteres.')
#         return value
#
#     def validate(self, attrs):
#         cuenta_eje = grupoPersona.objects.filter(person_id=self.context['admin_id']).values('empresa__is_active')
#
#         if len(cuenta_eje) == 0:
#             message = 'No perteneces a esta empresa o no cuentas con los permisos necesarios para realizar esta acción'
#             ErrorsList('null', 'null', message=message)
#
#             if len(self.list_errors.show_errors_list()) > 0:
#                 raise ValidationError(self.list_errors.standard_error_responses())
#
#         if not cuenta_eje[0]['empresa__is_active']:
#             message = 'No es posible crear un centro de costos hasta que su cuenta eje no este activada'
#             ErrorsList('centro_costo', value='No data', message=message)
#
#         if len(self.list_errors.show_errors_list()) > 0:
#             raise ValidationError(self.list_errors.standard_error_responses())
#
#         self.list_errors.clear_list()
#         return attrs
#
#     def create(self, validated_data):
#         instance = persona.objects.create_centro_costo(**validated_data)
#         return instance.get_only_id()


# (ChrGil 2021-10-18) Serializador para validar los datos de un centro de costo y representante legal
# (ChrGil 2021-12-08) Se comenta codigo de manera temporal
# class SerializerCreateCostCenter(Serializer):
#     company = SerializerCostCenter()
#     legal_representative = SerializerLegalRepresentative()


class SerializerRenderingDocuments(Serializer):
    documento = FileField()

    class Meta:
        fields = ['documento']


class SerializerDetailCentroCostoOut(Serializer):
    name = CharField(read_only=True)
    last_name = CharField(read_only=True)
    clave_traspaso = CharField(read_only=True)
    rfc = CharField(read_only=True)
    banco_clabe = SerializerMethodField()
    fdomicilio = SerializerMethodField()
    person_file = SerializerMethodField()

    def get_banco_clabe(self, obj: banco_clabe):
        instance_banco = get_Object_orList_error(bancos, clabe=obj.banco_clabe)
        return {
            'banco': instance_banco.institucion
        }

    def get_fdomicilio(self, obj: fdomicilio):
        instance_domicilio = get_Object_orList_error(domicilio, id=obj.fdomicilio_id)
        return {
            'id': instance_domicilio.id,
            'codigopostal': instance_domicilio.codigopostal,
            'colonia': instance_domicilio.colonia,
            'alcaldia_mpio': instance_domicilio.alcaldia_mpio,
            'estado': instance_domicilio.estado,
            'calle': instance_domicilio.calle,
            'no_exterior': instance_domicilio.no_exterior,
            'no_interior': instance_domicilio.no_interior,
            'pais': instance_domicilio.pais
        }

    def get_person_file(self, obj: person_file):
        document = documentos.objects.filter(person=obj.id)
        list_data = []
        for d in document:
            data = {
                'type': d.tdocumento,
                'document': d.documento.url,
                'status': d.status
            }
            list_data.append(data)
        return list_data


# Modificar
class SerialiazerListarCentroCostos(Serializer):
    empresa_id = SerializerMethodField()
    person_document = SerializerMethodField()

    def get_empresa_id(self, obj: empresa_id):
        person_instance = get_Object_orList_error(persona, id=obj.empresa_id)
        return {
            'id': person_instance.id,
            'name': person_instance.name,
            'date_joined': person_instance.date_joined
        }

    def get_person_document(self, obj: person_document):
        person_instance = get_Object_orList_error(persona, id=obj.person_id)
        documento = filter_all_data_or_return_none(documentos, person_id=person_instance.id, historial=False)

        lista = []
        for i in documento:

            if i.authorization == 1:
                lista.append(i.status)
                if lista.count('C') == 7:
                    return ({'status': 'AUTORIZADO'})

            if i.authorization == 0:
                lista.append(i.status)

                if lista.count('P') == 7:
                    return ({'status': 'PENDIENTE'})

            if i.authorization == 0:
                lista.append(i.status)

                if lista.count('D') >= 1:
                    return ({'status': 'DEVUELTO'})


class SerializerListCentroCostosOut(Serializer):
    id = ReadOnlyField()
    name = CharField()
    last_name = CharField()
    rfc = CharField()
    RepresentanteLegal = SerializerMethodField()
    DomicilioFiscal = SerializerMethodField()
    DatosTransferenciaFinal = SerializerMethodField()

    #
    def get_RepresentanteLegal(self, obj: RepresentanteLegal):
        queryset = filter_Object_Or_Error(grupoPersona, relacion_grupo=4, empresa_id=obj.id)
        datos = []
        for data in queryset:
            instance = persona.objects.get(id=data.person_id)
            datos.append(instance)
        return SerializerRepresentanteLegalOut(datos, many=True).data

    #
    def get_DomicilioFiscal(self, obj: DomicilioFiscal):
        queryGP = grupoPersona.objects.get(empresa_id=obj.id)
        queryPL = persona.objects.get(id=queryGP.person_id)
        instance = domicilio.objects.filter(domicilioPersona_id=queryPL.id)
        return SerializerAddressOut(instance, many=True).data

    #
    def get_DatosTransferenciaFinal(self, obj: DatosTransferenciaFinal):
        queryset = persona.objects.get(id=obj.id)
        instance = bancos.objects.get(clabe=obj.banco_clabe)
        return {
            'institucion': instance.institucion,
            'clave_traspaso': queryset.clave_traspaso
        }


class SerializerRepresentanteLegalOut(Serializer):
    id = ReadOnlyField()
    name = SerializerMethodField()
    email = CharField()
    phone = CharField()

    def get_name(self, obj: name):
        return obj.get_full_name()


class SerializerAddressOut(Serializer):
    id = ReadOnlyField()
    codigopostal = CharField()
    colonia = CharField()
    alcaldia_mpio = CharField()
    estado = CharField()
    calle = CharField()
    no_exterior = CharField()
    no_interior = CharField()
    pais = CharField()


class SerializerGetCenterCostOut(Serializer):
    clave_traspaso = CharField(allow_null=True)
    banco_clabe = CharField()

    def update_centroCostos(self, instance):
        instance.clave_traspaso = self.validated_data.get("clave_traspaso", instance.clave_traspaso)
        instance.banco_clabe = self.validated_data.get("banco_clabe", instance.banco_clabe)
        instance.save()
        return True


# (AAF 2021-12-08)
class SerializerCC(Serializer):
    id = IntegerField(required=False)
    nombre = CharField(required=False)
    claveTraspaso = CharField(required=False)
    bancoClave = CharField(required=False)
    razonSocial = CharField(required=False)
    rfc = CharField(required=False)
    cp = CharField(required=False)
    colonia = CharField(required=False)
    mpio = CharField(required=False)
    edo = CharField(required=False)
    calle = CharField(required=False)
    noExt = CharField(required=False)
    noInt = CharField(required=False)
    pais = CharField(required=False)

    def update(self, instance, validated_data):
        # actualizamos instancia persona
        if 'nombre' in validated_data:
            instance.nombre = validated_data['nombre']
        if 'claveTraspaso' in validated_data:
            instance.claveTraspaso = validated_data['claveTraspaso']
        if 'bancoClave' in validated_data:
            instance.bancoClave = validated_data['bancoClave']
        if 'razonSocial' in validated_data:
            instance.last_name = validated_data['razonSocial']
        if 'rfc' in validated_data:
            instance.rfc = validated_data['rfc']
        instance.save()

        # actualizamos domiclio
        instDom = domicilio.objects.get(domicilioPersona=instance, historial=False)
        if 'cp' in validated_data:
            instDom.codigopostal = validated_data['cp']
        if 'colonia' in validated_data:
            instDom.colonia = validated_data['colonia']
        if 'mpio' in validated_data:
            instDom.alcaldia_mpio = validated_data['mpio']
        if 'edo' in validated_data:
            instDom.estado = validated_data['edo']
        if 'calle' in validated_data:
            instDom.calle = validated_data['calle']
        if 'noExt' in validated_data:
            instDom.no_exterior = validated_data['noExt']
        if 'noInt' in validated_data:
            instDom.no_interior = validated_data['noInt']
        instDom.dateUpdate = datetime.datetime.now()
        instDom.save()
        return instance

    ###  (AAF 2021-12-13) baja de centro de costos
    def delete(self, instance):
        instance.state = False
        instance.save()
        return True


# (AAF 2021-12-08) representante legal para centro de costos
class CCRepresentanteLegalIn(Serializer):
    id = IntegerField()  # posible required False
    last_name = CharField(required=False)
    name = CharField(required=False)
    fecha_nacimiento = DateField(required=False)
    email = EmailField(required=False)
    phone = CharField(required=False)

    def update(self, validated_data):
        try:
            instance = persona.objects.get(id=validated_data['id'])
        except TypeError as e:
            raise ValidationError({
                "error": "Ocurrio un error al obtener el Representante legal",
                "detail": f"{e}"
            })
        if 'last_name' in validated_data:
            instance.last_name = validated_data['last_name']
        if 'name' in validated_data:
            instance.name = validated_data['name']
        if 'fecha_nacimiento' in validated_data:
            instance.fecha_nacimiento = validated_data['fecha_nacimiento']
        if 'email' in validated_data:
            instance.email = validated_data['email']
        if 'phone' in validated_data:
            instance.phone = validated_data['phone']
        instance.save()
        return instance


# (AAF 2021-12-09) serializador de documentos
class SerializerDocumentIn(Serializer):
    # tdocumento_id = IntegerField(required=False)
    documento = PDFBase64File(allow_null=False, required=True)
    comentario = CharField(required=False, default=None)
    person_id = IntegerField(required=False)
    # status = CharField(required=False)
    id = IntegerField(required=False)

    def create(self, validated_data, idPerson):
        try:
            instance = documentos.objects.create(person_id=idPerson, **validated_data)
        except:
            return False
        return instance

    def validate(self, attrs):
        return attrs

    # (AAF 2021-12-08)
    def update(self, validated_data):
        try:
            instance_document = documentos.objects.get(id=validated_data['id'])
        except TypeError as e:
            raise ValidationError({
                "error": "Ocurrio un error al actualizar el documento",
                "detail": f"{e}"
            })
        if 'documento' in validated_data:
            instance_document.documento.delete()
            instance_document.documento = validated_data['documento']
        instance_document.status = 'P'
        instance_document.comentario = ''
        instance_document.load = datetime.datetime.today()
        instance_document.dateupdate = datetime.datetime.today()
        instance_document.save()
        return instance_document


class SerializerCreateDocumentSolicitud(Serializer):
    tipo = IntegerField()
    owner = IntegerField()
    comment = CharField(default=None)
    base64_file = CharField()

    def validate(self, attrs):
        try:
            obj: TDocumento = TDocumento.objects.get(id=attrs['tipo'])
        except (ObjectDoesNotExist, FieldDoesNotExist, MultipleObjectsReturned) as e:
            raise ValueError('Tipo de documento no valido')
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


# (ChrGil 2022-03-10) Serializador que se encarga de crear la razón social de un cliente Moral
class SerializerAmendRazonSocial(Serializer):
    cost_center_name = CharField()
    cost_center_razon_social = CharField()
    rfc = CharField()
    # banco = CharField()
    # clave_traspaso = CharField()
    list_errors = ErrorsList()

    def validate_cost_center_name(self, value: str) -> str:
        return value.title()

    def validate_cost_center_razon_social(self, value: str) -> str:
        person_info = persona.objects.filter(id=self.context.get('cost_center')).values('last_name').first()

        if person_info:
            if person_info.get('last_name') == value:
                return value

        # if persona.objects.filter(name=value).exists():
        #     message = 'Asegúrese de que el nombre de la razón social sea valido o que no se encuentre registrado'
        #     raise ValueError(message)
        # return value.title()

    def validate_rfc(self, value: str) -> str:
        return value.upper()

    # def validate_banco(self, value: str) -> str:
    #     return value
    #
    # def validate_clave_traspaso(self, value: str) -> str:
    #     return value

    def validate(self, attrs):
        return attrs

    def amend(self, **kwargs):
        persona.objects.update_cost_center(**self.validated_data, cost_center_id=self.context.get('cost_center_id'))


# (ChrGil 2021-12-07) Serializador para la creación de un representante legal que es una persona Fisica
class SerializerAmendRepresentanteLegal(Serializer):
    nombre = CharField(max_length=80)
    paterno = CharField(max_length=80)
    materno = CharField(max_length=80, allow_null=True, default=None)
    nacimiento = DateField()
    rfc = CharField(max_length=13)
    homoclave = CharField(max_length=4)
    email = CharField(max_length=254)
    telefono = CharField(max_length=14)
    list_errors = ErrorsList()

    def errors_list_clear(self) -> None:
        self.list_errors.clear_list()

    # def validate_email(self, value: str) -> str:
    #     if persona.objects.filter(email=value).exists():
    #         raise ValueError("Asegúrese de que su email sea valido o que no este registrado")
    #     return value

    def validate_telefono(self, value: str) -> str:
        # if not ("+" in value):
        #     raise ValueError("Asegúrese de que la LADA sea valida")
        return value

    def validate(self, attrs):
        return attrs

    def amend(self, **kwargs):
        persona.objects.update_representante(**self.validated_data, representate_id=self.context.get('representate_id'))


# (ChrGil 2021-10-12) Nueva versión del serializador para crear un domicilio
class SerializerCorregirAddress(Serializer):
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

    def amend(self, **kwargs):
        domicilio.objects.filter(domicilioPersona_id=self.context.get('person_id')).update(
            **self.validated_data
        )


# (ChrGil 2022-03-08) corregir documentos
class SerializerAmendDocumentsCostCenter(Serializer):
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
            instance: documentos = documentos.objects.get(id=document_id)

            if instance.status == 'D':
                instance.status = 'P'

            with open(file, 'rb') as document:
                instance.documento = File(document)
                instance.save()
            remove(file)

    def create(self, **kwargs):
        file = self.validated_data.pop('base64_file')
        instance = documentos.objects.create_document(**self.validated_data)

        with open(file, 'rb') as document:
            instance.documento = File(document)
            instance.save()
        remove(file)


class SerializerSolicitudEditarDomicilioFiscal(Serializer):
    codigopostal = IntegerField(allow_null=False)
    colonia = CharField(allow_null=False)
    alcaldia_mpio = CharField(allow_null=False)
    estado = CharField(allow_null=False)
    calle = CharField(allow_null=False)
    no_exterior = IntegerField(allow_null=False)
    no_interior = IntegerField(allow_null=True)
    pais = CharField(allow_null=False)


    def create(self, validated_data):
        codigopostal = validated_data.get('codigopostal')
        colonia = validated_data.get('colonia')
        alcaldia_mpio = validated_data.get('alcaldia_mpio')
        estado = validated_data.get('estado')
        calle = validated_data.get('calle')
        no_exterior = validated_data.get('no_exterior')
        no_interior = validated_data.get('no_interior')
        pais = validated_data.get('pais')

        payload = {
            "cost_center_id": self.context['cost_center_info'].get('empresa_id'),
            "name": self.context['cost_center_info'].get('empresa__name'),
            "codigopostal": codigopostal,
            "colonia": colonia,
            "alcaldia_mpio": alcaldia_mpio,
            "estado": estado,
            "calle": calle,
            "no_exterior": no_exterior,
            "no_interior": no_interior,
            "pais": pais,
        }

        instance_solicitud = Solicitudes.objects.create(
            nombre="Editar Domicilio Fiscal Centro Costos",
            tipoSolicitud_id=19,
            personaSolicitud_id=self.context['PersonaSolicitudId'],
            estado_id=1,
            intentos=1,
            fechaChange=datetime.datetime.now(),
            dato_json=json.dumps(payload))

        sendNotificationEditFiscalAddress(
            self.context['admin'].get_full_name(),
            self.context['admin'].email,
            self.context['cost_center_info'].get('empresa__name'),
            instance_solicitud.estado.nombreEdo)
        return instance_solicitud


class SerializerEditarClaveTraspasoFinal(Serializer):
    clave_traspaso = CharField(allow_null=False)
    banco_clabe = CharField(allow_null=False)

    def create(self, validated_data):
        clave_traspaso = validated_data.get('clave_traspaso')
        banco_clabe = validated_data.get('banco_clabe')
        id = self.context['cost_center_info'].get('empresa_id')

        payload = {
            "cost_center_id": self.context['cost_center_info'].get('empresa_id'),
            "name": self.context['cost_center_info'].get('empresa__name'),
            "clave_traspaso": clave_traspaso,
            "banco_clabe": banco_clabe
        }

        instance_solicitud = Solicitudes.objects.create(
            nombre="Editar Clave Traspaso",
            tipoSolicitud_id=21,
            personaSolicitud_id=self.context['PersonaSolicitudId'],
            estado_id=1,
            intentos=1,
            fechaChange=datetime.datetime.now(),
            dato_json=json.dumps(payload))

        sendNotificationEditClaveTraspaso(
            self.context['admin'].get_full_name(),
            'jmlcalixtro98@gmail.com',
            self.context['cost_center_info'].get('empresa__name'),
            instance_solicitud.estado.nombreEdo)
        return instance_solicitud

# (2022-03-10 ChrAvaBus : Centro de costos)
"""
class SerializerCreateLegalRepresentativeCostCenter(serializers.Serializer):
    persona = serializers.IntegerField()
    tarjeta = serializers.IntegerField()
    alias   = serializers.CharField()

    def validate_persona(self, value):
        queryExistePersona  = persona.objects.filter(id=value).exists()
        if not queryExistePersona:
            msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd003")
            r   = {"status": msg}
            RegisterSystemLog(idPersona=-1, type=1, endpoint=get_info(self.context), objJsonResponse=r)
            raise serializers.ValidationError(r)
        return value

    def validate_tarjeta(self, value):
        queryExisteTarjeta  = tarjeta.objects.filter(tarjeta=value).exists()
        if not queryExisteTarjeta:
            msg = LanguageRegisteredUser(self.initial_data.get("persona"), "Das005BE")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.initial_data.get("persona"), type=1, endpoint=get_info(self.context), objJsonResponse=r)
            raise serializers.ValidationError(r)
        return value

    def validate(self, data):
        queryCuenta     = cuenta.objects.filter(persona_cuenta_id=data["persona"]).values("id")
        queryPertenece  = tarjeta.objects.filter(cuenta_id=queryCuenta[0]["id"], tarjeta=data["tarjeta"]).exists()
        if not queryPertenece:
            msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd005")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.initial_data.get("persona"), type=1, endpoint=get_info(self.context), objJsonResponse=r)
            raise serializers.ValidationError(r)
        else:
            queryTarjeta    = tarjeta.objects.filter(cuenta_id=queryCuenta[0]["id"], tarjeta=data["tarjeta"]).values("id")
            data["idCard"]  = queryTarjeta[0]["id"]
        return data

    def deleteCard(self, data):
        instance                = get_Object_orList_error(tarjeta, id=data["idCard"])
        instance.deletion_date  = datetime.now()
        instance.was_eliminated = True
        instance.status         = "28"
        instance.is_active      = False
        response    = change_status(instance.TarjetaId, "28", "Bloqueada ")
        if response[1] == 200 and response[0]["Respuesta"] == 0:
            instance.save()
        elif response[1] == 200 and response[0]["Respuesta"] == 1:
            msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd006")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.initial_data.get("persona"), type=1, endpoint=get_info(self.context), objJsonResponse=r)
            raise serializers.ValidationError(r)
        elif response[1] == 400 or response[1] == 500:
            msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd007")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.initial_data.get("persona"), type=1, endpoint=get_info(self.context), objJsonResponse=r)
            raise serializers.ValidationError(r)
"""


# (2022-03-10 ChrAvaBus : Centro de costos)
class SerializerListLegalRepresentativeCostCenter(serializers.Serializer):
    idCentroCosto   = serializers.IntegerField()
    type            = serializers.IntegerField()

    def validate_idCentroCosto(self, value):
        if int(value) < 1 or int(value) > 3:
            r = {
                "code": "[400]",
                "status": "ERROR",
                "detail": [
                    {
                        "data": "idCentroCosto",
                        "field": int(self.initial_data.get("idCentroCosto")),
                        "message": "Introduzca un id correcto."
                    }
                ]
            }
            raise serializers.ValidationError(r)

        if int(self.initial_data.get("type")) == 1:  # 1=Centro de costos
            queryExisteCC = persona.objects.filter(id=value, tipo_persona_id=1).exists()
            if not queryExisteCC:
                # msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd003")
                # r   = {"status": }
                # RegisterSystemLog(idPersona=-1, type=1, endpoint=get_info(self.context), objJsonResponse=r)
                r = {
                    "code": "[400]",
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": value,
                            "message": "El Centro de costos no existe o no está registrado de forma correcta."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

            queryLegalRepGP = grupoPersona.objects.filter(empresa_id=value, person_id__isnull=False, relacion_grupo_id=4).exists()
            if not queryLegalRepGP:
                r = {
                    "code": "[400]",
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": value,
                            "message": "No existe relacion del centro de costos con el representante legal."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

        elif int(self.initial_data.get("type")) == 2:  # 2=Representante Legal
            queryExisteRL = persona.objects.filter(id=value).exists()
            if not queryExisteRL:
                # msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd003")
                # r   = {"status": }
                # RegisterSystemLog(idPersona=-1, type=1, endpoint=get_info(self.context), objJsonResponse=r)
                r = {
                    "code": "[400]",
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": value,
                            "message": "No existe representante legal."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

            queryLegalRepGP = grupoPersona.objects.filter(empresa_id__isnull=False, person_id=value, relacion_grupo_id=4).exists()
            if not queryLegalRepGP:
                r = {
                    "code": "[400]",
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": value,
                            "message": "No existe relacion del representante legal con el centro de costos."
                        }
                    ]
                }
                raise serializers.ValidationError(r)
        else:
            r = {
                "code": "[400]",
                "status": "ERROR",
                "detail": [
                    {
                        "data": "type",
                        "field": int(self.initial_data.get("type")),
                        "message": "Valor para llave type incorrecto, puede ser 1 o 2."
                    }
                ]
            }
            raise serializers.ValidationError(r)

        return value

    def validate_type(self, value):
        if int(value) < 1 or int(value) > 3:
            r = {
                "code": "[400]",
                "status": "ERROR",
                "detail": [
                    {
                        "data": "type",
                        "field": int(self.initial_data.get("type")),
                        "message": "Valor para type incorrecto, puede ser 1 o 2."
                    }
                ]
            }
            raise serializers.ValidationError(r)
        return value

    def validate(self, data):
        if int(self.initial_data.get("type")) == 1:  # 1=Centro de costos
            queryExisteCCAndLR  = grupoPersona.objects.filter(empresa_id=data["idCentroCosto"], person_id__isnull=False, relacion_grupo_id=4).exists()
            if not queryExisteCCAndLR:
                r = {
                    "code": "[400]",
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": data["idCentroCosto"],
                            "message": "Centro de costos no tiene representante legal."
                        }
                    ]
                }
                raise serializers.ValidationError(r)
        elif int(self.initial_data.get("type")) == 2:  # 2=Representante Legal
            queryExisteCCAndLR = grupoPersona.objects.filter(empresa_id__isnull=False, person_id=data["idCentroCosto"],
                                                             relacion_grupo_id=4).exists()
            if not queryExisteCCAndLR:
                r = {
                    "code": "[400]",
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": data["idCentroCosto"],
                            "message": "Representante legal no pertenece a un Centro de costos."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

        return data

    def getInfoCostCenter(self, idCostCenter, data):
        queryInfoCostCenter = dict
        if int(data["type"]) == 1:  # 1=Centro de costos
            # Recupera y devuelve la info del centro de costos y su representante legal
            queryInfoCostCenter = persona.objects.filter(id=data["idCentroCosto"], tipo_persona_id=1).values(
                "id",
                "email", "name", "last_name", "username", "rfc", "phone", "tipo_persona_id",
                "tipo_persona_id__tPersona")

            if len(queryInfoCostCenter) == 0:
                r = {
                    "code": "[400]",
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": data["idCentroCosto"],
                            "message": "Sin registro para centro de costo."
                        }
                    ]
                }
                raise serializers.ValidationError(r)
        elif int(self.initial_data.get("type")) == 2:  # 2=Representante Legal
            # Recupera id del CC
            queryidCC   = grupoPersona.objects.filter(person_id=data["idCentroCosto"], relacion_grupo_id=4).values(
                "empresa_id")

            if len(queryidCC) == 0:
                r = {
                    "code": "[400]",
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": data["idCentroCosto"],
                            "message": "Sin registro para Representante Legal."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

            # Recupera y devuelve la info del centro de costos y su representante legal
            queryInfoCostCenter = persona.objects.filter(id=queryidCC[0]["empresa_id"], tipo_persona_id=1).values(
                "id",
                "email", "name", "last_name", "username", "rfc", "phone", "tipo_persona_id",
                "tipo_persona_id__tPersona")

            if len(queryInfoCostCenter) == 0:
                r = {
                    "code": "[400]",
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": data["idCentroCosto"],
                            "message": "No existe centro de costo."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

        return  queryInfoCostCenter

    def getInfoLegalRep(self, idLegalRep, data):

        if int(data["type"]) == 1:  # 1=Centro de costos

            queryLegalRep = grupoPersona.objects.filter(empresa_id=data["idCentroCosto"], relacion_grupo_id=4).values(
                "person_id")

            if len(queryLegalRep) == 0:
                r = {
                    "code": "[400]",
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": data["idCentroCosto"],
                            "message": "Centro de costos no existe."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

        elif int(self.initial_data.get("type")) == 2:  # 2=Representante Legal

            queryLegalRep = grupoPersona.objects.filter(person_id=data["idCentroCosto"], relacion_grupo_id=4).values(
                "person_id")

            if len(queryLegalRep) == 0:
                r = {
                    "code": "[400]",
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": data["idCentroCosto"],
                            "message": "Centro de costos no existe."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

        queryPersona    = persona.objects.filter(id=queryLegalRep[0]["person_id"]).values("id",
            "email", "name", "last_name", "username", "rfc", "phone", "tipo_persona_id", "tipo_persona_id__tPersona")
        if len(queryPersona ) == 0:
            r = {
                "code": "[400]",
                "status": "ERROR",
                "detail": [
                    {
                        "data": "idCentroCosto",
                        "field": data["idCentroCosto"],
                        "message": "No existe representante legal."
                    }
                ]
            }
            raise serializers.ValidationError(r)

        return queryPersona

    def listLegalRep(self, data):
        objJsonCC   = self.getInfoCostCenter(data["idCentroCosto"], data)
        objJsonLR   = self.getInfoLegalRep(data["idCentroCosto"], data)

        objJson = {
            "centroCosto": {
                "id": objJsonCC[0]["id"],
                "email": objJsonCC[0]["email"],
                "name": objJsonCC[0]["name"],
                "last_name": objJsonCC[0]["last_name"],
                "username": objJsonCC[0]["username"],
                "rfc": objJsonCC[0]["rfc"],
                "phone": objJsonCC[0]["phone"],
                "idTipoPersona": objJsonCC[0]["tipo_persona_id"],
                "tipoPersona": objJsonCC[0]["tipo_persona_id__tPersona"]
            },
            "repLegal": {
                "id": objJsonLR[0]["id"],
                "email": objJsonLR[0]["email"],
                "name": objJsonLR[0]["name"],
                "last_name": objJsonLR[0]["last_name"],
                "username": objJsonLR[0]["username"],
                "rfc": objJsonLR[0]["rfc"],
                "phone": objJsonLR[0]["phone"],
                "idTipoPersona": objJsonLR[0]["tipo_persona_id"],
                "tipoPersona": objJsonLR[0]["tipo_persona_id__tPersona"]
            }
        }

        return objJson


# (2022-03-10 ChrAvaBus : Centro de costos)
class SerializerDeleteLegalRepresentativeCostCenter(serializers.Serializer):
    idCentroCosto   = serializers.IntegerField()
    type            = serializers.IntegerField()

    def validate_idCentroCosto(self, value):
        if int(self.initial_data.get("type")) == 1: # 1=Centro de costos
            queryExisteCC   = persona.objects.filter(id=value).exists()
            if not queryExisteCC:
                #msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd003")
                #r   = {"status": }
                #RegisterSystemLog(idPersona=-1, type=1, endpoint=get_info(self.context), objJsonResponse=r)
                r = {
                    "code": "[200]",
                    "status": "OK",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": value,
                            "message": "No existe centro de costo."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

            queryExisteCC2  = persona.objects.filter(id=value, tipo_persona_id=1).exists()
            if not queryExisteCC2:
                # msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd003")
                # r   = {"status": }
                # RegisterSystemLog(idPersona=-1, type=1, endpoint=get_info(self.context), objJsonResponse=r)
                r = {
                    "code": "[200]",
                    "status": "OK",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": value,
                            "message": "Existe centro de costo, pero no está registrado correctamente.\nTipo persona incorrecto."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

            queryLegalRepGP = grupoPersona.objects.filter(empresa_id=value, relacion_grupo_id=4).exists()
            if not queryLegalRepGP:
                r = {
                    "code": "[200]",
                    "status": "OK",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": value,
                            "message": "No existe relacion del centro de costos con el representante legal."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

        elif int(self.initial_data.get("type")) == 2: # 2=Representante Legal
            queryExisteRL   = persona.objects.filter(id=value).exists()
            if not queryExisteRL:
                # msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd003")
                # r   = {"status": }
                # RegisterSystemLog(idPersona=-1, type=1, endpoint=get_info(self.context), objJsonResponse=r)
                r = {
                    "code": "[200]",
                    "status": "OK",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": value,
                            "message": "No existe representante legal."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

            queryLegalRepGP = grupoPersona.objects.filter(person_id=value, relacion_grupo_id=4).exists()
            if not queryLegalRepGP:
                r = {
                    "code": "[200]",
                    "status": "OK",
                    "detail": [
                        {
                            "data": "idCentroCosto",
                            "field": value,
                            "message": "No existe relacion del representante legal con el centro de costos."
                        }
                    ]
                }
                raise serializers.ValidationError(r)
        else:
            r = {
                "code": "[200]",
                "status": "OK",
                "detail": [
                    {
                        "data": "type",
                        "field": int(self.initial_data.get("type")),
                        "message": "Valor para llave type incorrecto, puede ser 1 o 2."
                    }
                ]
            }
            raise serializers.ValidationError(r)

        return value

    def validate_type(self, value):
        if int(value) < 1 or int(value) > 3:
            r = {
                "code": "[200]",
                "status": "OK",
                "detail": [
                    {
                        "data": "type",
                        "field": int(self.initial_data.get("type")),
                        "message": "Valor para type incorrecto, puede ser 1 o 2."
                    }
                ]
            }
            raise serializers.ValidationError(r)
        return value

    def validate(self, data):
        return data

    def deleteLegalRep(self, data):
        """
        instance                = get_Object_orList_error(tarjeta, id=data["idCard"])
        instance.deletion_date  = datetime.now()
        instance.was_eliminated = True
        instance.status         = "28"
        instance.is_active      = False
        response    = change_status(instance.TarjetaId, "28", "Bloqueada ")
        if response[1] == 200 and response[0]["Respuesta"] == 0:
            instance.save()
        elif response[1] == 200 and response[0]["Respuesta"] == 1:
            msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd006")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.initial_data.get("persona"), type=1, endpoint=get_info(self.context), objJsonResponse=r)
            raise serializers.ValidationError(r)
        elif response[1] == 400 or response[1] == 500:
            msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd007")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.initial_data.get("persona"), type=1, endpoint=get_info(self.context), objJsonResponse=r)
            raise serializers.ValidationError(r)
        """
        pass

class SerializerBajaCostCenter(Serializer):
    motivo = CharField(max_length=1001)

    def validate_motivo(self, value: str):
        if len(value) > 1000:
            raise ValueError('Se supero la longitud maxima')
        return value

    def validate(self, attrs):
        return attrs

    def update(self, **kwargs):
        persona.objects.filter(
            id=self.context.get('cost_center_id')
        ).update(
            motivo=self.validated_data.get('motivo'),
            date_modify=datetime.datetime.now()
        )


class SerializerAmentDocumentsClaveTraspaso(Serializer):
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
                instance.status = "P"
                instance.save()
            remove(file)


class SerializerAmentClaveTraspasoFinal(Serializer):
    clave_traspaso = CharField(allow_null=False)
    banco_clabe = CharField(allow_null=False)

    def validate(self, attrs):
        if self.context['EstadoSolicitudId'] == 1:
            raise ValidationError({'Esta solicitud esta en proceso de verificacion'})
        return attrs

    def update(self, instance, validated_data):
        clave_traspaso = validated_data.get('clave_traspaso')
        banco_clabe = validated_data.get('banco_clabe')
        intentos = 1

        payload = {
            "cost_center_id": self.context['CostCenterInfo'].get('empresa_id'),
            "name": self.context['CostCenterInfo'].get('empresa__name'),
            "clave_traspaso": clave_traspaso,
            "banco_clabe": banco_clabe
        }

        instance.estado_id = 1
        instance.intentos = instance.intentos + intentos
        instance.personaSolicitud_id = self.context['PersonaSolicitudId']
        instance.fechaChange = datetime.datetime.now()
        instance.dato_json = json.dumps(payload)
        instance.save()
        return instance


class SerializerAmentDocumentsDomicilioFiscal(Serializer):
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
            instance: documentos = documentos.objects.get(id=document_id)

            if instance.status == 'D':
                instance.status = 'P'

            with open(file, 'rb') as document:
                instance.documento = File(document)
                instance.save()
            remove(file)


class SerializerAmentDomFiscal(Serializer):
    codigopostal = IntegerField(allow_null=False)
    colonia = CharField(allow_null=False)
    alcaldia_mpio = CharField(allow_null=False)
    estado = CharField(allow_null=False)
    calle = CharField(allow_null=False)
    no_exterior = IntegerField(allow_null=False)
    no_interior = IntegerField(allow_null=True)
    pais = CharField(allow_null=False)

    def validate(self, attrs):
        # if self.context['EstadoSolicitudId'] == 1:
        #     raise ValueError('Esta solicitud esta en proceso de verificacion')
        return attrs

    def update(self, instance, validated_data):
        codigopostal = validated_data.get('codigopostal')
        colonia = validated_data.get('colonia')
        alcaldia_mpio = validated_data.get('alcaldia_mpio')
        estado = validated_data.get('estado')
        calle = validated_data.get('calle')
        no_exterior = validated_data.get('no_exterior')
        no_interior = validated_data.get('no_interior')
        pais = validated_data.get('pais')
        intentos = 1

        payload = {
            "cost_center_id": self.context['CostCenterInfo'].get('empresa_id'),
            "name": self.context['CostCenterInfo'].get('empresa__name'),
            "codigopostal": codigopostal,
            "colonia": colonia,
            "alcaldia_mpio": alcaldia_mpio,
            "estado": estado,
            "calle": calle,
            "no_exterior": no_exterior,
            "no_interior": no_interior,
            "pais": pais,
        }
        instance.estado_id = 1
        instance.intentos = instance.intentos + intentos
        instance.personaSolicitud_id = self.context['PersonaSolicitudId']
        instance.fechaChange = datetime.datetime.now()
        instance.dato_json = json.dumps(payload)
        instance.save()
        return instance


class SerializerCreateDocumentRepresentanteLegal(Serializer):
    tipo = IntegerField()
    owner = IntegerField()
    comment = CharField(default=None)
    base64_file = CharField()

    def validate(self, attrs):
        try:
            obj: TDocumento = TDocumento.objects.get(id=attrs['tipo'])
        except (ObjectDoesNotExist, FieldDoesNotExist, MultipleObjectsReturned) as e:
            raise ValueError('Tipo de documento no valido')
        else:
            if attrs['comment'] is None:
                attrs['comment'] = obj.descripcion

            file_name = create_file(attrs['base64_file'], attrs['owner'])
            attrs['base64_file'] = file_name
        return attrs

    def create(self, **kwargs) -> int:
        file = self.validated_data.pop('base64_file')
        instance = documentos.objects.create_document(**self.validated_data)

        with open(file, 'rb') as document:
            instance.documento = File(document)
            instance.save()
        remove(file)
        return instance.id


class SerializerAltaRepresentanteLegal(Serializer):

    def validate_email(self, value: str) -> str:
        if persona.objects.filter(email=value).exists():
            raise ValueError('Este email ya ha sido registrado')
        return value

    @property
    def _data(self) -> Dict[str, Any]:
        context = self.context.get('info_representante_legal')
        context['documents_id'] = self.context.get('documents_list')
        return context

    def create(self, validated_data):
        instance_solicitud = Solicitudes.objects.create(
            nombre="Alta Representante Legal",
            tipoSolicitud_id=23,
            personaSolicitud_id=self.context['PersonaSolicitudId'],
            estado_id=1,
            intentos=1,
            fechaChange=datetime.datetime.now(),
            dato_json=json.dumps(self._data)
        )
        return instance_solicitud
