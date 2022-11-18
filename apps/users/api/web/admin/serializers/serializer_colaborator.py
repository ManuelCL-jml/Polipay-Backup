# import datetime
from rest_framework.serializers import *
# from apps.solicitudes.models import *
from apps.users.management import *
from drf_extra_fields.fields import Base64FileField

# (AAF 2021-12-27)
class SerializerDocumento(Serializer):
    id = ReadOnlyField()
    documento = Base64FileField()
    status = CharField()
    comentario = CharField()
    tdocumento_id = IntegerField()

# (AAF 2021-12-27)
class SerializerDocumentosOut(Serializer):
    colaboratorDetail = SerializerMethodField()
    colaboratorDom = SerializerMethodField()
    documentos_colaborator = SerializerMethodField()
    centros_costo = SerializerMethodField()
    permisos = SerializerMethodField()

    def get_documentos_colaborator(self, obj: documentos_colaborator):
        queryset = documentos.objects.filter(person_id=obj.person_id)
        return SerializerDocumento(queryset, many=True).data

    def get_colaboratorDetail(self, obj: colaboratorDetail):
        queryset = persona.objects.values('id', 'name','last_name', 'rfc', 'clave_traspaso', 'banco_clabe','email','is_active','phone').get(id=obj.person_id)
        return queryset

    def get_colaboratorDom(self, obj: colaboratorDom):
        domicilio_Col = domicilio.objects.values('codigopostal', 'colonia', 'alcaldia_mpio', 'estado', 'calle',
                                                 'no_exterior', 'no_interior', 'pais').filter(domicilioPersona_id=obj.person_id, historial=False)
        data = []
        for dom in domicilio_Col:
            data.append(dom)
        return domicilio_Col

    def get_centros_costo(self, obj: colaboratorDom):
        queryset = grupoPersona.objects.get_values_empresa(obj.person_id,8)
        return queryset

    def get_permisos(self,obj: colaboratorDom):
        user = persona.objects.get(id=obj.person_id)
        namepermisions = user.groups.all().values("name")
        listP = []
        for permission in namepermisions:
            data = permission['name'].split('*')
            listP.append(data[1])
        return listP

# (AAF 2021-12-27)
class SerListColaboratorAct(Serializer):
    id = IntegerField()
    fechaAlta = SerializerMethodField()
    permisos = SerializerMethodField()
    name = SerializerMethodField()
    correo = SerializerMethodField()

    def get_name(self,obj:id):
        return  obj.person.name

    def get_fechaAlta(self, obj: id):
        return obj.person.date_joined

    def get_permisos(self, obj: id):
        user = persona.objects.get(id=obj.person_id)
        namepermisions = user.groups.all().values("name")
        listP = ""
        for permission in namepermisions:
            data = permission['name'].split('*')
            if len(listP)==0:
                listP = data[1]
            else:
                listP = listP + "," + data[1]
        return listP

    def get_correo(self, obj: id):
        return obj.person.email

    # def to_representation(self, instance):
    #     return {
    #         'Colaborador': instance.person.get_centro_costo(),
    #         'cuentas': cuenta.objects.values('id', 'cuenta', 'cuentaclave', 'is_active', 'monto').filter(
    #             persona_cuenta_id=instance.person_id)
    #     }

# (AAF 2021-12-27)
class SerializerListSolColaborator(Serializer):

    def to_representation(self, instance):
        lista = {
            'idCC':instance.personaSolicitud.id,
            'colaboradores': instance.personaSolicitud.name,
            'tipo_solicitud': instance.tipoSolicitud.nombreSol,
            'fecha_Sol': instance.fechaSolicitud,
            'intentos': instance.intentos,
            'estado': instance.estado.nombreEdo,
            'idSol': instance.id
        }
        return lista


class SerializerVerifyDocuments(Serializer):
    document_id = IntegerField()
    status = CharField()
    comment = CharField(allow_null=True)

    def validate(self, attrs):
        return attrs

    def update(self, **kwargs):
        documentos.objects.update_document(
            document_id=self.validated_data.get('document_id'),
            user_auth=self.context.get('user_auth'),
            status=self.validated_data.get('status'),
            comment=self.validated_data.get('comment'),
        )


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

    def update(self, **kwargs) -> persona:
        print(self.validated_data)
        return persona.objects.filter(
            id=self.context.get('person_id')
        ).update(**self.validated_data)







