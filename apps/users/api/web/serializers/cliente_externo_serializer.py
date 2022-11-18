import datetime as dt
from typing import List
import string

from django.db import IntegrityError
from django.db.models import FilteredRelation, query
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.transaction import atomic

from rest_framework.serializers import *

from MANAGEMENT.Utils.utils import remove_asterisk
from polipaynewConfig.exceptions import *

from apps.solicitudes.api.web.serializers.centro_costos_serializers import SerializerDocumentsOut
# from apps.users.managerUser import *
from apps.users.management import *
from apps.users.models import *
from apps.transaction.models import *

# (ChrGil 2021-12-14) Generador de contraseñas temporal (ELIMINAR CUANDO SE SUBAN CAMBIOS DE TESTER)
# (ChrGil 2021-12-09) Genera una contraseña de 12 caracteres de manera aleatoria
from polipaynewConfig.settings import rfc_Bec


def random_password() -> str:
    return "".join(random.choices(string.hexdigits, k=12))


# (ChrGil 2021-12-14) Generador de numeros aleatorios temporal (ELIMINAR CUANDO SE SUBAN CAMBIOS DE TESTER)
def random_number(length: int = 8):
    return "".join(random.choices(string.digits, k=length))


class SerializerEditarPersonalExternoIn(Serializer):
    # (ChrAvaBus - lun13.12.2021 17:58) Se comenta y remplaza por cliente MUEVETE ZAPOPAN
    # id = ReadOnlyField()
    # name = CharField()
    # last_name = CharField()
    # rfc = CharField(allow_null=True, allow_blank=True)
    # email = CharField()
    # motivo = CharField()
    # --------------------------------------------------------- mejora
    id = ReadOnlyField()
    name = CharField()
    last_name = CharField(allow_null=True, allow_blank=True)  # Colocar allow_null y allow_blank
    rfc = CharField(allow_null=True, allow_blank=True)
    email = CharField()
    motivo = CharField(allow_null=True, allow_blank=True)  # Colocar allow_null y allow_blank
    fecha_nacimiento = DateField(allow_null=True)

    def validate_rfc(self, value: str) -> str:
        _rfc_default: str = rfc_Bec
        if value is None:
            return _rfc_default
        return value

    def validate_fecha_nacimiento(self, value: Union[None, dt.date]) -> dt.date:
        if value is None:
            return dt.date(1900, 1, 1)
        if value == "":
            return dt.date(1900, 1, 1)
        return value

    def validate(self, attrs):
        return attrs

    def update_personal_externo(self, instance):
        try:
            with atomic():
                instance.name = self.validated_data.get("name")
                instance.last_name = self.validated_data.get("last_name")
                instance.email = self.validated_data.get("email")
                instance.rfc = self.validated_data.get("rfc")
                instance.motivo = self.validated_data.get("motivo")
                instance.fecha_nacimiento = self.validated_data.get("fecha_nacimiento")

                document = self.validated_data.get('documento')
                if document:
                    self.create_document(self.validated_data.get('documento'), instance)

                instance.save()
        except (IntegrityError, ObjectDoesNotExist, Exception) as e:
            print(e)
            raise ValidationError({"status": "Ocurrio un error dureante el proceso de actualización del beneficiario"})
        return instance

    def create_document(self, file: str, instance: persona):
        create_pdf_data_v2(file, instance)
        uploadDocument(instance)


