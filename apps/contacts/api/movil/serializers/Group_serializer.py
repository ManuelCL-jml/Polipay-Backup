from rest_framework import serializers

from apps.contacts.api.movil.serializers.Contacts_serializer import *
from apps.contacts.models import *



class serializerGrupoIn(serializers.Serializer):
    nombreGrupo = serializers.CharField()

    def createGrupo(self, validated_data):
        grupos = grupo.objects.create(**validated_data)
        return grupos

class serializerGrupoOutV1(serializers.Serializer):
    id = serializers.ReadOnlyField()
    nombreGrupo = serializers.CharField()


class serializerGrupoOutV2(serializers.Serializer):
    id = serializers.ReadOnlyField()
    nombreGrupo = serializers.CharField()
    contacts = serializers.SerializerMethodField()

    def get_contacts(self,obj:contacts):
        queryGroupPerson = grupoContacto.objects.filter(group_id=obj.id)
        list_contact = []
        for groupP in queryGroupPerson:
            queryContac = contactos.objects.get(id=groupP.contacts_id)
            list_contact.append(queryContac)
        return SerializerContactsOut(list_contact, many=True).data


class serializerEditGrupoIn(serializers.Serializer):
    id = serializers.ReadOnlyField()
    nombreGrupo = serializers.CharField()

    def update(self, instance, validated_data):
        instance.nombreGrupo = validated_data.get("nombreGrupo",instance.nombreGrupo)
        instance.save()
        return instance