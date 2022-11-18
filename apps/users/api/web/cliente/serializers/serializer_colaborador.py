import itertools
from os import remove

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files import File
from django.db.models import Q
from requests.api import request

from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Utils.utils import create_file
from apps import solicitudes

from rest_framework.serializers import *

from apps.permision.manager import *
from apps.users.management import *
from apps.users.models import *
from apps.solicitudes.models import *


class documentURL(Serializer):
    document = DateField()


class SerializerCostCenterColaborator(Serializer):
    cost_center_list = ListField()

    def validate_cost_center_list(self, value: List[int]):
        cost_center_count = grupoPersona.objects.filter(person_id__in=value, relacion_grupo_id=5).count()
        if cost_center_count == 0:
            raise ValueError('Centro de costos no asociado a tu cuenta eje')
        return value

    def validate(self, attrs):
        return attrs

    def create(self, **kwargs):
        objs = [
            grupoPersona.objects.create_grupo_persona(empresa_id=i, **self.context)
            for i in self.validated_data.get('cost_center_list')
        ]

        grupoPersona.objects.bulk_create(objs)


# (ChrGil 2021-12-07) Serializador para la creación de un documento tipo PDF
class SerializerDocuments(Serializer):
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


class SerializerAltaColaborador(Serializer):
    name = CharField()
    email = CharField()
    fecha_nacimiento = DateField()
    phone = CharField()

    def validate_email(self, value: str) -> str:
        if '@' not in value:
            raise ValueError('Dirección de correo electronico no valido')

        if persona.objects.filter(email=value).exists():
            raise ValueError('Dirección de correo electronico no valido o ya existe')
        return value.lower()

    def validate_phone(self, value: str) -> str:
        if not value.isnumeric():
            raise ValueError('Ingrese un numero telefonico valido')

        if len(value) > 15:
            raise ValueError('Ingrese un numero telefonico valido')
        return value.lower()

    def validate(self, attrs):
        return attrs

    def create(self, **kwargs) -> persona:
        return persona.objects.create_colaborador(**self.validated_data)

        # for Centros in self.validated_data.get("CenCost"):
        #     centroColabo = grupoPersona.objects.create(empresa_id=Centros, person_id=colaborador.id,
        #                                                relacion_grupo_id=8)
        # grupoPersona.objects.create(empresa_id=pk_user, person_id=colaborador.id, relacion_grupo_id=14)
        # Solicitudes.objects.create(tipoSolicitud_id=1, personaSolicitud_id=colaborador.id, estado_id=1, intentos=0)
        # UserAddGroup(grupoPermiso, colaborador)
        # return colaborador


# (ChrGil 2022-03-08) Corregir información de un colaborador
class SerializerAmendColaborador(Serializer):
    name = CharField()
    email = CharField()
    fecha_nacimiento = DateField()
    phone = CharField()

    def validate_email(self, value: str) -> str:
        person_info = persona.objects.filter(id=self.context.get('person_id')).values('email').first()

        if person_info:
            if person_info.get('email') == value:
                return value.lower()

        if '@' not in value:
            raise ValueError('Dirección de correo electronico no valido')

        if persona.objects.filter(email=value).exists():
            raise ValueError('Dirección de correo electronico no valido o ya existe')
        return value.lower()

    def validate_phone(self, value: str) -> str:
        person_info = persona.objects.filter(id=self.context.get('person_id')).values('phone').first()

        if person_info:
            if person_info.get('phone') == value:
                return value

        if not value.isnumeric():
            raise ValueError('Ingrese un numero telefonico valido')

        if len(value) > 15:
            raise ValueError('Ingrese un numero telefonico valido')

        return value

    def validate(self, attrs):
        return attrs

    def amend(self, **kwargs) -> NoReturn:
        persona.objects.filter(id=self.context.get('person_id')).update(**self.validated_data)


# (ChrGil 2022-03-08) corregir documentos
class SerializerAmendDocuments(Serializer):
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


# (ChrGil 2022-03-08) Editar información de un colaborador
class SerializerEditColaborador(Serializer):
    phone = CharField()

    def validate_phone(self, value: str) -> str:
        person_info = persona.objects.filter(id=self.context.get('person_id')).values('phone').first()

        if person_info:
            if person_info.get('phone') == value:
                return value

        if not value.isnumeric():
            raise ValueError('Ingrese un numero telefonico valido')

        if len(value) > 15:
            raise ValueError('Ingrese un numero telefonico valido')
        return value

    def validate(self, attrs):
        return attrs

    # def update(self, **kwargs) -> persona:
    #     print(self.validated_data)
    #     return persona.objects.filter(
    #         id=self.context.get('person_id')
    #     ).update(**self.validated_data)


