from django.shortcuts import render
from rest_framework import viewsets,status
from rest_framework import status
from .serializers import SerializerCodeEfectivaCRD, SerializerCodeEfectivaUpdate, SerializerTranTypeCRD, \
    SerializerTranTypeUpdate, SerializerTransmitterHaveTrantypeCDU, SerializerSolicita
from rest_framework.response import Response
from .models import *
from rest_framework import serializers
from polipaynewConfig.redefectiva import *

from datetime import date

# Create your views here.

"""
    CRUD para los codigos de red efectiva
"""


class CRUDCodeEfectiva(viewsets.GenericViewSet):
    serializer_class = SerializerCodeEfectivaCRD
    queryset = ()
    permission_classes = ()

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.create(serializer.validated_data)
            message_request_succesfull = {
                "code": [200],
                "status": "OK",
                "detail": [
                    {
                        "data": "",
                        "field": "",
                        "message": "TranType succesfully created",
                    }
                ]
            }
            return Response(message_request_succesfull, status=status.HTTP_201_CREATED)

    def list(self, request):
        queryset = CodeEfectiva.objects.all()
        serializer = SerializerCodeEfectivaCRD(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        try:
            instance_code_efectiva = CodeEfectiva.objects.get(id=request.data["id"])
        except Exception as e:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["id"],
                        "field": "id",
                        "message": "Code Efectiva not found",
                    }
                ]
            }
            raise serializers.ValidationError(message_not_found)
        serializer = SerializerCodeEfectivaUpdate(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance_code_efectiva)
            message_updated = {
                "code": [200],
                "status": "OK",
                "detail": [
                    {
                        "data": "",
                        "field": "",
                        "message": "Code Efectiva updated",
                    }
                ]
            }
            return Response(message_updated, status=status.HTTP_200_OK)

    def delete(self, request):
        try:
            CodeEfectiva.objects.get(id=request.data["id"]).delete()
        except Exception as e:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["id"],
                        "field": "id",
                        "message": "Code Efectiva not found",
                    }
                ]
            }
            raise serializers.ValidationError(message_not_found)
        message_deleted_successfully = {
            "code": [200],
            "status": "Deleted",
            "detail": [
                {
                    "data": "",
                    "field": "",
                    "message": "Code Efectiva deleted",
                }
            ]
        }
        return Response(message_deleted_successfully, status=status.HTTP_200_OK)


"""
    CRUD para los los tipos de transacciones(trantypes)
"""


class CRUDTranType(viewsets.GenericViewSet):
    serializer_class = SerializerTranTypeCRD
    queryset = ()
    permission_classes = ()

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.create(serializer.validated_data)
            message_request_succesfull = {
                "code": [200],
                "status": "OK",
                "detail": [
                    {
                        "data": "",
                        "field": "",
                        "message": "TranType succesfully created",
                    }
                ]
            }
            return Response(message_request_succesfull, status=status.HTTP_201_CREATED)

    def list(self, request):
        queryset = TranTypes.objects.all()
        serializer = SerializerTranTypeCRD(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        try:
            instance_trantype = TranTypes.objects.get(id=request.data["id"])
        except Exception as e:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["id"],
                        "field": "id",
                        "message": "TranType not found",
                    }
                ]
            }
            raise serializers.ValidationError(message_not_found)
        serializer = SerializerTranTypeUpdate(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance_trantype)
            message_updated = {
                "code": [200],
                "status": "OK",
                "detail": [
                    {
                        "data": "",
                        "field": "",
                        "message": "TranType updated",
                    }
                ]
            }
            return Response(message_updated, status=status.HTTP_200_OK)

    def delete(self, request):
        try:
            TranTypes.objects.get(id=request.data["id"]).delete()
        except Exception as e:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["id"],
                        "field": "id",
                        "message": "TranType not found",
                    }
                ]
            }
            raise serializers.ValidationError(message_not_found)
        message_deleted_successfully = {
            "code": [200],
            "status": "Deleted",
            "detail": [
                {
                    "data": "",
                    "field": "",
                    "message": "TranType deleted",
                }
            ]
        }
        return Response(message_deleted_successfully, status=status.HTTP_200_OK)


