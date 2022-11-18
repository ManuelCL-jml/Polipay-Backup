from django.core.files import File

from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework import viewsets, status

from polipaynewConfig.exceptions import *
from apps.transaction.management import to_base64_file
from apps.users.management import create_pdf_data, EliminarDoc
from apps.users.api.web.serializers.documentos_serializer import *
from apps.users.models import documentos, persona


class Document(viewsets.GenericViewSet):
    permission_classes = ()
    serializer_class = SerializerUpDocumentIn
    serializer_class_d = SerializerDocumentsOut

    def create(self, request):
        instance = get_Object_orList_error(persona, pk=request.data["person_id"])

        serializer = self.serializer_class(data=request.data, context={"person_id": instance.id})
        serializer.is_valid(raise_exception=True)

        data = serializer.create(validated_data=serializer.data, id=instance.id)
        serializer = self.serializer_class_d(data)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


# class Document(viewsets.GenericViewSet):
#     serializer_class = SerializerDocumentIn
#     permission_classes = ()
#
#     def create(self, request):
#         pk_user = request.data["persona"]
#         if pk_user:
#             instance = get_Object_Or_Error(persona, id=pk_user)
#             serializer = self.serializer_class(data=request.data, context={"pk_user": pk_user})
#             if serializer.is_valid(raise_exception=True):
#                 create_pdf_data(request.data["file"])
#                 serializer.upload_file(instance)
#                 return Response({"status": "Documento creado"}, status=status.HTTP_201_CREATED)
#         else:
#             return Response({"status": "Se esperaba una id de usuario"}, status=status.HTTP_400_BAD_REQUEST)
#
#     def list(self, request):
#         try:
#             type = self.request.query_params["type"]
#             pk_user = self.request.query_params["id"]
#             if pk_user:
#                 instance = get_Object_Or_Error(persona, id=pk_user)
#                 if type == "T":
#                     serializer = SerializerDocumentsPersonAllOut(instance)
#                 elif type in "P,C,D":
#                     serializer = SerializerDocumentsPersonOut(instance, context={"type": type})
#                 else:
#                     return Response({"status": "Type no reconocido"}, status=status.HTTP_400_BAD_REQUEST)
#                 return Response(serializer.data, status=status.HTTP_200_OK)
#         except:
#             return Response({"status": "Id de persona no reconocida"}, status=status.HTTP_400_BAD_REQUEST)


def delete(self, request):
    pk_document = self.request.query_params["id"]
    instance = get_Object_Or_Error(documentos, id=pk_document)
    EliminarDoc(instance)
    return Response({"status": "Documentos eliminados"}, status=status.HTTP_200_OK)


class AuthorizeDocuments(viewsets.GenericViewSet):
    permission_classes = ()
    serializer_class = SerializerAuthorizeIn

    def put(self, request):
        pk_user = request.user.id
        print(pk_user)
        pk_document = self.request.query_params["id"]
        instance = get_Object_Or_Error(documentos, id=pk_document)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance, pk_user)
            message = "Has devuelto el documento con id: "
            if "C" in serializer.data.values():
                message = "Has autorizado el documento con id: "
            return Response({"status": message + pk_document}, status=status.HTTP_200_OK)

    def list(self, request):
        try:
            pk_user = self.request.query_params["id"]
            if pk_user:
                instance = get_Object_Or_Error(documentos, id=pk_user)
                serializer = SerializerDocumentsOut(instance)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            type_consult = self.request.query_params["type"]
            if type_consult == "admin":
                instance = documentos.objects.all()
                serializer = SerializerDocumentsOut(instance, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)

class DownloadPdf(RetrieveAPIView):
    permission_classes = ()
    serializer_class = DownloadPDF

    def retrieve(self, request, *args, **kwargs):
        id = self.request.query_params['id']
        document = documentos.objects.get(id = id )

        data ={
            'documento': document.documento
        }

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