class SerializerPersonalExternoIn(Serializer):
    name = CharField()
    last_name = CharField()
    rfc = CharField(allow_null=True)
    email = CharField()
    motivo = CharField(allow_null=True, allow_blank=True)
    fecha_nacimiento = DateField(allow_null=True)

    def validate_email(self, value: str) -> str:
        if persona.objects.filter(email=value).exists():
            raise ValidationError("Email ya registrado")
        return value

    def validate_rfc(self, value: str) -> str:
        _rfc_default: str = rfc_Bec
        if value is None:
            return _rfc_default
        elif len(value) != 13:
            raise ValidationError("Para una persona física, el RFC debe contener 13 caracteres alfanumericos.")
        return value

    def validate_fecha_nacimiento(self, value: Union[None, dt.date]) -> dt.date:
        if value is None:
            return dt.date(1900, 1, 1)
        if value == "":
            return dt.date(1900, 1, 1)
        return value

    def create_personalExterno(self, file, pk_user):
        try:
            with atomic():
                global apellido
                fecha_nacimiento = self.validated_data.get("fecha_nacimiento")
                nombre = self.validated_data.get("name")
                last_name = self.validated_data.get("last_name")
                motivo = self.validated_data.get("motivo")
                first_last_name, last_last_name = last_name.split("*")

                if "*" in last_name:
                    apellido = last_name.replace("*", "")
                if first_last_name != "" or first_last_name != None:
                    password = first_last_name.replace(" ", "")
                else:
                    password = nombre.replace(" ", "")

                password = random_password()
                username_new = GenerarUsername(nombre, apellido)

                # if fecha_nacimiento == "" or fecha_nacimiento == None:
                #     fecha_nacimiento = "1900-01-01"

                instance = persona.objects.create(
                    username=username_new,
                    motivo=motivo,
                    name=nombre,
                    last_name=last_name,
                    rfc=self.validated_data.get("rfc"),
                    fecha_nacimiento=fecha_nacimiento,
                    email=self.validated_data.get("email"),
                    is_active=True,
                    tipo_persona_id=2,
                    password=make_password(password),
                    state=True
                )

                if file:
                    create_pdf_data_personal_externo(file, instance)
                    uploadDocumentPersonalExterno(instance)

                PersonaExternaGrupoPersona(pk_user, instance)
                Cuenta = OrderCuenta(instance)
                # (ChrGil 2022-01-28) Se parchea error 500
                # BeneficiarioDispersaAddGroup(instance)
        except ValueError as e:
            raise ValidationError({"status": "Ocurrio un error durante el proceso de creación de un persona externo"})
        else:
            createMessageWelcomeExternalPerson(nombre, instance.email, password, Cuenta)
            return Cuenta, instance


class EliminarPersonaExternaIn(Serializer):
    id = ReadOnlyField()
    motivo = CharField(allow_null=False, allow_blank=False)

    def Eliminar_persona_externa(self, instance, queryset):
        documento = documentos.objects.filter(person_id=instance.id)
        for i in documento:
            i.historial = True
            i.save()
        cuentas = cuenta.objects.filter(persona_cuenta_id=instance.id)
        for i in cuentas:
            i.is_active = False
            i.save()
        for query in queryset:
            query.delete()
        instance.motivo = str(instance.motivo) + " Motivo: " + str(self.validated_data.get("motivo"))
        instance.is_active = False
        instance.state = False
        instance.save()
        return


