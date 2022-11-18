from rest_framework import serializers


class serializerTipoTransferenciaOut(serializers.Serializer):
    id = serializers.ReadOnlyField()
    nombre_tipo = serializers.CharField()


class serializerStatusOut(serializers.Serializer):
    id = serializers.ReadOnlyField()
    nombre = serializers.CharField()


class serializerBancosOut(serializers.Serializer):
    id = serializers.ReadOnlyField()
    clabe = serializers.CharField()
    institucion = serializers.CharField()
    participante = serializers.IntegerField()