"""
    CRUD para los asignar los trantypes a los emissores (transmitterhavetrantypes)
"""


class CRUDTransmitterHaveTranType(viewsets.GenericViewSet):
    serializer_class = SerializerTransmitterHaveTrantypeCDU
    queryset = ()
    permission_classes = ()

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.create(serializer.validated_data)
            message_request_succesfull = {
                "code": [200],
                "status": "OK",
                "detail": [
                    {
                        "data": "",
                        "field": "",
                        "message": "TransmitterHaveTrantype succesfully created",
                    }
                ]
            }
            return Response(message_request_succesfull, status=status.HTTP_201_CREATED)

    def put(self, request):
        try:
            instance_TransmitterHaveTypes = TransmitterHaveTypes.objects.get(id=request.data["id"])
        except Exception as e:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["id"],
                        "field": "id",
                        "message": "TransmitterHaveTrantype not found",
                    }
                ]
            }
            raise serializers.ValidationError(message_not_found)
        serializer = SerializerTransmitterHaveTrantypeCDU(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance_TransmitterHaveTypes)
            message_updated = {
                "code": [200],
                "status": "OK",
                "detail": [
                    {
                        "data": "",
                        "field": "",
                        "message": "TransmitterHaveTypes updated",
                    }
                ]
            }
            return Response(message_updated, status=status.HTTP_200_OK)

    def delete(self, request):
        try:
            TransmitterHaveTypes.objects.get(id=request.data["id"]).delete()
        except Exception as e:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["id"],
                        "field": "id",
                        "message": "TransmitterHaveTypes not found",
                    }
                ]
            }
            raise serializers.ValidationError(message_not_found)
        message_deleted_successfully = {
            "code": [200],
            "status": "Deleted",
            "detail": [
                {
                    "data": "",
                    "field": "",
                    "message": "TransmitterHaveTypes deleted",
                }
            ]
        }
        return Response(message_deleted_successfully, status=status.HTTP_200_OK)


class TestConnectionAPISOAP(viewsets.GenericViewSet):
    serializer_class = SerializerSolicita
    queryset = ()
    permission_classes = ()

    def list(self, request):
        response = oEcho()
        return Response(response, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            response = serializer.create(serializer.validated_data)
            return Response(response, status=status.HTTP_200_OK)

    """def create(self, request):
        test_matrix()
        return Response({"Todas las pruebas ejecutadas"}, status=status.HTTP_200_OK)"""


"""
    Vista para el demonio que crea el archivo de conciliacion
"""


class DemonConcilationFile(viewsets.GenericViewSet):
    serializer_class = ()
    queryset = ()
    permission_classes = ()

    def list(self, request):
        today = date.today()
        string_date = str(today).split("-")
        datetime = string_date[2] + string_date[1] + string_date[0]  # Ejemplo: 28032022
        NIdentificador = "00002"
        #Query con las transacciones a red efectiva
        querys = LogEfectiva.objects.filter(payment_date__year=today.year, payment_date__month=today.month,
                                       payment_date__day=today.day)
        #Query con el total de monto
        sum_monto = LogEfectiva.objects.raw('SELECT id, SUM(amount) as total FROM services_pay_logefectiva where date(payment_date)= date(now())')[0]
        #TODO: query con el total de comision
        sum_comision = LogEfectiva.objects.raw('SELECT id, SUM(commission) as total FROM services_pay_logefectiva where date(payment_date)= date(now())')[0]
        #TODO: query con el total de cargos
        f = open("REV3_" + datetime + "_F2_" + NIdentificador + ".txt", "w") #TODO: actualizar el numero idenfiticador justificado!!
        f.write("H2|" + NIdentificador + "|" + datetime + "|" + str(len(querys)) + "|" + str(sum_monto.total) + "|" + str(sum_comision.total) + "|") #TODO: actualizar el numero idenfiticador justificado!!
        #TODO: agregar los registros con un loop de querys
        f.close()

        return Response({"Archivo de conciliacion creado"}, status=status.HTTP_200_OK)