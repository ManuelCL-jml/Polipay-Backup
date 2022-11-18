from django.shortcuts import render

from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.response import Response

from apps.permision.permisions import BlocklistPermission
from polipaynewConfig.exceptions import *
from apps.contacts.api.movil.serializers.Contacts_serializer import *
from apps.contacts.api.movil.serializers.GroupContact_serializer import *
from apps.contacts.api.movil.serializers.Group_serializer import *
from apps.contacts.models import *
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser

class contacto(viewsets.GenericViewSet):
    queryset = contactos.objects.all()
    serializer_class = SerializerContactIn
    #permission_classes = (BlocklistPermission,)
    permission_classes = ()
    #permisos = ['can_create_contact_v2','can_edit_contact_v2','can_get_contact_v2']

    def create(self,request):
        pk_user = request.data["persona"]
        pk_tc = request.data["tipo_contacto"]
        instanceP = get_Object_Or_Error(persona, id=pk_user)
        instanceTC = get_Object_Or_Error(tipo_transferencia,id=pk_tc)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.createContact(serializer.validated_data,instanceP,instanceTC)
            return Response({"status":"contacto creado"},status=status.HTTP_200_OK)


    def list(self,request):
        try:
            pk_user = self.request.query_params['id']
            if pk_user:
                instance = get_Object_Or_Error(persona,pk=pk_user)
                serializer = SerializerContactsOutV2(instance)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response({"status":"Se esperaba una id de usuario"},status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)


    def delete(self,request):
        pk_contact = self.request.query_params['id']
        instace = get_Object_Or_Error(contactos,id=pk_contact)
        instace.delete()
        return Response({"status":"Contacto eliminado"},status=status.HTTP_200_OK)

    def put(self,request):
        pk_contact = self.request.query_params['id']
        instance = get_Object_Or_Error(contactos,id=pk_contact)
        serializer = SerializerEditContactIn(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance,serializer.validated_data)
            return Response({"status":"Contacto actualizado"},status=status.HTTP_200_OK)


class personaGrupoContacto(viewsets.GenericViewSet):
    permission_classes = ()

    def list(self,request):
        pk = self.request.query_params['id']
        type = self.request.query_params['type']
        if str(type) == "c":
            instance = get_Object_Or_Error(persona,pk=pk)
            serializer = SerializerPersonContactOut(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif str(type) == "g":
            instance = get_Object_Or_Error(persona, pk=pk)
            serializer = SerializerPersonGroupOut(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"status":"datos no especificados"},status=status.HTTP_400_BAD_REQUEST)

# -------- (ChrAvaBus Mar16.11.2021) v3 --------

class ListFrequentAccounts(viewsets.GenericViewSet):
    serializer_class    = None
    permission_classes  = [IsAuthenticated]
    #permission_classes = ()

    def list(self, request):
        pk              = ""
        queryResult     = ""
        arrayTmpResult  = []
        result          = {}

        pk              = self.request.query_params["id"]
        if pk == False or pk == None or pk == "":
            msg = LanguageRegisteredUser(0, "Fre001BE")
            result = {"status": msg}
            #result  = {"status":"Debes proporcionar un id."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        else:
            queryResult	= contactos.objects.filter(person_id=pk, is_favorite=1).values("id", "nombre", "cuenta", "banco",
                                                "alias", "tipo_contacto_id","tipo_contacto__nombre_tipo")
            if len(queryResult) == 0 or queryResult == False or queryResult == None or queryResult == "":
                result = {
                    "Contacts": []
                }
                return Response(result, status=status.HTTP_200_OK)
            else:
                for rows in queryResult:
                    rows["tipo_contacto"]   = rows["tipo_contacto__nombre_tipo"]
                    rows.pop("tipo_contacto__nombre_tipo")
                    arrayTmpResult.append(rows)

                    """
                    result  = {
                        "code":[200],
                        "status":"OK",
                        "detail":[
                            {
                                "data":"---",
                                "field":"---",
                                "message":"---"
                            }
                        ]
                    }
                    """

                result	= {
                    "Contacts":arrayTmpResult
                }

                return Response(result,status=status.HTTP_200_OK)



class CreateFrequentAccounts(viewsets.GenericViewSet):
    serializer_class    = SerializerCreateFrequentAccounts
    permission_classes  = [IsAuthenticated]
    #permission_classes = ()

    def create(self,request):
        pk_user     = request.data["person"]
        pk_tc       = request.data["tipo_contacto"]
        if request.data["banco"] == 0:
            request.data["banco"]   = 86
        instanceP   = get_Object_Or_Error(persona, id=pk_user)
        instanceTC  = get_Object_Or_Error(tipo_transferencia,id=pk_tc)
        serializer  = self.serializer_class(data=request.data)

        if serializer.is_valid(raise_exception=True):
            serializer.createFrequent(serializer.validated_data,instanceP,instanceTC)
            """
            result  = {
                "code":[200],
                "status":"OK",
                "detail":[
                    {
                        "data":"---",
                        "field":"---",
                        "message":"---"
                    }
                ]
            }
            """
            msg = LanguageRegisteredUser(request.data["person"], "Fre001")
            result = {"status": msg}
            #result	= {"status":"Frecuente creado."}
            return Response(result,status=status.HTTP_200_OK)



class UpdateFrequentAccounts(UpdateAPIView):
    serializer_class    = SerializerCreateFrequentAccounts
    permission_classes  = [IsAuthenticated]
    #permission_classes = ()

    def update(self,request):
        pk_tc       = request.data["tipo_contacto"]
        if request.data["banco"] == 0:
            request.data["banco"]   = 86
        pk_contact  = self.request.query_params['id']
        instance    = get_Object_Or_Error(contactos,id=pk_contact)
        instanceTC  = get_Object_Or_Error(tipo_transferencia,id=pk_tc)
        serializer  = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.updateFrequent(serializer.validated_data, instance, instanceTC)
            msg = LanguageRegisteredUser(request.data["person"], "Fre002")
            return Response({"status": msg},status=status.HTTP_200_OK)
            #return Response({"status":"Frecuente actualizado."},status=status.HTTP_200_OK)




class DestroyFrequentAccounts(DestroyAPIView):
    serializer_class    = None
    permission_classes  = [IsAuthenticated]
    #permission_classes = ()

    def destroy(self,request):
        pk  = self.request.query_params['id']

        if pk == False or pk == None or pk == "":
            msg = LanguageRegisteredUser(0, "Fre001BE")
            result = {"status": msg}
            #result  = {"status":"Debes proporcionar un id."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        else:
            instace = get_Object_Or_Error(contactos,id=pk)
            instace.delete()
            msg = LanguageRegisteredUser(pk, "Fre003")
            result = {"status": msg}
            #result  = {"status":"Frecuente eliminado."}
            return Response(result,status=status.HTTP_200_OK)



