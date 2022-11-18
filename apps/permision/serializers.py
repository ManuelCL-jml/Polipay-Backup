# Modulos nativos
from django.contrib.auth.models import Permission
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from django.core.files import File

from rest_framework import serializers

# Modulos locales
from .models import *
from apps.users.models import *


class serializerPermisionOut(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'


class serializerGroupOut(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'


class ListarPermisosOut(serializers.Serializer):
    id = serializers.ReadOnlyField()
    name = serializers.CharField()


class ListGruposPermisosNombre(serializers.Serializer):
    id = serializers.ReadOnlyField()
    name = serializers.CharField()
    fechaRegistro = serializers.DateField()