# (ChrGil 2022-03-08) Editar información de un colaborador
class SerializerAmendEditColaborador(Serializer):
    phone = CharField()

    def validate_phone(self, value: str) -> str:
        person_info = persona.objects.filter(id=self.context.get('person_id')).values('phone').first()

        if person_info:
            if person_info.get('phone') == value:
                return value

        if not value.isnumeric():
            raise ValueError('Ingrese un numero telefonico valido')

        if len(value) > 15:
            raise ValueError('Ingrese un numero telefonico valido')
        return value

    def validate(self, attrs):
        return attrs

    def amend(self, **kwargs) -> persona:
        return persona.objects.filter(
            id=self.context.get('person_id')
        ).update(**self.validated_data)






class AltaColaborador(Serializer):
    name = CharField()
    email = CharField()
    fecha_nacimiento = DateField()
    phone = CharField()
    CenCost = ListField()

    def validate(self, data):
        errores = []
        for Centros in data["CenCost"]:
            if grupoPersona.objects.filter(person_id=Centros, relacion_grupo_id=5):
                continue
            else:
                errores.append({"field": "CenCost", "data": Centros,
                                "message": "Centro de costos no encontrado"})
        if persona.objects.filter(email=data["email"]):
            errores.append({"field": "email", "data": data["email"],
                            "message": "Email ya registrado"})
        if len(data["CenCost"]) == 0:
            errores.append({"field": "CenCost", "data": data["CenCost"],
                            "message": "Debe asignar al menos 1 centro de costo"})
        if errores:
            raise ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [errores]})
        else:
            return data

    def create(self, validated_data, grupoPermiso, pk_user):
        ExistGroup(grupoPermiso)
        name = self.validated_data.get("name")
        colaborador = persona.objects.create_colaborador(
            name=name,
            email=self.validated_data.get("email"),
            fecha_nacimiento=self.validated_data.get("fecha_nacimiento"),
            phone=self.validated_data.get("phone"),
        )

        for Centros in self.validated_data.get("CenCost"):
            centroColabo = grupoPersona.objects.create(empresa_id=Centros, person_id=colaborador.id,
                                                       relacion_grupo_id=8)
        # grupoPersona.objects.create(empresa_id=pk_user, person_id=colaborador.id, relacion_grupo_id=14)
        # Solicitudes.objects.create(tipoSolicitud_id=1, personaSolicitud_id=colaborador.id, estado_id=1, intentos=0)
        UserAddGroup(grupoPermiso, colaborador)
        return colaborador


class EditarColaborador(Serializer):
    phone = CharField()
    CenCost = ListField()

    def validate(self, data):
        errores = []
        for Centros in data["CenCost"]:
            if grupoPersona.objects.filter(person_id=Centros, relacion_grupo_id=5):
                continue
            else:
                errores.append({"field": "CenCost", "data": Centros,
                                "message": "Centro de costos no encontrado"})
        if len(data["CenCost"]) == 0:
            errores.append({"field": "CenCost", "data": data["CenCost"],
                            "message": "Debe asignar al menos 1 centro de costo"})
        if errores:
            raise ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [errores]})
        else:
            return data

    def update(self, colaborador, groupId):
        ExistGroup(grupoPermiso=groupId)
        CenCost = self.validated_data.get("CenCost")
        listCrear = []
        queryTotal = grupoPersona.objects.filter(person_id=colaborador, relacion_grupo_id=8).count()
        countList = len(CenCost)
        resultado = queryTotal - countList
        metodo = "None"
        if int(resultado) > 0:
            metodo = "d"
        if int(resultado) < 0:
            resultado = str(resultado).replace("-", "")
            metodo = "c"
            for list in CenCost:
                queryset = grupoPersona.objects.filter(person_id=colaborador, relacion_grupo_id=8).values("empresa_id")
                if list == queryset:
                    continue
                else:
                    listCrear.append(list)
        if metodo == "d":
            n = 1
            for instance in grupoPersona.objects.filter(person_id=colaborador, relacion_grupo_id=8):
                instance.delete()
                if n == resultado:
                    break
                n = n + 1
        if metodo == "c":
            for n in itertools.count(start=0):
                if int(n) == int(resultado):
                    break
                centroColabo = grupoPersona.objects.create(empresa_id=CenCost[0], person_id=colaborador,
                                                           relacion_grupo_id=8, nombre_grupo="Colaborador")
        for queryCen in grupoPersona.objects.filter(person_id=colaborador, relacion_grupo_id=8):
            instance = grupoPersona.objects.get(id=queryCen.id)
            for CenCostos in CenCost:
                instance.empresa_id = CenCostos
                instance.save()
                break
        UserEditGroup(colaborador, groupId)
        return


class CentroCostosSerializer(Serializer):
    CentroCostos = SerializerMethodField()

    def get_CentroCostos(self, obj: CentroCostos):
        queryset = persona.objects.get(id=obj.person_id)
        return {"id": queryset.id, "name": queryset.name}


