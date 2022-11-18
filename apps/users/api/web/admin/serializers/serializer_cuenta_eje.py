import sys
from typing import ClassVar
from datetime import datetime

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import BaseUserManager
from django.core.files import File
from django.db import IntegrityError

from rest_framework.serializers import *

from MANAGEMENT.Utils.utils import random_password
from apps.commissions.models import Cat_commission, Commission
from apps.productos.models import rel_prod_serv, servicios
from apps.users.exc import YouNotSuperUser
from apps.users.messages import messageAddAdminToCompany
from polipaynewConfig.exceptions import add_list_errors
from apps.permision.manager import *
from apps.transaction.models import bancos
from apps.users.serializers import *
from apps.users.models import *
from apps.users.management import (
    to_dict,
    get_account,
    filter_data_or_return_none,
    GenerarUsername,
    create_pdf_data,
    uploadDocument,
    addAdministrative, create_pdf_data_v2, create_pdf_data_v3, SubirDocumento)

# - - - - - - - - Funciones de uso exclusivo para Cuenta Eje / administrativos - - - - - - -

def replace_key_account(clabe:str):
    """ Se reemplaza el codigo de polipay con el texto indicado en la clabe interbancaria"""
    text_to_replace = "PPCE"
    clabe = clabe[0:6]+text_to_replace+clabe[10:18]
    return clabe


def replace_account(account:str):
    """ Se reemplaza el codigo de polipay con el texto indicado en la cuenta"""
    text_to_replace = "PCE"
    account = text_to_replace+account[3:11]
    return account



# - - - - - - S e r i a l i z a d o r e s   D e   A d m i n i s t r a t i v o s - - - - - -

class SerializerAdministrators(Serializer):
    email = EmailField()
    name = CharField()
    a_paterno = CharField()
    a_materno = CharField(allow_null=True, default=None)
    password = CharField(read_only=True)
    phone = CharField()
    is_superuser = BooleanField(default=False)
    is_staff = BooleanField(default=False)
    fecha_nacimiento = DateField()

    def validate_email(self, value: str) -> str:
        return value.lower()

    def validate_name(self, value: str) -> str:
        return value.title()

    def validate_a_paterno(self, value: str) -> str:
        return value.title()

    def validate_a_materno(self, value: str) -> str:
        return value.title()

    def validate(self, attrs):
        list_errors = []
        email_if_exists = filter_object_if_exist(persona, email=attrs['email'])

        if email_if_exists:
            add_list_errors({'email': f'Dirección de correo electronico {attrs["email"]} no valido o ya asignado.'},
                            list_errors)

        if len(list_errors) > 0:
            self.context.get('log').json_response(list_errors)
            raise ValidationError({'status': list_errors})

        attrs['password'] = random_password()
        return attrs

    def create(self, validated_data, **kwargs):
        instance = persona.objects.create_admin(**validated_data)
        return instance.get_only_id()


class SerializerAddAdministrators(SerializerGeneralGrupoPersonaIn):
    is_admin = BooleanField(read_only=True)
    addworker = BooleanField(read_only=True)

    def validate(self, attrs):
        admin_id = self.context['instance']
        persona_moral_id = self.context['persona_moral_id']

        attrs['person_id'] = admin_id
        attrs['empresa_id'] = persona_moral_id
        attrs['is_admin'] = True
        attrs['nombre_grupo'] = 'Administrativos'
        attrs['relacion_grupo_id'] = 3
        attrs['addworker'] = True
        attrs['delworker'] = True

        return attrs

    def create(self, **kwargs):
        return grupoPersona.objects.create(**self.validated_data)


# - - - - - - S e r i a l i z a d o r   D e   R a z o n   S o c i a l - - - - - -

