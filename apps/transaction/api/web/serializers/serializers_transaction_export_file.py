
from rest_framework.serializers import *
from rest_framework import serializers

from apps.users.models import documentos



class SerializerExportDataToCSV(serializers.Serializer):

    documento   = serializers.CharField(allow_null=False, required=True)
    comentario  = serializers.CharField(required=False, default=None)
    person_id   = serializers.IntegerField(required=False)
    id          = IntegerField(required=False)

    #def create(self, validated_data, idPerson):
    def create(self, data):
        try:
            #instance = documentos.objects.create(person_id=idPerson, **validated_data)
            instance = documentos.objects.create(person_id=data[""], **validated_data)
        except:
            return False
        return instance

    """
    def validate(self, attrs):
        return attrs

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
    
    def getFileCSV(self, data):
        pass
    """