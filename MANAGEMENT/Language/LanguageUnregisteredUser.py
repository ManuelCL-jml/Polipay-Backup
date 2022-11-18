import json
from datetime import datetime

from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework import status

from apps.languages.models import Cat_languages, Language_Person


def LanguageUnregisteredUser(idLang : int, idMenssage : str):
    queryJsonMensajes   = ""
    msg                 = "..."

    # Confirmo id de idioma
    queryExisteIdioma   = Cat_languages.objects.filter(id=idLang).exists()

    if queryExisteIdioma:

        # Recupero JSON con los mensjaes del idioma correspondiente
        queryJsonMensajes   = Cat_languages.objects.filter(id=idLang).values("id", "json_content")
        if len(queryJsonMensajes) == 0 or queryJsonMensajes  == False or queryJsonMensajes  == None or queryJsonMensajes  == "":
            result = {"status": "IDIOMA\nUsuario_no_registrado\nSin contenido en JSON, idioma no registrado."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    else:

        # Recupero JSON con los mensjaes en español (default)
        queryJsonMensajes = Cat_languages.objects.filter(id=1).values("id", "json_content")
        if len(queryJsonMensajes) == 0 or queryJsonMensajes == False or queryJsonMensajes == None or queryJsonMensajes == "":
            result = {"status": "IDIOMA\nUsuario_no_registrado\nSin contenido en JSON, idioma no registrado."}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    # Selecciono el mensaje correspondiente
    banderaSalir    = False
    objJson = json.loads(queryJsonMensajes[0]["json_content"])
    for categoria in objJson["Categorias"]:
        if banderaSalir:
            break
        for mensaje in categoria["mensajes"]:
            if mensaje["codigo"] == idMenssage:
                msg = mensaje["mensaje"]
                banderaSalir    = True
                break

    if msg == "...":
        result = {"status": "IDIOMA\nUsuario_no_registrado\nMensaje no registrado."}
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    return msg