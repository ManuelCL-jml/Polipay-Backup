from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status
from apps.services_pay.api.mobile.serializers.category_serializer import *
from apps.services_pay.models import *


class CategoryCrud(GenericViewSet):
    serializer_class = SerializerCategoryIn

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({"status": [
                {
                    "code": 201,
                    "status": "SUCCESS",
                    "field": "",
                    "data": "",
                    "message": "Categoria creada correctamente"
                }]}, status=status.HTTP_200_OK)

    def list(self, request):
        query = Category.objects.all()
        serializer = SerializerCategoryOut(query, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        instance = Category.objects.get(id=pk)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance, None)
            return Response({"status": [
                {
                    "code": 200,
                    "status": "SUCCESS",
                    "field": "",
                    "data": "",
                    "message": "Categoria actualizada correctamente"
                }]}, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        Category.objects.get(id=pk).delete()
        return Response({"status": [
            {
                "code": 200,
                "status": "SUCCESS",
                "field": "",
                "data": "",
                "message": "Categoria eliminada correctamente"
            }]}, status=status.HTTP_200_OK)


class CategoryCreateReference(GenericViewSet):
    serializer_class = SerializerReferenceIn

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({"status": [
                {
                    "code": 201,
                    "status": "SUCCESS",
                    "field": "",
                    "data": "",
                    "message": "Refrencia creada correctamente"
                }]}, status=status.HTTP_200_OK)
