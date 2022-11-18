import json

from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from rest_framework import status
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.response import Response

from apps.permision.permisions import BlocklistPermission
from polipaynewConfig.exceptions import *
from apps.notifications.api.movil.serializers.notifications_serializer import *
from apps.notifications.models import notification
from apps.transaction.models import transferencia
from apps.users.models import persona
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser


# -------- (ChrAvaBus Jue25.11.2021) v3 --------

class ListNotification(viewsets.GenericViewSet):
    serializer_class    = None
    permission_classes  = [IsAuthenticated]
    #permission_classes = ()

    def list(self, request):
        pk = ""
        queryExisteNotificacion = ""
        queryNotificacion = ""
        queryTransferencia = ""
        arrayTmpResult = []
        result = {}

        pk = self.request.query_params["id"]
        if pk == False or pk == None or pk == "":
            msg = LanguageRegisteredUser(pk, "Not001BE")
            result = {"status": msg}
            #result = {"status": "Debes proporcionar un id."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        else:
            queryExistePersona = persona.objects.filter(id=pk).exists()
            if not queryExistePersona:
                msg = LanguageRegisteredUser(pk, "Not002BE")
                result = {"status": msg}
                #result = {"status": "No existe Persona."}
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            else:
                queryNotificacion = notification.objects.filter(person_id=pk, is_active=1, notification_type_id=1).values().order_by("-id")
                if len(queryNotificacion) == 0 or queryNotificacion == False or queryNotificacion == None or queryNotificacion == "":
                    result = {"Notifications": []}
                    return Response(result, status=status.HTTP_200_OK)
                else:
                    for rows in queryNotificacion:
                        objJson = json.loads(rows["json_content"])
                        rows["json_content"] = objJson
                        arrayTmpResult.append(rows)

                    result = {
                        "Notifications": queryNotificacion
                    }

                    return Response(result, status=status.HTTP_200_OK)


class UpdateNotification(UpdateAPIView):
    serializer_class    = SerializerCreateNotification
    permission_classes  = [IsAuthenticated]
    #permission_classes = ()

    def update(self, request):
        pk  = self.request.query_params['id']
        request.data["id"]  = pk
        instance = get_Object_Or_Error(notification, id=pk)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.updateNotification(serializer.validated_data, instance)
            msg = LanguageRegisteredUser(request.data["person"], "Not009")
            return Response({"status": msg}, status=status.HTTP_200_OK)
            #return Response({"status": "Notificación eliminada."}, status=status.HTTP_200_OK)



class ActiveNotification(viewsets.GenericViewSet):
    # Devuelve las notificaciones que aun no se leen, esto se determina mientras el campo
    #   deactivation_date sea Null o 0000-00-00 00:00:00.000000 y is_active=true no se ha leido.
    #   si deactivation_date en diferente Null o 0000-00-00 00:00:00.000000 y is_active=false el usuario la elimino.
    serializer_class    = None
    permission_classes  = [IsAuthenticated]
    #permission_classes = ()

    def list(self, request):
        pk                  = ""
        queryExistePersona  = ""
        queryNumDeNotiAct   = ""
        result              = {}

        pk = self.request.query_params["id"]
        if pk == False or pk == None or pk == "":
            msg = LanguageRegisteredUser(pk, "BackEnd002")
            result = {"status": msg}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        queryExistePersona = persona.objects.filter(id=pk).exists()
        if not queryExistePersona:
            msg = LanguageRegisteredUser(pk, "BackEnd003")
            result = {"status": msg}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        queryNumDeNotiAct = notification.objects.filter(deactivation_date__isnull=True, person_id=pk, is_active=1, notification_type_id=1).values("id")
        if len(queryNumDeNotiAct) == 0 or queryNumDeNotiAct == False or queryNumDeNotiAct == None or queryNumDeNotiAct == "":
            result = {"Notifications":0}
            return Response(result, status=status.HTTP_200_OK)
        else:
            result = {"Notifications": len(queryNumDeNotiAct)}
            return Response(result, status=status.HTTP_200_OK)