class SerializerRazonSocialWebIn(Serializer):
    # (AAF 2022-06-06) se quitan debido a que no se usaran la clave interbancaria_dos ni clave_banco
    # (AAF 2022-06-07) se agrega el campo name_stp y la validacion correspodiente
    """
    Serializador de entrada de razon social

    """

    name = CharField()
    rfc = CharField()
    fecha_nacimiento = DateField()
    clabeinterbancaria_uno = CharField()
    # clabeinterbancaria_dos = CharField()
    giro = CharField()
    # banco_clabe = CharField()
    domicilio = SerializerDomicilioIn()
    name_stp = CharField()

    def validate_name(self, value: str) -> str:
        return value.title()

    def validate_rfc(self, value: str) -> str:
        return value.upper()

    #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
    def validate_name_stp(self, value: str):
        """
        value                   = value.replace(" ", "_")
        value                   = value.upper()
        array_caracteres_esp    = [" ", "_", "-", "\"", "\'", "\\", "/", "+", "-", ".", ":", ",", "¡", "!", "?", "¿", "%", "&", "$", "#", "@"]
        array_numeros           = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        if len(value) == 1 and ( str(value) in array_caracteres_esp or str(value) in array_numeros ):
            raise ValidationError({"status": "Nombre de STP (name_stp) no puede ser un caracter especial"})

        if len(value) < 1 or len(value) > 15:
            raise ValidationError({"status":"Nombre de STP (name_stp) debe tener de 1 hasta 15 caracteres"})
        """
        return value.upper()


    def validate(self, attrs):
        clb_interbancaria_uno = filter_object_if_exist(persona, clabeinterbancaria_uno=attrs['clabeinterbancaria_uno'])
        list_errors = []

        if filter_object_if_exist(persona, name=attrs['name']):
            add_list_errors({"name": 'El nombre de la razon social ya existe.'}, list_errors)

        if clb_interbancaria_uno:
            add_list_errors({'clb_interbancaria_uno': 'Clabe interbancaria no valida.'}, list_errors)

        if filter_object_if_exist(persona, name=attrs['name_stp']):
            add_list_errors({"name": 'El nombre registrado en STP de la razon social ya existe.'}, list_errors)
        # (AAF 2022-06-06) se quitan debido a que no se usaran las claves
        # if attrs['clabeinterbancaria_uno'] == attrs['clabeinterbancaria_dos']:
        #     add_list_errors({'clabes': 'Las clabes interbancarias no deben ser iguales.'}, list_errors)
        #
        # if attrs['clabeinterbancaria_dos'][0:3] == '646':
        #     add_list_errors({'clb_interbancaria_dos': 'Asegúrese que esta cuenta no le pertenezca a STP'}, list_errors)

        if len(list_errors) > 0:
            raise ValidationError({'status': list_errors})

        return attrs

    def create(self, **kwargs):
        return self.validated_data


class SerializerGeneral(Serializer):
    razon_social = SerializerRazonSocialWebIn()
    representante_legal = SerializerRepresentanteLegalWebIn()

    def create(self, validated_data):
        """
        De los datos validados se crea un diccionario para que
        se pueda crear la razon social y su representante retornando
        sus instancias creadas


        """

        razon_social_data = to_dict(validated_data['razon_social'])
        domicilio_razon_social = to_dict(razon_social_data['domicilio'])
        razon_social_data.pop('domicilio')

        #instance_razon_social = persona.objects.create_razon_social(**razon_social_data)
        #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
        instance_razon_social = persona.objects.create_razon_social(**razon_social_data, type=validated_data["type_ce_ccc"])
        domicilio.objects.add_address_rs(**domicilio_razon_social, person_id=instance_razon_social.id)

        #       Para la Cuenta Eje (PPCE)
        instance_representante_legal    = None
        is_admin                        = None
        if int(validated_data["type_ce_ccc"]) == 0:
            representante_legal_data: Dict = to_dict(validated_data['representante_legal'])
            domicilio_representante_legal = to_dict(representante_legal_data['domicilio'])
            representante_legal_data.pop('domicilio')
            is_admin = representante_legal_data.pop('is_admin')

            instance_representante_legal = persona.objects.create_admin(**representante_legal_data)
            domicilio.objects.add_address_rs(**domicilio_representante_legal, person_id=instance_representante_legal.id)
        return instance_razon_social, instance_representante_legal, is_admin


