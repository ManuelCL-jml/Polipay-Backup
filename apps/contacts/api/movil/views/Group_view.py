from django.shortcuts import render

from rest_framework import viewsets, status
from rest_framework.response import Response

from polipaynewConfig.exceptions import *
from apps.contacts.api.movil.serializers.Group_serializer import *


class grupos(viewsets.GenericViewSet):
    queryset = grupo.objects.all()
    permission_classes = ()

    def create(self,request):
        serializer = serializerGrupoIn(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.createGrupo(serializer.validated_data)
            return Response({"status":"Grupo creado"},status=status.HTTP_200_OK)


    def list(self,request):
        try:
            pk = self.request.query_params['id']
            instance = get_Object_Or_Error(grupo,pk=pk)
            serializer = serializerGrupoOutV2(instance)
            return Response(serializer.data,status=status.HTTP_200_OK)
        except:
            queryset = grupo.objects.all()
            serializer = serializerGrupoOutV2(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self,request):
        pk = self.request.query_params['id']
        instance = get_Object_Or_Error(grupo,id=pk)
        instance.delete()
        return Response({"status":"Grupo eliminado"},status=status.HTTP_200_OK)

    def put(self,request):
        pk = self.request.query_params['id']
        instance = get_Object_Or_Error(grupo,id=pk)
        serializer = serializerEditGrupoIn(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance,serializer.validated_data)
            return Response({"status":"Grupo actualizado"},status=status.HTTP_200_OK)
