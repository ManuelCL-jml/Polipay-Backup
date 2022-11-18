from django.core.files import File

from rest_framework import serializers

from apps.transaction.models import *
from apps.transaction.management import *
from apps.users.management import *


class serializerTransMasivaProdIn(serializers.Serializer):
    date_liberation = serializers.DateTimeField()
    observations = serializers.CharField()
    data = serializers.ListField()

    def createMasive(self):
        datos = self.validated_data.get("data")
        f = open('file.xlsx', 'rb')
        excel = File(f)
        instanceM = transmasivaprod.objects.create(date_liberation=self.validated_data.get("date_liberation"),
                                                   observations=self.validated_data.get("observations"))
        instanceM.file = excel
        instanceM.date_modified = None
        instanceM.save()
        ceateTransactionIndividualMasive(datos, instanceM)
        return instanceM


class serializerTransmasivaprodOut(serializers.Serializer):
    id = serializers.ReadOnlyField()
    date_created = serializers.DateTimeField()
    date_modified = serializers.DateTimeField()
    date_liberation = serializers.DateTimeField()
    observations = serializers.CharField()
    file = serializers.FileField()