class SerializerGrupoPersonaIn(SerializerGeneralGrupoPersonaIn):
    """
    Serializador de entrada para grupo de persona

    """

    is_admin = BooleanField(read_only=True)
    addworker = BooleanField(read_only=True)


    def validate(self, attrs):
        attrs['person_id'] = self.context['instance_rl']
        attrs['empresa_id'] = self.context['instance']['id']
        attrs['nombre_grupo'] = self.context['instance']['name']
        #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
        #       Para la Cuenta Eje (PPCE)
        if int(self.context['type_ce_ccc']) == 0:
            attrs['relacion_grupo_id']  = 1
        #   Para el centro de costos concentrador (ccc)
        elif int(self.context['type_ce_ccc']) == 1:
            attrs['relacion_grupo_id']  = 4

        if self.context.get('is_admin'):
            attrs['is_admin'] = True
            attrs['addworker'] = True
            attrs['delworker'] = True

        if not self.context.get('is_admin'):
            attrs['is_admin'] = False
            attrs['addworker'] = False
            attrs['delworker'] = False

        return attrs

    def create(self, **kwargs):
        # (AAF 2022-06-07) se añade replace a la clabeinterbancaria_uno para sustituir 1718 de la cuentaclave por PPCE
        # (AAF 2022-06-07) se añade replace a la cuenta para sustituir 718 en la cuenta por PCE
        """
        Se crea la cuenta de la cuenta eje

        """

        account = get_account(self.context['instance']['clabeinterbancaria_uno'])
        #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
        #       Para la Cuenta Eje (PPCE)
        if int(self.context['type_ce_ccc']) == 0:
            cuenta.objects.create(
                cuenta=replace_account(account),
                is_active=False,
                persona_cuenta_id=self.context['instance']['id'],
                cuentaclave=replace_key_account(self.context['instance']['clabeinterbancaria_uno'])
            )
        #       Para el centro de costos concentrador (ccc)
        else:
            cuenta.objects.create(
                cuenta              = account,
                is_active           = True,
                persona_cuenta_id   = self.context['instance']['id'],
                cuentaclave         = self.context['instance']['clabeinterbancaria_uno']
            )
        return grupoPersona.objects.create(**self.validated_data)

    #   Para el centro de costos concentrador (ccc)
    def create_relacion5(self, **kwargs):
        datos_validados = self.validated_data
        datos_validados.update(
            {
                "is_admin": False,
                "relacion_grupo_id": 5,
                "person_id": datos_validados.get("empresa_id"),
                "empresa_id": int(self.context["idCE"]["id"]),
                "nombre_grupo": datos_validados.get("nombre_grupo") + " CE - CCC"
            }
        )
        return grupoPersona.objects.create(**datos_validados)



class SerializerRepresentanteLegalUpdateIn(Serializer):
    name = CharField(read_only=True)
    last_name = CharField(read_only=True)
    rfc = CharField(read_only=True)
    email = CharField()
    phone = CharField()

    def validate(self, attrs):
        instance = get_Object_orList_error(persona, id=self.context['id'])

        if attrs['email'] != instance.email:
            queryset = filter_object_if_exist(persona, email=attrs['email'])
            if queryset:
                error = {'status': ['Esta dirección de correo electronico ya existe.']}
                self.context.get('log').json_response(error)
                raise ValidationError(error)
            return attrs
        return attrs

    def update(self, instance, **kwargs):
        instance.email = self.validated_data.get('email', instance.email)
        instance.phone = self.validated_data.get('phone', instance.phone)
        instance.save()
        return instance