class FilterPersonExtSerializer(Serializer):
    empresa_id = IntegerField()
    numero_tarjetas = CharField(allow_blank=True)
    name = CharField(allow_null=True, allow_blank=True)
    is_active = BooleanField(allow_null=True)
    numero_cuenta = CharField(allow_blank=True, allow_null=True)
    date_1 = DateField()
    date_2 = DateField()

    def list_person_with_number_cards(self, inquiries: List, numero_tarjetas: str, numero_cuenta: str) -> List:
        list_data = []
        _number_targets: int = 0

        for query in inquiries:
            _number_targets = tarjeta.objects.filter(cuenta__persona_cuenta_id=query['person_id']).count()

            # (ChrGil 2022-01-07) Se elimina asterisco
            if query["person__last_name"]:
                last_name: str = query.get('person__last_name')
                result = remove_asterisk(last_name)
                query["person__last_name"] = None if result == '' else result

            # (2021-12-13) Se agrega parche, para el listado de personal externo
            if numero_tarjetas == "null":
                numero_cuentas = cuenta.objects.filter(
                    persona_cuenta_id=query['person_id'],
                    cuenta__icontains=numero_cuenta
                )

                if numero_cuentas:
                    query['number_targets'] = _number_targets
                    list_data.append(query)

            if numero_tarjetas == str(_number_targets):
                numero_cuentas = cuenta.objects.filter(
                    persona_cuenta_id=query['person_id'],
                    cuenta__icontains=numero_cuenta
                )

                if numero_cuentas:
                    query['number_targets'] = _number_targets
                    list_data.append(query)
        return list_data

    def filter_querys(self):
        company_id: int = self.validated_data['empresa_id']
        is_active: bool = self.validated_data['is_active']
        numero_cuenta: str = self.validated_data['numero_cuenta']
        numero_tarjetas: str = self.validated_data['numero_tarjetas']
        date_1 = self.validated_data['date_1']
        date_2 = self.validated_data['date_2']
        name: str = self.validated_data['name']

        inquiries = grupoPersona.objects.all().values(
            'person_id',
            'person__name',
            'person__last_name',
            'person__date_joined',
        ).filter(empresa_id=company_id, relacion_grupo_id=6).annotate(
            persona_fisica=FilteredRelation(
                'person', condition=Q(person__state=is_active) &
                                    Q(person__date_joined__date__gte=date_1) & Q(person__date_joined__date__lte=date_2)
            )).filter(persona_fisica__name__icontains=name).order_by('-person__date_joined')

        queryset = self.list_person_with_number_cards(inquiries, numero_tarjetas, numero_cuenta)
        return queryset


class SerializerDetailPersonaExternaOut(Serializer):
    empresa_id = SerializerMethodField()
    person_id = SerializerMethodField()
    tarjetas = SerializerMethodField()
    cuenta = SerializerMethodField()
    Documents = SerializerMethodField()

    def get_empresa_id(self, obj: empresa_id):
        person_instance = get_Object_orList_error(persona, id=obj.empresa_id)
        account_instance = get_Object_orList_error(cuenta, persona_cuenta=person_instance.id)
        return {
            'id': person_instance.id,
            'name': person_instance.name,
            'saldoDisponible': account_instance.monto,
            'Cuenta': account_instance.cuenta,
            'Clabe': person_instance.clabeinterbancaria_uno
        }

    def get_person_id(self, obj: person_id):
        person_instance = get_Object_orList_error(persona, id=obj.person_id)
        return {
            'id': person_instance.id,
            'Nombre': person_instance.name,
            'apellido': person_instance.last_name,
            'rfc': person_instance.rfc,
            'fechaNacimiento': person_instance.fecha_nacimiento,
            'email': person_instance.email,
            'descripcionActividades': person_instance.motivo
        }

    def get_Documents(self, obj: Documents):
        instance = documentos.objects.filter(person_id=obj.person_id, historial=False, tdocumento_id=12)
        return SerializerDocumentsOut(instance, many=True).data

    def get_cuenta(self, obj: cuenta):
        person_instance = get_Object_orList_error(persona, id=obj.person_id)
        account_instance = get_Object_orList_error(cuenta, persona_cuenta=person_instance.id)
        return {
            'DatosCuenta': account_instance.cuenta,
            'SaldoCuenta': account_instance.monto
        }

    def get_tarjetas(self, obj: tarjetas):
        person_instance = get_Object_orList_error(persona, id=obj.person_id)
        account_instance = get_Object_orList_error(cuenta, persona_cuenta=person_instance.id)
        tarjeta_instance = tarjeta.objects.filter(cuenta_id=account_instance.id)

        lista = []
        for c in tarjeta_instance:
            data = {
                'tarjeta': c.tarjeta,
                'status': c.is_active,
                "status_inntec": get_actual_state({"TarjetaID": c.TarjetaId})[0].get("Detalle"),
                "was_eliminated": c.was_eliminated,
                "deletion_date": c.deletion_date
            }
            lista.append(data)
        return (lista)


