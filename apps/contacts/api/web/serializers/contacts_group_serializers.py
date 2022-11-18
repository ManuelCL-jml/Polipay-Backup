from rest_framework.serializers import *

from apps.contacts.models import grupo, grupoContacto, contactos


# (ManuelCalixtro 12/11/2021 ) Serializadores para crear un grupo de contactos frecuentes

class SerializerCreateGroups(Serializer):
    nombreGrupo = CharField()

    def validate(self, attrs):
        nombre_grupo = grupoContacto.objects.filter(contacts__person_id=self.context['user_id']).values(
            'group__nombreGrupo', 'group__id')
        for nombre in nombre_grupo:
            if attrs['nombreGrupo'] == nombre['group__nombreGrupo']:
                raise ValidationError({'code': 400,
                                       'status': 'error',
                                       'message': 'Ya existe un grupo registrado con este nombre'})
        return attrs

    def createGroup(self, validated_data):
        grupos = grupo.objects.create(**validated_data)
        return grupos

# (ManuelCalixtro 12/11/2021 ) Serializadores para agregar un contacto frecuente a la hora de crear un grupo

class SerializerAddFrecuentContacts(Serializer):
    group_id = IntegerField(read_only=True)
    contacts_id = IntegerField(allow_null=True)

    def validate(self, attrs):
        attrs['group_id'] = self.context['group_id']
        return attrs

    def create(self, lista_objects_contacts):
        return grupoContacto.objects.bulk_create(lista_objects_contacts)


#(ManuelCalixtro 12/11/2021)Serializadores para actualizar el nombre de un grupo

class SerializerPutGroupContacts(Serializer):
    id = ReadOnlyField()
    nombreGrupo = CharField()



    def update(self, instance, validated_data):
        instance.nombreGrupo = validated_data.get("nombreGrupo", instance.nombreGrupo)
        instance.save()
        return instance

#(ManuelCalixtro 12/11/2021)Serializadores para agregar o quitar contactos frecuentes de un grupo
class SerializerEditGroupContact(Serializer):
    group_id = IntegerField(read_only=True)
    contacts_id = IntegerField(allow_null=True)

    def validate(self, attrs):
        attrs['group_id'] = self.context['group_id']
        return attrs

    def create(self, validated_data):
        return grupoContacto.objects.create(**validated_data)


class SerializerListFrecuentsContactsGroups(Serializer):
    grupos = SerializerMethodField()

    def get_grupos(self, obj: grupos):
        group_instance = grupoContacto.objects.filter(contacts__person_id=self.context['user_id']).values('group__nombreGrupo','group__id')
        lista = []
        for i in group_instance:

            data = {
                'nombre_grupo': i['group__nombreGrupo'],
                'id_grupo': i['group__id']
            }
            if i['group__id'] > 1:
                lista.append(data)
                print(lista)
        return lista
