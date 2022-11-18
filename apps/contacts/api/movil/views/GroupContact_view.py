from django.shortcuts import render

from rest_framework import viewsets, status
from rest_framework.response import Response

from apps.contacts.api.movil.serializers.GroupContact_serializer import *
from apps.contacts.models import *
from polipaynewConfig.exceptions import *


class grupoContactos(viewsets.GenericViewSet):
    queryset = grupoContacto.objects.all()
    serializer_class = serializerGrupoContactoIn
    permission_classes = ()

    def create(self,request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.create(serializer.validated_data)
            return Response({"status":"Grupo contacto creado"},status=status.HTTP_200_OK)

    def list(self,request):
        pk = self.request.query_params['id']
        instance = get_Object_Or_Error(persona,pk=pk)
        serializer = serializerGrupoContactoOut(instance)
        return Response(serializer.data,status=status.HTTP_200_OK)


    def delete(self,request):
        pk = self.request.query_params['id']
        instance = get_Object_Or_Error(grupoContacto,id=pk)
        instance.delete()
        return Response({"status":"Grupo contacto eliminado"},status=status.HTTP_200_OK)