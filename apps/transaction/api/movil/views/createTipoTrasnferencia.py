from django.shortcuts import render
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status, pagination
from rest_framework.response import Response

from polipaynewConfig.exceptions import *
from apps.transaction.messages import *
from apps.transaction.models import *
from apps.contacts.serializer import serializerTipo_transferenciaIn, serializerTipo_transferenciaOut, \
    serializerTipo_transferenciaEdit


class tiposTransferencia(viewsets.GenericViewSet):
    serializer_class = serializerTipo_transferenciaIn
    queryset = transmasivaprod.objects.all()
    permission_classes = ()

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.create(serializer.validated_data)
            return Response({"status": "Tipo de trasferencia creado"}, status=status.HTTP_200_OK)

    def list(self, request):
        try:
            pk = self.request.query_params['id']
            if pk:
                queryset = tipo_transferencia.objects.all()
                lista = get_Object_Or_Error(queryset, pk=pk)
                serializer = serializerTipo_transferenciaOut(lista)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            queryset = tipo_transferencia.objects.all()
            serializer = serializerTipo_transferenciaOut(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        pk = self.request.query_params['id']
        queryset = tipo_transferencia.objects.all()
        instace = get_Object_Or_Error(queryset, id=pk)
        instace.delete()
        return Response({"status": "Tipo de trasferencia eliminado"}, status=status.HTTP_200_OK)

    def put(self, request):
        pk = self.request.query_params['id']
        instance = get_Object_Or_Error(tipo_transferencia, id=pk)
        serializer = serializerTipo_transferenciaEdit(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance, serializer.validated_data)
            return Response({"status": "Tipo de trasferencia actualizado"}, status=status.HTTP_200_OK)