class SerializerServicesIn(Serializer):
    f_producto_id = IntegerField()
    comision = BooleanField()
    porc_comision = FloatField()
    f_persona_id = IntegerField()
    fecha_autorizacion = DateTimeField(read_only=True)
    usuario_autorizacion_id = IntegerField(read_only=True)

    def validate(self, attrs):
        attrs['usuario_autorizacion_id'] = self.context['id_superuser'].id
        attrs['fecha_autorizacion'] = datetime.datetime.now()

        is_superuser = filter_data_or_return_none(persona, id=attrs['usuario_autorizacion_id'], is_superuser=True)
        razon_social = filter_object_if_exist(persona, id=attrs['f_persona_id'], tipo_persona_id=1)
        products = filter_object_if_exist(Productos, id=attrs['f_producto_id'])

        if not is_superuser:
            error = {'status': ['Esta operación solo es permitida por el super usuario']}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if not razon_social:
            error = {'status': ['Unicamente se puede asignar servicios y comiciones a una razon social']}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if not products:
            error = {'status': ['Producto no encontrado']}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        return attrs

    def create(self, **kwargs):
        instance_service = Comisiones.objects.create(**self.validated_data)
        persona_id = instance_service.f_persona_id

        # instance_cuenta_eje = get_Object_orList_error(persona, id=instance_service.f_persona_id)
        # instance_cuenta_eje.is_active = True
        # instance_cuenta_eje.save()
        persona.objects.filter(id=persona_id).update(is_active=True)
        cuenta.objects.filter(persona_cuenta_id=persona_id).update(is_active=True)
        return instance_service


class SerializerGetDocumentOut(Serializer):
    documento = FileField()


class SerializerEditDomicilioIn(Serializer):
    documento = CharField()

    def EditDomicilio(self, instance):
        file = self.validated_data.get("documento")

        if file != None:
            create_pdf_data(file)
            with open('TEMPLATES/Files/file.pdf', 'rb') as document:
                instance.documento = File(document)
                instance.save()

        else:
            error = 'Este campo no puede estar vacio'
            self.context.get('log').json_response(error)
            raise ValidationError(error)


# - - - - - - - - - - S e r i a l i z a d o r e s   D e   L i s t a d o - - - - - - - - - -


class serializerAdministrativeStaffOut(Serializer):
    id = ReadOnlyField()
    name = CharField()
    last_name = CharField()
    email = CharField()
    phone = CharField()


class serializerAdministrativeStaffNameEmailOut(Serializer):
    def to_representation(self, instance):
        return {
            'id': instance.person_id,
            'name': instance.person.get_full_name(),
            'email': instance.person.email,
            'state': instance.person.state,
            'is_admin': instance.is_admin
        }


class SerializerRazonSocialOut(ModelSerializer):
    class Meta:
        model = persona
        fields = ['id', 'name', 'rfc']


class SerializerRetrieveCuentaEje(Serializer):
    representante_legal = SerializerMethodField()
    empresa_id = SerializerMethodField()

    def get_representante_legal(self, obj: representante_legal):
        return obj.person_details

    def get_empresa_id(self, obj: empresa_id):
        person_instance = get_Object_orList_error(persona, id=obj.empresa_id)
        account_instance = get_Object_orList_error(cuenta, persona_cuenta=person_instance.id)
        # (2022-06-10 AAF) se quita la busqueda del banco
        # bank_instance = get_Object_orList_error(bancos, clabe=person_instance.banco_clabe)

        return {
            'id': person_instance.id,
            'name': person_instance.name,
            # (2022-06-10 AAF) se añade el campo de name_stp para mostrar como alias en la vista, y se quita banco
            'name_stp': person_instance.name_stp,
            'rfc': person_instance.rfc,
            'clabeinterbancaria_uno': person_instance.clabeinterbancaria_uno,
            'giro': person_instance.giro,
            'date_joined': person_instance.date_joined,
            # 'banco': bank_instance.institucion,
            'cuenta': account_instance.cuenta
        }


