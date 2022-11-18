from rest_framework import serializers

from apps.transaction.models import *
from apps.users.management import *


class serializerTipo_transferenciaIn(serializers.Serializer):
    nombre_tipo = serializers.CharField()

    def create(self, validated_data):
        nombre_tipos = tipo_transferencia.objects.create(**validated_data)
        return nombre_tipos


class serializerTipo_transferenciaOut(serializers.Serializer):
    id = serializers.ReadOnlyField()
    nombre_tipo = serializers.CharField()


class serializerTipo_transferenciaEdit(serializers.Serializer):
    id = serializers.ReadOnlyField()
    nombre_tipo = serializers.CharField()

    def update(self, instance, validated_data):
        instance.nombre_tipo = validated_data.get("nombre_tipo", instance.nombre_tipo)
        instance.save()
        return instance
