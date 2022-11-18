from typing import List

from rest_framework.serializers import *

from polipaynewConfig.exceptions import add_list_errors, status_error
from apps.users.models import grupoPersona


class SerializerGrupoPersona(Serializer):
    nombre_grupo = CharField(read_only=True)
    person_id = IntegerField()
    empresa_id = IntegerField(read_only=True)
    relacion_grupo_id = IntegerField(read_only=True)
    is_admin = BooleanField(default=False)

    def validate(self, attrs):
        longitud_lista_personal_externo: int = self.context['longitud_lista_personal_externo']
        nombre_grupo: str = self.context['nombre_grupo']
        company_id: int = self.context['empresa_id']
        is_admin = self.context['is_admin']
        list_errors: List = []

        nombre_grupo_exist = grupoPersona.objects.filter(
            empresa_id=company_id,
            relacion_grupo_id=7,
            nombre_grupo__icontains=nombre_grupo
        ).exists()

        persona_externa_data = grupoPersona.objects.filter(
            person_id=attrs['person_id'],
            relacion_grupo_id=7,
            nombre_grupo__icontains=nombre_grupo,
            empresa_id=company_id
        ).values('person__name', 'person__last_name').first()

        if longitud_lista_personal_externo < 2:
            add_list_errors({
                "field": None,
                'message': 'Personal insuficiente para crear un grupo de personal externo',
                "data": None
            }, list_errors)

        if nombre_grupo_exist:
            add_list_errors({
                "field": "nombre_grupo",
                "message": "Ya existe el grupo",
                "data": nombre_grupo.upper(),
            }, list_errors)

        if persona_externa_data:
            full_name = f"{persona_externa_data['person__name']} {persona_externa_data['person__last_name']}"

            add_list_errors({
                "field": "Personal Externo",
                "message": f"La persona {full_name} ya pertenece a este grupo",
                "data": f"{full_name}",
            }, list_errors)

        if not is_admin:
            add_list_errors({
                'field': 'Unauthorized',
                'message': 'No tienes permiso para realizar esta acción'
            }, list_errors)

        if len(list_errors) > 0:
            raise ValidationError(status_error(list_errors))

        if self.context['person_id'] == attrs['person_id']:
            attrs['is_admin'] = True

        attrs['nombre_grupo'] = nombre_grupo
        attrs['empresa_id'] = company_id
        attrs['relacion_grupo_id'] = 7

        return attrs

    def create(self, validated_data):
        return grupoPersona.objects.create(**validated_data)


class SerializerEditGrupoPersona(Serializer):
    nombre_grupo = CharField(read_only=True)
    person_id = IntegerField()
    empresa_id = IntegerField(read_only=True)
    relacion_grupo_id = IntegerField(read_only=True)
    is_admin = BooleanField(default=False)

    def validate(self, attrs):
        list_errors: List = []
        nombre_grupo: str = self.context['nombre_grupo']
        company_id: int = self.context['empresa_id']

        persona_externa_data = grupoPersona.objects.filter(
            person_id=attrs['person_id'],
            relacion_grupo_id=7,
            nombre_grupo__icontains=nombre_grupo,
            empresa_id=company_id
        ).values('person__name', 'person__last_name').first()

        if persona_externa_data:
            full_name = f"{persona_externa_data['person__name']} {persona_externa_data['person__last_name']}"

            add_list_errors({
                "field": "Personal Externo",
                "message": f"La persona {full_name} ya pertenece a este grupo",
                "data": f"{full_name}",
            }, list_errors)

        if len(list_errors) > 0:
            raise ValidationError(status_error(list_errors))

        attrs['nombre_grupo'] = nombre_grupo
        attrs['empresa_id'] = company_id
        attrs['relacion_grupo_id'] = 7

        return attrs

    def create(self, validated_data):
        return grupoPersona.objects.create(**validated_data)
