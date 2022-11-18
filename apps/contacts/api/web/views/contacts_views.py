from typing import Union, ClassVar

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework import pagination
from rest_framework.viewsets import GenericViewSet

from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.EndPoint.EndPointInfo import get_info
from apps.contacts.api.web.serializers.contacs_serializers import SerializerFrecuentContacts, \
    SerializerAddHistoryContact, \
    SerializerMakeOrBreakFrecuentContact, SerializerDeleteFrecuentContact, SerializerUpdateFrecuentConctact, \
    AddFrecuentContactToGroup, UpdateFrecuentContactToGroup, SerializerDetailFrecuentContact
from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from polipaynewConfig.exceptions import *
from apps.contacts.api.movil.serializers.Group_serializer import *


class CreateFrecuentContacts(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear contacto frecuente"]

    serializer_class = SerializerFrecuentContacts

    def crear_object(self, group_id: int, contacts_id: int):
        return grupoContacto(
            contacts_id=contacts_id,
            group_id=group_id
        )

    def create(self, request):
        # (ManuelCalixtro 2021-11-10) Se crea contacto frecuente nuevo y se registra en la tabla, historico contactos\
        # ademas si se desea agregar a un grupo existente tambien se guarda ese registro en la tabla grupo contacto

        person_id = request.query_params['user_id']
        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)
        instanceP = get_Object_Or_Error(persona, id=person_id)

        context = {
            'person_id': instanceP.id,
            'user_log': request.user.id,
            'endpoint': get_info(request)
        }

        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.create()
        instance_contacts = contactos.objects.last()
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer.data)

        context = {
            'contactoRel': instance_contacts.id,
            'Usuario': instanceP.id,
        }

        serializer_add_frecuent = SerializerAddHistoryContact(data=request.data, context=context)
        serializer_add_frecuent.is_valid(raise_exception=True)
        serializer_add_frecuent.create_history_contact()
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer_add_frecuent.data)

        list_frecuents_contacts: List = request.data['frecuent_groups']
        lista_objects_contacts = []

        for group in list_frecuents_contacts:
            serializer_add_contact_to_group = AddFrecuentContactToGroup(data=group)
            serializer_add_contact_to_group.is_valid(raise_exception=True)
            objetos = self.crear_object(**serializer_add_contact_to_group.data)
            lista_objects_contacts.append(objetos)
            if len(lista_objects_contacts) == 0:
                serializer_add_contact_to_group.create_contact_without_group(
                    serializer_add_contact_to_group.validated_data)
                RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                                  objJsonRequest=serializer_add_contact_to_group.data)
        if len(lista_objects_contacts) != 0:
            serializer_add_contact_to_group.create(lista_objects_contacts)
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                              objJsonRequest=serializer_add_contact_to_group.data)
        return Response({'status': 'Add',
                         'Code': 201,
                         'message': 'Contacto frecuente registrado'}, status=status.HTTP_201_CREATED)


# ManuelCL15/12/2021 (actualizar contactos frecuentes)
class UpdateFrecuentContact(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Editar contacto frecuente"]
    serializer_class = SerializerUpdateFrecuentConctact

    def crear_object(self, group_id: int, contacts_id: int):
        return grupoContacto(
            contacts_id=contacts_id,
            group_id=group_id
        )

    def create(self):
        pass

    def put(self, request):
        user_id = request.query_params['user_id']
        contact_id = request.query_params['contact_id']
        log_dict = {
            "params": request.query_params,
            "body": request.data
        }

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        instance_contacts = get_Object_Or_Error(contactos, id=contact_id, person_id=user_id)

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance_contacts, serializer.validated_data)

            history_contact = HistoricoContactos.objects.get(contactoRel_id=contact_id, usuario_id=user_id)

            serializer_put = SerializerAddHistoryContact(data=request.data)
            serializer_put.is_valid(raise_exception=True)
            serializer_put.update_history_contact(history_contact, serializer_put.validated_data)
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                              objJsonRequest=serializer_put.data)

            list_frecuents_contacts: List = request.data['frecuent_groups']
            lista_objects_contacts = []
            context = {
                'contact': contact_id,
                'user_id': user_id
            }
            for group in list_frecuents_contacts:
                serializer_add_contact_to_group = UpdateFrecuentContactToGroup(data=group, context=context)
                serializer_add_contact_to_group.is_valid(raise_exception=True)
                objetos = self.crear_object(**serializer_add_contact_to_group.data)
                lista_objects_contacts.append(objetos)
                if len(lista_objects_contacts) == 0:
                    serializer_add_contact_to_group.create_contact_without_group(
                        serializer_add_contact_to_group.validated_data)
                    RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                                      objJsonRequest=serializer_add_contact_to_group)
            if len(lista_objects_contacts) != 0:
                serializer_add_contact_to_group.create(lista_objects_contacts)
                RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                                  objJsonRequest=serializer_add_contact_to_group.data)
            return Response({'status': 'Update',
                             'Code': 200,
                             'message': 'Se ha actualizado el contacto frecuente'}, status=status.HTTP_200_OK)