class DetallesMovimientosCuenta(Serializer):
    id = ReadOnlyField()
    nombre_beneficiario = CharField()
    cta_beneficiario = CharField()
    receiving_bank_id = CharField()
    transmitter_bank_id = CharField()
    nombre_emisor = CharField()
    monto = FloatField()
    concepto_pago = CharField()
    referencia_numerica = CharField()
    fecha_creacion = DateTimeField()


# (JM 2021/12/06   end point para dar de alta beneficiarios de manera masiva)
class AltaBeneficiarioMasivo(Serializer):

    def validate(self, listado_excel):
        error = []
        for datos in listado_excel:
            if "@" not in datos.get('Correo_Electronico'):
                error.append({"field": "Correo_Electronico", "data": datos.get("Correo_Electronico"),
                              "message": "Correo electronico no valido"})

            if persona.objects.filter(email=datos.get("Correo_Electronico")):
                error.append({"field": "Correo_Electronico", "data": datos.get("Correo_Electronico"),
                              "message": "Correo electronico ya registrado"})
            if error:
                continue
            else:
                if datos.get("RFC") == None or datos.get("RFC") == "":
                    rfc = rfc_Bec
                    datos['RFC'] = rfc
                username = GenerarUsername(nombre=datos.get("Nombres"), apellido="")
                Fecha_de_Nacimiento = datos.get("Fecha_de_Nacimiento")
                if Fecha_de_Nacimiento == "" or Fecha_de_Nacimiento == None:
                    Fecha_de_Nacimiento = "1900-01-01"
                    datos['Fecha_de_Nacimiento'] = Fecha_de_Nacimiento
                nueva_llave = {"username": username.replace("*", "")}
                datos.update(nueva_llave)
        MensajeError(error)
        return listado_excel

    def create(self, listado_excel, pk_user):
        queryset = persona.objects.bulk_create([
            persona(
                name=datos.get("Nombres"),
                username=datos.get("username"),
                last_name=datos.get(str("Apellido_Paterno")) + "*" + datos.get(str("Apellido_Materno")),
                email=datos.get("Correo_Electronico"),
                password=make_password(str(datos.get("Nombres").replace(" ", "").replace("*", "") + "9/P")),
                rfc=datos.get("RFC"),
                fecha_nacimiento=datos.get("Fecha_de_Nacimiento"),
                is_active=True,
                is_new=True,
                is_client=True,
                tipo_persona_id=2,
                state=True
            ) for datos in listado_excel
        ]
        )
        # Conseguir id de los usuarios
        beneficiarios_solo_id = []
        cuentas = cuenta.objects.filter(cuenta__startswith='9').values('cuenta').last()
        cuenta_actual = int(cuentas['cuenta'])
        nueva_cuenta = cuenta_actual
        for i in queryset:
            user_id = persona.objects.get(username=i).get_only_id()
            nueva_cuenta = nueva_cuenta + 1
            dic = {
                "id": user_id,
                "NumeroCuenta": nueva_cuenta,
            }
            beneficiarios_solo_id.append(dic)
        # Cuenta
        cuenta.objects.bulk_create([
            cuenta(
                cuenta=str(datos.get("NumeroCuenta")), persona_cuenta_id=datos.get("id"),
                cuentaclave="XXXXXXX" + str(datos.get("NumeroCuenta")) + "X",
                is_active=True
            ) for datos in beneficiarios_solo_id
        ]
        )
        grupoPersona.objects.bulk_create([
            grupoPersona(
                empresa_id=pk_user, person_id=datos['id'], relacion_grupo_id=6,
            ) for datos in beneficiarios_solo_id
        ]
        )
        return beneficiarios_solo_id
