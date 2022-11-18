from typing import List, Dict, Optional

from rest_framework.generics import ListAPIView, DestroyAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework import pagination
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import GenericViewSet

from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.EndPoint.EndPointInfo import get_info
from apps.contacts.api.web.serializers.contacts_group_serializers import *

from apps.contacts.models import grupo, grupoContacto
from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from apps.users.management import get_Object_orList_error


# (ManuelCl 01/12/2021) Crea grupos de contactos frecuentes
class CreateContactsGroups(GenericViewSet):
    serializer_class = SerializerAddFrecuentContacts
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear grupo de contactos frecuentes"]

    def crear_object(self, contacts_id: int, group_id: int):
        return grupoContacto(
            contacts_id=contacts_id,
            group_id=group_id
        )

    def create(self, request):
        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        context = {
            'user_id': request.query_params['user_id']
        }
        serializer = SerializerCreateGroups(data = request.data, context=context)
        serializer.is_valid(raise_exception = True)
        serializer.createGroup(serializer.validated_data)
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer.data)
        instance_group = grupo.objects.last()
        list_frecuents_contacts: List = request.data['frecuent_contacts']

        context = {
            'group_id': instance_group.id,
            'user_id': request.query_params['user_id'],
            'list_frecuents_contacts': list_frecuents_contacts
        }

        lista_objects_contacts = []

        for contact in list_frecuents_contacts:
            serializer_add_contacts = self.serializer_class(data=contact, context=context)
            serializer_add_contacts.is_valid(raise_exception=True)
            objetos = self.crear_object(**serializer_add_contacts.data)
            lista_objects_contacts.append(objetos)
        serializer_add_contacts.create(lista_objects_contacts)
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer_add_contacts.data)

        return Response({'Code': 201,
                         'status': 'created',
                         'message': 'Grupo Creado'})


# (ManuelCl 01/12/2021) Actualiza grupo de contactos frecuentes
class UpdateContactsGroups(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Editar grupo de contactos frecuentes"]
    serializer_class = SerializerEditGroupContact

    def create(self):
        pass

    def editar_grupo_contact(self, group_id: int, list_frecuent_contacts: List) -> bool:

        context = {
            'group_id': group_id
        }

        for index in list_frecuent_contacts:
            if index['method'] == "new":
                serializer = self.serializer_class(data=index, context=context)
                serializer.is_valid(raise_exception=True)
                serializer.create(serializer.data)

            if index['method'] == "delete":
                self.delete_person_group(group_id, index['contacts_id'])

        return True

    def delete_person_group(self, group_id, contacts_id: int) -> bool:
        grupo_persona = grupoContacto.objects.get(
            group_id = group_id,
            contacts_id=contacts_id,
        )

        grupo_persona.delete()
        return True

    def put(self, request):
        user_id = self.request.query_params['user_id']
        group_id = self.request.query_params['group_id']

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        group_instance = get_Object_orList_error(grupo, id=group_id)
        context = {
            'user_id': user_id
        }
        serializer = SerializerPutGroupContacts(data=request.data, context= context)
        serializer.is_valid(raise_exception = True)
        serializer.update(group_instance, serializer.validated_data)

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer.data)

        list_frecuent_contacts = request.data['personal_externo']
        self.editar_grupo_contact(group_id, list_frecuent_contacts)

        return Response({'code': 200,
                         'status': 'update',
                         'message': 'Grupo Actualizado'})


# (ManuelCl 01/12/2021) Elimina grupo de contactos frecuentes
class DeleteContactsGroups(DestroyAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Eliminar grupo de contactos frecuentes"]

    def create(self, request):
        pass

    def delete_group(self, group_id: int):
        grupoContacto.objects.filter(
            group_id=group_id
        ).delete()
        return True

    def destroy(self,  request, *args, **kwargs):
        group_id = self.request.query_params['group_id']

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        self.delete_group(group_id)

        instance = get_Object_orList_error(grupo,id=group_id)
        instance.delete()

        R = {'code': 200, 'status': 'delete', 'message': 'Grupo Eliminado'}

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=R)
        return Response(R)


# (ManuelCl 01/12/2021) Listar grupos de contactos frecuentes
class ListFrecuentsContactsGroups(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver grupos de contactos frecuentes"]

    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        user_id= self.request.query_params['user_id']
        log.json_request(request.query_params)

        person_groups = grupoContacto.objects.list_group_contacts(person_id=user_id)
        groups_name = grupo.objects.filter(id__in=person_groups).values('id', 'nombreGrupo')

        for i in groups_name:
            log.json_response(i)

        return Response(groups_name)


# (ManuelCl 01/12/2021) Endpoint para ver detalles de un grupo de frecuentes
class DetailsFrecuentsContactsGroups(RetrieveAPIView):#nuevo

    def retrieve(self, request, *args, **kwargs):
        group_id = self.request.query_params['group_id']

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        nombre_grupo = grupo.objects.get(id=group_id)
        get_contacts = grupoContacto.objects.filter(group_id=group_id).values('contacts__id', 'contacts__nombre')

        for i in get_contacts:
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                              objJsonRequest=i)

        R = {'nombreGrupo': nombre_grupo.nombreGrupo, 'contactos': get_contacts}
        return Response(R)