# ManuelCL15/12/2021 (Listar contactos frecuentes)
class ListFrecuentsContacts(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver contactos frecuentes"]


    @staticmethod
    def lista_all_contacts(**kwargs):
        l = contactos.objects.filter(
            person_id=kwargs.get('user_id'),
            is_active=True,
            tipo_contacto_id=2,
            nombre__icontains=kwargs.get('nombre', '')
        ).values('id', 'nombre', 'alias', 'is_favorite')

        return l

    @staticmethod
    def list_contacts(lista: list):
        for row in lista:
            contacs_groups = grupoContacto.objects.filter(
                contacts_id=row.get('id')
            ).values('id', 'group__nombreGrupo').first()

            if contacs_groups:
                row['nombreGrupo'] = contacs_groups.get('group__nombreGrupo')
            if not contacs_groups:
                row['nombreGrupo'] = 'Sin grupo'

        return lista

    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        size = self.request.query_params['size']
        log.json_request(request.query_params)

        data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
        contacts = self.list_contacts(self.lista_all_contacts(**data))
        pagination.PageNumberPagination.page_size = size

        page = self.paginate_queryset(contacts)
        log.json_response(page)
        return self.get_paginated_response(page)


# ManuelCL15/12/2021 (Eliminar un contacto frecuente)
class DeleteFrecuentContact(GenericViewSet):
    permission_classes = () #No hay permisos para este end point
    serializer_class = SerializerDeleteFrecuentContact

    def create(self):
        pass

    def put(self, request):
        user_id = request.query_params['user_id']
        contact_id = request.query_params['contact_id']

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        instance_contacts = contactos.objects.get(id=contact_id, person_id =user_id)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception = True)
        serializer.update(instance_contacts, serializer.validated_data)
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer.data)

        history_contact = HistoricoContactos.objects.get(contactoRel_id = contact_id, usuario_id = user_id)

        serializer_del = SerializerAddHistoryContact(data=request.data)
        serializer_del.is_valid(raise_exception=True)
        serializer_del.delete_history_contact(history_contact, serializer_del.validated_data)
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer_del.data)

        instance = grupoContacto.objects.filter(contacts_id = contact_id).first()
        if instance:
            instance.delete()
            succ = {'code':200, 'status':'update', 'message': 'Contacto Frecuente Eliminado'}
            return Response(succ)
        else:
            return Response({'code':200, 'status':'update', 'message': 'Contacto Frecuente Eliminado'})


# ManuelCL15/12/2021 (Reactivar un contacto frecuente)
class ReactivateFrecuentContact(GenericViewSet):
    permission_classes = () #No hay permisos para este end point
    serializer_class = SerializerDeleteFrecuentContact

    def create(self):
        pass

    def put(self, request):
        user_id = request.query_params['user_id']
        contact_id = request.query_params['contact_id']

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        instance_contacts = get_Object_Or_Error(contactos, id=contact_id, person_id=user_id)

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance_contacts, serializer.validated_data)
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                              objJsonRequest=serializer.data)

            history_contact = HistoricoContactos.objects.get(contactoRel_id=contact_id, usuario_id=user_id)

            serializer_del = SerializerAddHistoryContact(data=request.data)
            if serializer_del.is_valid(raise_exception=True):
                serializer_del.reactivate_contact(history_contact, serializer_del.validated_data)
                RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                                  objJsonRequest=serializer_del.data)
            return Response({'code': 201,
                             'status': 'created',
                             'message': 'Contactto Frecuente Registrado'})


# ManuelCL15/12/2021 (Hacer un deshacer favorito un contacto frecuente )
class MakeOrBreakFrecuentContact(GenericViewSet):
    permission_classes = ()  # No hay permisos para este end point
    serializer_class = SerializerMakeOrBreakFrecuentContact

    def create(self):
        pass

    def put(self, request):
        user_id = request.query_params['user_id']
        contact_id = request.query_params['contact_id']

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        instance_contacts = get_Object_Or_Error(contactos, id=contact_id, person_id=user_id)

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance_contacts, serializer.validated_data)
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                              objJsonRequest=serializer.data)
            return Response({'status': 'Update',
                             'Code': 200,
                             'message': 'Tu operacion se realizo de manera satisfactoria'}, status=status.HTTP_200_OK)


# ManuelCL15/12/2021 (ver detaelles de contactos freecuentes)
class DetailFrecuentContact(RetrieveAPIView):

    def get(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        user_id = request.query_params['user_id']
        contact = request.query_params['contact_id']
        log.json_request(request.query_params)

        y = contactos.objects.filter(id=contact, person_id=user_id).values('alias', 'banco', 'cuenta', 'email', 'id',
                                                                   'is_active', 'is_favorite', 'nombre',
                                                                   'rfc_beneficiario')

        for i in y:
            nombre_banco = bancos.objects.filter(id=i['banco']).values('institucion').first()
            i['banco'] = nombre_banco['institucion']
            g = grupoContacto.objects.filter(contacts_id=i.get('id')).values('id', 'group__nombreGrupo').first()
            if g:
                i['nombreGrupo'] = g.get('group__nombreGrupo')
            if not g:
                i['nombreGrupo'] = 'Sin grupo'

            log.json_response(i)
            return Response(i)


# ManuelCL15/12/2021 (listar contactos frecuentes de un centro de costos para transacciones de polipay a polipay
class ListFrecuentContactsCostCenters(ListAPIView):

    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        cost_center = request.query_params['cost_center_id']
        log.json_request(request.query_params)
        cost_center_contacs = contactos.objects.filter(
            person_id=cost_center,
            tipo_contacto_id=1,
            is_active=True
        ).values(
            'id',
            'alias',
            'nombre',
            'cuenta',
            'email',
            'rfc_beneficiario')

        log.json_response({cost_center_contacs})
        return Response(cost_center_contacs)


# ManuelCL15/12/2021 (listar contactos frecuentes de un centro de costos para transacciones de polipay a terceros"
class ListFrecuentContactsPolipayToThirPerson(ListAPIView):

    def list(self, request, *args, **kwargs):
        cost_center = request.query_params['cost_center_id']

        cost_center_contacs = contactos.objects.filter(
            person_id=cost_center,
            tipo_contacto_id=2,
            is_active=True
        ).values(
            'id',
            'alias',
            'nombre',
            'cuenta',
            'email',
            'rfc_beneficiario',
            'banco'
        )
        return Response(cost_center_contacs)
