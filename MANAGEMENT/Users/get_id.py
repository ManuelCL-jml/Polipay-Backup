import json
from datetime import datetime

from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework import status

from apps.users.models import persona, cuenta, tarjeta

def get_id(campo="", valorStr="", valorInt=0):
    id  = ""

    if str(campo)   == "email":
        queryExiste = persona.objects.filter(email=valorStr).exists()

        if not queryExiste:
            result = {"status": "(get_id) email:\nCorreo no registrado."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        queryIdPersona  = persona.objects.filter(email=valorStr).values("id")
        if len(queryIdPersona) == 0 or queryIdPersona == False or queryIdPersona == None or queryIdPersona == "":
            result = {"status": "(get_id) email:\nSin registros."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        id = queryIdPersona[0]["id"]


    if str(campo) == "card":
        queryExiste = tarjeta.objects.filter(id=valorStr).exists()

        if not queryExiste:
            result = {"status": "(get_id) card:\nTarjeta no registrada."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        queryIdCuenta   = tarjeta.objects.filter(id=valorStr).values("id", "cuenta_id")
        if len(queryIdCuenta) == 0 or queryIdCuenta == False or queryIdCuenta == None or queryIdCuenta == "":
            result = {"status": "(get_id) card:\nSin registro de tarjeta."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        queryIdP        = cuenta.objects.filter(id=queryIdCuenta[0]["cuenta_id"]).values("id", "persona_cuenta_id")
        if len(queryIdP) == 0 or queryIdP == False or queryIdP == None or queryIdP == "":
            result = {"status": "(get_id) card:\nSin registro de cuenta."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        queryIdPersona = persona.objects.filter(id=queryIdP[0]["persona_cuenta_id"]).values("id")
        if len(queryIdPersona) == 0 or queryIdPersona == False or queryIdPersona == None or queryIdPersona == "":
            result = {"status": "(get_id) card:\nSin registros."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        id  = queryIdPersona[0]["id"]


    if str(campo)   == "account":
        queryExiste = cuenta.objects.filter(cuenta=valorStr).exists()

        if not queryExiste:
            result = {"status": "(get_id) account:\nCuenta no registrado."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        queryIdPersona  = cuenta.objects.filter(cuenta=valorStr).values("persona_cuenta_id")
        if len(queryIdPersona) == 0 or queryIdPersona == False or queryIdPersona == None or queryIdPersona == "":
            result = {"status": "(get_id) account:\nSin registros."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        id = queryIdPersona[0]["persona_cuenta_id"]


    if str(campo)   == "idAccount":
        queryExiste = cuenta.objects.filter(id=valorInt).exists()

        if not queryExiste:
            result = {"status": "(get_id) idAccount:\nCuenta no registrado."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        queryIdPersona  = cuenta.objects.filter(id=valorInt).values("persona_cuenta_id")
        if len(queryIdPersona) == 0 or queryIdPersona == False or queryIdPersona == None or queryIdPersona == "":
            result = {"status": "(get_id) idAccount:\nSin registros."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        id = queryIdPersona[0]["persona_cuenta_id"]


    return id