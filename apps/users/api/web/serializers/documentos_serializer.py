import datetime
import base64
from os import remove

from django.core.files import File
from django.db.models import Q

from rest_framework.serializers import *

from MANAGEMENT.Utils.utils import create_file
from apps.users.models import documentos
from apps.users.models import *
from apps.users.management import *


class SerializerUpDocumentIn(Serializer):
    tdocumento_id = IntegerField()
    documento = CharField()
    comentario = CharField(allow_null=True, allow_blank=True)

    def validate(self, attrs):
        # documents = documentos.objects.filter(
        #     Q(person_id=attrs['person_id']) & Q(tdocumento_id=attrs['tdocumento_id'])).exists()
        #
        # if documents:
        #     raise ValidationError({'status': ["Este archivo ya fue subido"]})
        return attrs

    def create(self, **kwargs):
        try:
            file_name = create_file(kwargs.get('validated_data').get("documento"), kwargs.get('id'))
            kwargs.get('validated_data')['documento'] = file_name
            instance_document = documentos.objects.create(**kwargs.get('validated_data'), person_id=kwargs.get('id'))

            with open(file_name, 'rb') as document:
                instance_document.documento = File(document)
                instance_document.save()

            remove(file_name)
            return instance_document
        except Exception as e:
            pass

# class SerializerDocumentIn(Serializer):
#     tdocumento = CharField(allow_blank=False, allow_null=False)  # I
#
#     def validate_tdocumento(self, data):
#         documents = documentos.objects.filter(person_id=self.context['pk_user'], tdocumento=data)
#         if len(documents) != 0:
#             raise ValidationError({'status': ["Este archivo ya fue subido"]})
#         return data
#
#     def upload_file(self, instance):
#         file = documentos.objects.create(person=instance, tdocumento=self.validated_data.get("tdocumento"))
#         with open('TEMPLATES/FileSystem/Administrativo-23062021.xlsx', 'rb') as document:
#             file.documento = File(document)
#             file.save()
#
#         return file


class SerializerDocumentsOut(Serializer):
    id = ReadOnlyField()
    documento = FileField()
    tdocumento_id = SerializerMethodField()
    status = CharField()
    comentario = CharField()
    load = DateTimeField()
    status = CharField()
    userauth_id = ReadOnlyField()
    dateauth = CharField()

    def get_tdocumento_id(self, obj: tdocumento_id):
        return obj.tdocumento.nombreTipo


class SerializerDocumentsPersonOut(Serializer):
    documents = SerializerMethodField()

    def get_documents(self, obj: documents):
        queryset = documentos.objects.filter(person_id=obj.id, status=self.context['type'])
        return SerializerDocumentsOut(queryset, many=True).data


class SerializerDocumentsPersonAllOut(Serializer):
    documents = SerializerMethodField()

    def get_documents(self, obj: documents):
        queryset = documentos.objects.filter(person_id=obj.id)
        return SerializerDocumentsOut(queryset, many=True).data


class SerializerAuthorizeIn(Serializer):
    status = CharField(allow_null=False, allow_blank=False)
    comentario = CharField(allow_null=True, allow_blank=True)

    def validate_status(self, data):
        if data == "P" or data == "C" or data == "D":
            return data
        else:
            raise ValidationError("Status no reconocido")

    def update(self, instance, pk_user):
        dateNow = datetime.datetime.now()
        instance.comentario = self.validated_data.get("comentario", instance.comentario)
        instance.status = self.validated_data.get("status", instance.status)
        if instance.status == "C":
            instance.authorization = True
            instance.dateauth = dateNow
            instance.userauth_id = pk_user
            if grupoPersona.objects.filter(person_id=instance.person_id,
                                           relacion_grupo_id=8):  ######### se activara colaborador
                queryset = documentos.objects.filter(person_id=instance.person_id, historial=False, status="C").count()
                try:
                    queryDes = documentos.objects.get(person_id=instance.person_id, historial=False, tdocumento_id=19)
                    if queryDes:
                        instanceUser = persona.objects.get(id=queryDes.person_id)
                        instanceUser.is_active = False
                        instanceUser.save()
                except:
                    pass
                if queryset == 2:
                    instanceCola = persona.objects.get(id=instance.person_id)
                    instanceCola.is_active = True
                    instanceCola.save()
        return instance.save()


class DownloadPDF(Serializer):
    documento = FileField()

    def validate(self, attrs):
        print(attrs['documento'])
        return attrs