class SerializerGetAdminActual(Serializer):
    persona_id = SerializerMethodField()

    def get_persona_id(self, obj: persona_id):
        gp_persona_instance = get_Object_orList_error(grupoPersona, person_id=self.context['admin_id'].id)
        return {
            'id': self.context['admin_id'].id,
            'name': self.context['admin_id'].get_full_name(),
            'email': self.context['admin_id'].email,
            'cuenta_eje_id': gp_persona_instance.empresa_id
        }


class SerializerListCuentaEje(Serializer):
    querysets = SerializerMethodField()

    def get_querysets(self, obj: querysets):
        list_cuenta_eje_with_services = []
        for instance in obj:
            instance_comision = Comisiones.objects.filter(f_persona_id=instance.empresa_id).select_related('f_producto')
            get_cuenta = cuenta.objects.get(persona_cuenta_id=instance.empresa_id).get_cuenta()
            listado_comisiones = [j.get_producto() for j in instance_comision]

            data = {
                "data": instance.get_empresa(),
                "cuenta": get_cuenta,
                "services": listado_comisiones
            }

            list_cuenta_eje_with_services.append(data)

        return list_cuenta_eje_with_services


# (ChrGil 2022-03-07) Asiganr permisos dependiendo del producto
class GetProductCuentaEje:
    product_cuenta_eje: ClassVar[Dict[str, Any]]
    _dispersa: ClassVar[PermissionDispersa] = PermissionDispersa
    _liberate: ClassVar[PermissionLiberate] = PermissionLiberate
    _empresa: ClassVar[PermissionEmpresa] = PermissionEmpresa

    def __init__(self, cuenta_eje_id: int):
        self._cuenta_eje_id = cuenta_eje_id
        self.product_cuenta_eje = self._get_product_cuenta_eje

    @property
    def _get_product_cuenta_eje(self) -> Dict[str, Any]:
        return cuenta.objects.filter(persona_cuenta_id=self._cuenta_eje_id).values('id', 'rel_cuenta_prod').first()

    def set_permission_admin(self, admin: int):
        print(self.product_cuenta_eje.get('rel_cuenta_prod'))
        if self.product_cuenta_eje.get('rel_cuenta_prod') == 3:
            self._empresa(admin)

        if self.product_cuenta_eje.get('rel_cuenta_prod') == 1:
            self._dispersa(admin)

        if self.product_cuenta_eje.get('rel_cuenta_prod') == 2:
            self._liberate(admin)


