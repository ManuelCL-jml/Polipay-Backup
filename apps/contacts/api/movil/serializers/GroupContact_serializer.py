from rest_framework import serializers
from rest_framework.exceptions import ParseError

from apps.contacts.api.movil.serializers.Group_serializer import serializerGrupoOutV2
from apps.contacts.models import *
from apps.transaction.serializers import *
from apps.transaction.models import tipo_transferencia

class groupIn(serializers.Serializer):
    id = serializers.IntegerField()


class serializerGrupoContactoIn(serializers.Serializer):
    group = groupIn(many=True)
    contacts = serializers.IntegerField()

    def validate_contacts(self,data):
        contacto = contactos.objects.filter(id=data)
        if len(contacto) !=0:
            return data
        else:
            raise serializers.ValidationError("id no encontrada")

    def create(self, validated_data):
        try:
            grupos_data_list = validated_data.pop("group")
            for group in grupos_data_list:
                queryset = grupoContacto.objects.filter(group_id=group["id"],contacts_id=validated_data.get("contacts"))
                if len(queryset) !=0:
                    pass
                else:
                    grupcontact = grupoContacto.objects.create(group_id=group["id"],contacts_id=validated_data.get("contacts"))
        except Exception as inst:
            raise ParseError({'status': inst})


class serializerGrupoContactoOut(serializers.Serializer):
    id = serializers.ReadOnlyField()
    name = serializers.CharField()
    grupos = serializers.SerializerMethodField()

    def get_grupos(self,obj:grupos):
        queryset = contactos.objects.filter(person_id=obj.id)
        grupos_list = []
        for contac in queryset:
            querygrupocontac = grupoContacto.objects.filter(contacts_id=contac.id)
            for grupocontac in querygrupocontac:
                querygroup = grupo.objects.get(id=grupocontac.group_id)
                grupos_list.append(querygroup)
        return serializerGrupoOutV2(grupos_list,many=True).data