class CrearDocumentosColaborador(Serializer):
    def create(self, colaborador, documentoR, documentoI, pk_user):
        errores = []
        if persona.objects.filter(id=colaborador):
            instance = persona.objects.get(id=colaborador)
        else:
            errores.append({"field": "id", "data": colaborador,
                            "message": "Colaborador no encontrado"})
        if documentos.objects.filter(person_id=instance.id, historial=False, tdocumento_id=16):
            errores.append({"field": "Responsiva", "data": "",
                            "message": "Carta Responsiva ya esta registrada"})
        if documentos.objects.filter(person_id=instance.id, historial=False, tdocumento_id=12):
            errores.append({"field": "Identificacion", "data": "",
                            "message": "Identificacion ya esta registrada"})
        if errores:
            raise ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [errores]})
        grupoPersona.objects.create(nombre_grupo="Colaborador", empresa_id=pk_user, person_id=colaborador,
                                    relacion_grupo_id=14)
        instance_document = documentos.objects.create(person_id=instance.id, comentario="Carta Responsiva colaborador",
                                                      tdocumento_id=12)
        file = documentoI
        create_pdf_data_v2(file, instance)
        with open('TMP/web/' + instance.username + '.pdf', 'rb') as document:
            instance_document.documento = File(document)
            instance_document.save()
        EliminarArchivo(dato_unico=instance.username, ruta="TMP/web/", tipo="pdf")
        instance_document2 = documentos.objects.create(person_id=instance.id, comentario="Carta Responsiva colaborador",
                                                       tdocumento_id=16)

        file = documentoR
        create_pdf_data_v2(file, instance)
        with open('TMP/web/' + instance.username + '.pdf', 'rb') as document_2:
            instance_document2.documento = File(document_2)
            instance_document2.save()
        EliminarArchivo(dato_unico=instance.username, ruta="TMP/web/", tipo="pdf")
        solicitud = "{'solicita': " + str(pk_user) + "}"
        Solicitudes.objects.create(nombre="Solicitud Colaborador", tipoSolicitud_id=1, personaSolicitud_id=colaborador,
                                   estado_id=1, intentos=0, referencia=solicitud)
        return


class EditarDocumentosColaborador(Serializer):
    def update(self, colaborador, documentoR, documentoI):
        errores = []
        if persona.objects.filter(id=colaborador):
            instance = persona.objects.get(id=colaborador)
        else:
            errores.append({"field": "id", "data": colaborador,
                            "message": "Colaborador no encontrado"})
        if documentos.objects.filter(
                Q(person_id=instance.id, historial=False, tdocumento_id=16, status="P") | Q(person_id=instance.id,
                                                                                            historial=False,
                                                                                            tdocumento_id=16,
                                                                                            status="C")):
            errores.append({"field": "Responsiva", "data": "",
                            "message": "Carta Responsiva ya esta registrada"})
        if documentos.objects.filter(
                Q(person_id=instance.id, historial=False, tdocumento_id=12, status="P") | Q(person_id=instance.id,
                                                                                            historial=False,
                                                                                            tdocumento_id=12,
                                                                                            status="C")):
            errores.append({"field": "Identificacion", "data": "",
                            "message": "Identificacion ya esta registrada"})
        if errores:
            raise ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [errores]})
        instance_document = documentos.objects.create(person_id=instance.id, comentario="Carta Responsova colaborador",
                                                      tdocumento_id=12)
        file = documentoI
        create_pdf_data_v2(file, instance)
        with open('TMP/web/' + instance.username + '.pdf', 'rb') as document:
            instance_document.documento = File(document)
            instance_document.save()
        EliminarArchivo(dato_unico=instance.username, ruta="TMP/web/", tipo="pdf")

        instance_document2 = documentos.objects.create(person_id=instance.id, comentario="Carta Responsova colaborador",
                                                       tdocumento_id=16)
        file = documentoR
        create_pdf_data_v2(file, instance)
        with open('TMP/web/' + instance.username + '.pdf', 'rb') as document_2:
            instance_document2.documento = File(document_2)
            instance_document2.save()
        EliminarArchivo(dato_unico=instance.username, ruta="TMP/web/", tipo="pdf")
        return


class pruebas(Serializer):
    id = ReadOnlyField()
    documento = FileField()


class DarBajaColaborador(Serializer):
    comentario = CharField(allow_null=False, allow_blank=False)

    def create(self, documento, instance, **kwargs):
        instance_document = documentos.objects.create_document(19, instance.id, self.validated_data.get("comentario"))

        file_name = create_file(documento, instance.id)

        with open(file_name, 'rb') as document:
            instance_document.documento = File(document)
            instance_document.save()
        remove(file_name)


# (ManuelCalixtro 28-11-2021 Se agrego el serializador para ver detalle de un colaborador)
class DetailsColaborator(Serializer):
    id = IntegerField()
    status = CharField()
    comentario = CharField()
    tipo_documento = SerializerMethodField()
    documento = SerializerMethodField()

    def get_tipo_documento(self, obj: tipo_documento):
        queryset = TDocumento.objects.filter(id=obj.tdocumento_id).values('nombreTipo')
        return queryset

    def get_documento(self, obj: documento):
        queryset = obj.get_url_aws_document()
        return queryset
