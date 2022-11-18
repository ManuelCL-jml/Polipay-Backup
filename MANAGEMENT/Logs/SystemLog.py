from datetime import datetime

from apps.users.models import persona, cuenta, tarjeta
from apps.logspolipay.models import log



def RegisterIt(_endpoint:str, _idPersona:int, _objJsonRequest:dict,  _objJsonResponse:dict):
    instanciaRegLog = log(
        creation_date=datetime.now(),
        url=_endpoint,
        persona_id=_idPersona,
        json_content=_objJsonRequest,
        response=_objJsonResponse
    )
    instanciaRegLog.save()

def existPerson(idPersona):
    query   = persona.objects.filter(id=idPersona).exists()
    if query:
        return idPersona
    else:
        return -1

def existEmail(_email):
    query   = persona.objects.filter(email=_email).exists()
    if query:
        query2   = persona.objects.filter(email=_email).values("id")
        return query2[0]["id"]
    else:
        return -1

def existIdAccount(idAccount):
    query   = cuenta.objects.filter(id=idAccount).exists()
    if query:
        query2  = cuenta.objects.filter(id=idAccount).values("persona_cuenta_id")
        return query2[0]["persona_cuenta_id"]
    else:
        return -1

def existIdCard(idCard):
    query   = tarjeta.objects.filter(id=idCard).exists()
    if query:
        query2  = tarjeta.objects.filter(id=idCard).values("cuenta_id")
        query3  = cuenta.objects.filter(id=query2[0]["cuenta_id"]).values("persona_cuenta_id")
        return query3[0]["persona_cuenta_id"]
    else:
        return -1

def existAccount(account):
    query   = cuenta.objects.filter(cuenta=account).exists()
    if query:
        query2  = cuenta.objects.filter(cuenta=account).values("persona_cuenta_id")
        return query2[0]["persona_cuenta_id"]
    else:
        return -1

def existCard(card):
    query   = tarjeta.objects.filter(tarjeta=card).exists()
    if query:
        query2  = tarjeta.objects.filter(tarjeta=card).values("cuenta_id")
        query3  = cuenta.objects.filter(id=query2[0]["cuenta_id"]).values("persona_cuenta_id")
        return query3[0]["persona_cuenta_id"]
    else:
        return -1

def RegisterSystemLog(idPersona=0, idCuenta=0, idTarjeta=0, email="", account="", card="", type=0, endpoint="", objJsonRequest={}, objJsonResponse={}):
    # Caso 1: Cuando proporcionan el id del usuario
    if type == 1:
        idPersona   = existPerson(idPersona)
        RegisterIt(endpoint, idPersona, objJsonRequest, objJsonResponse)

    # Caso 2: Cuando proporcionan el id de la cuenta y se debe recuperar el id del usuario
    if type == 2:
        idP = existIdAccount(idCuenta)
        RegisterIt(endpoint, idP, objJsonRequest, objJsonResponse)

    # Caso 3: Cuando proporcionan el id de la tarjeta y se debe recuperar el id del usuario
    if type == 3:
        idP = existIdCard(idTarjeta)
        RegisterIt(endpoint, idP, objJsonRequest, objJsonResponse)

    # Caso 4: Cuando proporcionan el correo del usuario y se debe recuperar el id del usuario
    if type == 4:
        idP = existEmail(email)
        RegisterIt(endpoint, idP, objJsonRequest, objJsonResponse)

    # Caso 5: Cuando proporcionan la cuenta del usuario y se debe recuperar el id del usuario
    if type == 5:
        idP = existAccount(account)
        RegisterIt(endpoint, idP, objJsonRequest, objJsonResponse)

    # Caso 6: Cuando proporcionan la tarjeta y se debe recuperar el id del usuario
    if type == 6:
        idP = existCard(card)
        RegisterIt(endpoint, idP, objJsonRequest, objJsonResponse)