class SerializerAddAdministrativesCompany(Serializer):
    name = CharField(allow_null=False, allow_blank=False)
    last_name = CharField(read_only=True)
    password = CharField(read_only=True)
    apellido_paterno = CharField(write_only=True)
    apellido_materno = CharField(write_only=True)
    phone = IntegerField(allow_null=False)
    email = EmailField(allow_null=False, allow_blank=False)
    fecha_nacimiento = DateField(allow_null=False)
    documento = CharField(allow_null=False)

    def validate(self, attrs):
        apellido_paterno = (attrs['apellido_paterno'])
        apellido_materno = (attrs['apellido_materno'])

        admins_in_company = grupoPersona.objects.filter(
            Q(empresa_id=self.context['empresa_id'],
              relacion_grupo_id=3) |
            Q(empresa_id=self.context['empresa_id'],
              relacion_grupo_id=1)).count()

        if admins_in_company > 5:
            error = {'code': 400, 'status': 'error', 'message': 'Solo se permiten tener 5 administradores'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        attrs['last_name'] = f'{apellido_paterno} {apellido_materno}'
        attrs['password'] = random_password()
        return attrs

    def validate_email(self, data):
        emails = persona.objects.filter(email=data)
        if len(emails) != 0:
            error = {'code': 400, 'status': 'error', 'message': 'Este email ya ha sido registrado'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)
        else:
            return data

    def create(self, get_empresa):
        self.validated_data.pop('apellido_paterno')
        self.validated_data.pop('apellido_materno')
        name = self.validated_data.get('name')
        last_name = self.validated_data.get('last_name')
        password = self.validated_data.get('password')
        phone = self.validated_data.get('phone')
        email = self.validated_data.get('email')
        fecha_nacimiento = self.validated_data.get('fecha_nacimiento')
        documento = self.validated_data.get('documento')

        instance_persona = persona.objects.create_admin_cuenta_eje(
            name=name,
            last_name=last_name,
            phone=phone,
            email=email,
            fecha_nacimiento=fecha_nacimiento,
            password=password
        )
        create_pdf_data_v3(documento, instance_persona)
        uploadDocument(instance_persona)
        addAdministrative(get_empresa, instance_persona)
        permission = GetProductCuentaEje(self.context.get('empresa_id'))
        permission.set_permission_admin(instance_persona.id)
        messageAddAdminToCompany(instance_persona, password, name, last_name)
        return instance_persona


class SerializerUpdateAdmin(Serializer):
    name = CharField(allow_null=False, allow_blank=False)
    last_name = CharField(read_only=True)
    apellido_paterno = CharField(write_only=True)
    apellido_materno = CharField(write_only=True)
    phone = IntegerField(allow_null=False)
    email = EmailField(allow_null=False, allow_blank=False)

    def validate(self, attrs):
        apellido_paterno = (attrs['apellido_paterno'])
        apellido_materno = (attrs['apellido_materno'])

        attrs['last_name'] = f'{apellido_paterno} {apellido_materno}'
        return attrs

    def update(self, instance):
        instance.name = self.validated_data.get('name')
        instance.last_name = self.validated_data.get('last_name')
        instance.phone = self.validated_data.get('phone')
        instance.email = self.validated_data.get('email')
        instance.save()
        return instance


class SerializerDeleteAdmin(Serializer):
    id = IntegerField(read_only=True)
    motivo = CharField(allow_null=False, allow_blank=False)

    def delete_admin(self, admin, admin_company):
        documento = documentos.objects.filter(person_id=admin.id)
        for doc in documento:
            doc.historial = True
            doc.save()

        for query in admin_company:
            query.delete()

        admin.motivo = str(admin.motivo) + " Motivo: " + str(self.validated_data.get("motivo"))
        admin.is_active = False
        admin.state = False
        admin.save()
        return


class SerializerProductsServices(Serializer):
    _service: ClassVar[Dict[str, Any]]

    porcentaje = FloatField()
    monto = FloatField(default=0.0)
    descripcion = CharField(read_only=True)
    tipo_comission = BooleanField()
    aplicacion = IntegerField(read_only=True)
    servicio = IntegerField()

    def validate_porcentaje(self, value: int) -> float:
        if value >= 100:
            raise TypeError('El porcentaje no debe de ser mayor a 100')
        return value / 100

    def validate_tipo_comission(self, value: bool) -> int:
        # Positiva
        if value:
            return 1

        # Negativa
        if not value:
            return 2

    def validate_servicio(self, value: int):
        self._service = rel_prod_serv.objects.filter(service_id=value).values('id', 'service_id').first()
        if not self._service:
            raise ValueError('Servicio no valido')
        return self._service.get('id')

    def validate(self, attrs):
        service = servicios.objects.filter(id=self._service.get('service_id')).values('nombre', 'descripcion').first()
        attrs["descripcion"] = f"{service.get('nombre')}: {service.get('descripcion')}"

        if not self.context.get('is_superuser'):
            raise YouNotSuperUser("No tienes los permisos suficientes para hacer esta operación")

        # Cobro comisión, mensual
        if attrs['tipo_comission'] == 1:
            attrs['aplicacion'] = 2

        # Cobro comisión, inmediato
        if attrs['tipo_comission'] == 2:
            attrs['aplicacion'] = 1

        return attrs

    def create(self, **kwargs) -> int:
        return Cat_commission.objects.create_cat_comission(**self.validated_data)
