import pandas as pd

from django.shortcuts import render, get_object_or_404

from rest_framework import viewsets, status, pagination
from rest_framework.response import Response

from apps.transaction.api.movil.serializers.TransMasivapProd_serializer import *
from polipaynewConfig.exceptions import *


class transaccionesMasivasExcel(viewsets.GenericViewSet):
    serializer_class = serializerTransMasivaProdIn
    queryset = transmasivaprod.objects.all()
    permission_classes = ()

    def create(self, request):
        createExcelData(request.data['file'])
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.createMasive()
            return Response({"status": "listo"}, status=status.HTTP_200_OK)

    def list(self, request):
        try:
            pk = self.request.query_params['id']
            if pk:
                df = pd.read_excel('file.xlsx', sheet_name="Layout2021")
                df.fillna('', inplace=True)
                print(df)
                queryset = transmasivaprod.objects.all()
                lista = get_Object_Or_Error(queryset, pk=pk)
                serializer = serializerTransmasivaprodOut(lista)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            df = pd.read_excel('file.xlsx', sheet_name="Layout2021")
            df.fillna('', inplace=True)
            print(df)
            queryset = transmasivaprod.objects.all()
            serializer = serializerTransmasivaprodOut(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        pk = self.request.query_params['id']
        instace = get_Object_Or_Error(self.queryset, id=pk)
        instace.delete()
        return Response({"status": "Tipo de trasferencia eliminado"}, status=status.HTTP_200_OK)
