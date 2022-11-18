from rest_framework import serializers
from .models import *
from polipaynewConfig.redefectiva import *

"""
    Serializadores para el CRUD de los Codigos de Red Efectiva
"""


class SerializerCodeEfectivaCRD(serializers.Serializer):
    id = serializers.ReadOnlyField()
    code = serializers.IntegerField()
    message = serializers.CharField()

    def validate_code(self, attr):
        queryset = CodeEfectiva.objects.filter(code=attr)
        if len(queryset) > 0:
            message_repeated_code = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": attr,
                        "field": "Code",
                        "message": "Code already used",
                    }
                ]
            }
            raise serializers.ValidationError(message_repeated_code)
        else:
            return attr

    def create(self, validated_data):
        CodeEfectiva.objects.create(**validated_data)


class SerializerCodeEfectivaUpdate(serializers.Serializer):
    id = serializers.ReadOnlyField()
    code = serializers.IntegerField()
    message = serializers.CharField()

    def update(self, instance):
        instance.code = self.validated_data.get('code')
        instance.message = self.validated_data.get('message')
        instance.save()


"""
    Serializadores para el CRUD de TranType
"""

class SerializerTranTypeCRD(serializers.Serializer):
    id = serializers.ReadOnlyField()
    number = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()

    def validate_number(self, attr):
        queryset = TranTypes.objects.filter(number=attr)
        if len(queryset) > 0:
            message_repeated_number = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": attr,
                        "field": "number",
                        "message": "Number already used",
                    }
                ]
            }
            raise serializers.ValidationError(message_repeated_number)
        else:
            return attr

    def create(self, validated_data):
        TranTypes.objects.create(**validated_data)


class SerializerTranTypeUpdate(serializers.Serializer):
    id = serializers.ReadOnlyField()
    number = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()

    def update(self, instance):
        instance.number = self.validated_data.get('number')
        instance.name = self.validated_data.get('name')
        instance.description = self.validated_data.get('description')
        instance.save()


"""
    Serializadores para el CRUD de TransmitterHaveTranType
"""

class SerializerTransmitterHaveTrantypeCDU(serializers.Serializer):
    id = serializers.ReadOnlyField()
    transmitter = serializers.IntegerField()
    type = serializers.IntegerField()

    def validate_transmitter(self, attr):
        queryset = Transmitter.objects.filter(id=attr)
        if len(queryset) <= 0:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": attr,
                        "field": "transmitter",
                        "message": "Transmitter not found",
                    }
                ]
            }
            raise serializers.ValidationError(message_not_found)
        else:
            return attr

    def validate_type(self, attr):
        queryset = TranTypes.objects.filter(id=attr)
        if len(queryset) <= 0:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": attr,
                        "field": "type",
                        "message": "Trantype not found",
                    }
                ]
            }
            raise serializers.ValidationError(message_not_found)
        else:
            return attr

    def create(self, validated_data):
        queryset = TransmitterHaveTypes.objects.filter(transmitter=self.validated_data.get('transmitter'), type=self.validated_data.get('type'))
        if len(queryset) > 0:
            message_already_have = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": "",
                        "field": "",
                        "message": "Transmitter already have that TranType",
                    }
                ]
            }
            raise serializers.ValidationError(message_already_have)
        instance_transmitter = Transmitter.objects.get(id=self.validated_data.get('transmitter'))
        instance_type = TranTypes.objects.get(id=self.validated_data.get('type'))
        TransmitterHaveTypes.objects.create(transmitter=instance_transmitter, type=instance_type)

    def update(self, instance):
        instance.transmitter = Transmitter.objects.get(id=self.validated_data.get('transmitter'))
        instance.type = TranTypes.objects.get(id=self.validated_data.get('type'))
        instance.save()

class SerializerSolicita(serializers.Serializer):
    Comercio = serializers.IntegerField()
    sSucursal = serializers.CharField(required=False, allow_null=True)
    Corresponsal = serializers.IntegerField()
    sCaja = serializers.CharField(required=False, allow_null=True)
    sCodigo = serializers.CharField()
    TranType = serializers.IntegerField()
    Emisor = serializers.CharField()
    Importe = serializers.IntegerField(required=False, allow_null=True)
    Comision = serializers.IntegerField(required=False, allow_null=True)
    Cargo = serializers.IntegerField(required=False, allow_null=True)
    sRef1 = serializers.CharField(required=False, allow_null=True)
    sRef2 = serializers.CharField(required=False, allow_null=True)
    sRef3 = serializers.CharField(required=False, allow_null=True)
    sTicket = serializers.CharField(required=False, allow_null=True)
    sOperador = serializers.CharField(required=False, allow_null=True)
    sSku = serializers.CharField(required=False, allow_null=True)
    EntryMode = serializers.CharField(required=False, allow_null=True)

    def create(self, validated_data):
        response, ticket = solicita(validated_data)
        return response


