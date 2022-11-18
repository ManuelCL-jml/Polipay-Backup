# -*- coding: utf-8 -*-
import codecs
import json
from datetime import datetime

from django.http import HttpResponse

from rest_framework import status
from rest_framework.response import Response

from apps.users.models import persona, cuenta, tarjeta
from apps.notifications.models import notification
from apps.transaction.models import transferencia
from MANAGEMENT.notifications.movil.push import pushNotifyAppUser
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from MANAGEMENT.Users.get_id import get_id

def sendNotify(idPersona=0, idCuenta=0, tituloNoti="Alerta PoliPay Wallet", msgNoti="...", tituloData="Alerta Polipay", msgData="...", detail="...", numDeNotiSinLeer=0):
    if idPersona != 0:
        pk_persona = idPersona
        queryExistePersona = persona.objects.filter(id=pk_persona).exists()
        if not queryExistePersona:
            msg = LanguageRegisteredUser(pk_persona, "Not008BE")
            return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
            #return Response({"status": "Usuario no existe o no pertenece\na Polipay, favor de verificar los datos."},
            #                status=status.HTTP_400_BAD_REQUEST)

        queryTokenDevice    = persona.objects.filter(id=pk_persona).values("token_device")
        if len(queryTokenDevice) == 0 or queryTokenDevice == None or queryTokenDevice == "":
            msg = LanguageRegisteredUser(pk_persona, "Not015BE")
            return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
            #return Response({"status": "Error, Usuario sin Token Device."},
            #                status=status.HTTP_400_BAD_REQUEST)

        tokenDevice = queryTokenDevice[0]["token_device"]

        pushNotifyAppUser(pk_persona, tituloNoti, msgNoti, tituloData, msgData, tokenDevice, "general", detail, numDeNotiSinLeer)

    if idCuenta != 0:
        pass


def getMontoActualCuentaTarjeta(account="", card=0):
    queryMontoActual    = None
    # Cuenta
    if account != "":
        queryMontoActual    = cuenta.objects.filter(cuenta=account).values("monto")
        if len(queryMontoActual) == 0 or queryMontoActual == None or queryMontoActual == "":
            idP = get_id(campo="account", valorStr=account)
            msg = LanguageRegisteredUser(idP, "Not013BE")
            return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
            #return Response({"status": "Problema al recuperar monto de Cuenta."},
            #                status=status.HTTP_400_BAD_REQUEST)

    # Tarjeta
    if card != 0:
        queryMontoActual    = tarjeta.objects.filter(tarjeta=card).values("monto")

        if len(queryMontoActual) == 0 or queryMontoActual == None or queryMontoActual == "":
            idP = get_id(campo="card", valorStr=card)
            msg = LanguageRegisteredUser(idP, "Not014BE")
            return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
            #return Response({"status": "Problema al recuperar monto de Tarjeta."},
            #                status=status.HTTP_400_BAD_REQUEST)

    return queryMontoActual[0]["monto"]


def getNumeroDeNotiSinLeer(idPersona):
    numDeNoti   = 0
    queryNumDeNotiAct = notification.objects.filter(deactivation_date__isnull=True, person_id=idPersona, is_active=1).values("id")
    if len(queryNumDeNotiAct) >= 1 or queryNumDeNotiAct != False or queryNumDeNotiAct != None or queryNumDeNotiAct != "":
        numDeNoti   = len(queryNumDeNotiAct)

    return numDeNoti


def hasTokenDevice(idPersona):
    tieneTokenDevice        = False
    queryTieneTokenDevice   = persona.objects.filter(id=idPersona).values("id", "token_device")
    tokenDevice             = queryTieneTokenDevice[0]["token_device"]
    if len(str(tokenDevice)) == 163:
        tieneTokenDevice    = True
    return tieneTokenDevice


# Se ejecuta desde el portal web la Banca
def notifyAppUserFromWeb(objJson : dict, opcion : int):
    # Resgitar y envia una notificación al smartphone del usuario de la app (wallet) mediante FireBase.
    #   Esta función es para cuando el usuario de la wallet realiza/recibe una dispersión/transferencia
    #   opcion = 1 ---> Polipay a Polipay (LIQUIDADA)
    #       Escenario 1: Cuando es Polipay a Polipay y se le notifica al emisor y receptor, en este función y caso,
    #                   unciamente se le notifica al receptor.
    #   opcion = 2 ---> Polipay a Terceros (LIQUIDADA, DEVUELTA)
    #       Escenario 2: Cuando es Polipay a Tercero y se le notifica al emisor, en el caso de que se liquide o devuelva.
    #   opcion = 3 ---> Recibida (LIQUIDADA)
    #       Escenario 3: Cuando se recibe una trasnferencia de terceros o solicitud de saldo y se le notifica al receptor.
    #   opcion = 4 ---> Dispersión (Recibida)
    #       Escenario 4: Cuando Tu centro de costos / cuenta eje te dispersa a tu cuenta polipay, ej: Pago de Nomina.


    data_jsonContent    = {}
    data_tipoMovimiento = objJson["tipo_pago"]
    data_status         = objJson["status_trans"]
    data_monto          = objJson["monto"]
    data_nombreEmisor   = objJson["nombre_emisor"]
    data_nombreBene     = objJson["nombre_beneficiario"]
    data_referenciaNum  = objJson["referencia_numerica"]
    data_idDeCuenta     = objJson["cuentatransferencia"]
    data_idDeTransf     = objJson["id_transferencia"]

    # valido id cuenta
    queryExisteCuenta   = cuenta.objects.filter(id=data_idDeCuenta).exists()
    if not queryExisteCuenta:
        idP = get_id(campo="idAccount", valorInt=data_idDeCuenta)
        msg = LanguageRegisteredUser(idP, "Not007BE")
        return Response({"status": msg},status=status.HTTP_400_BAD_REQUEST)
        #return Response({"status": "La cuenta no existe o no pertenece\na Polipay, favor de verificar los datos."},
        #                status=status.HTTP_400_BAD_REQUEST)

    # recupero id de persona
    queryIdPersona  = cuenta.objects.filter(id=data_idDeCuenta).values("persona_cuenta_id")
    if len(queryIdPersona) == 0 or queryIdPersona == None or queryIdPersona == "":
        idP = get_id(campo="idAccount", valorInt=data_idDeCuenta)
        msg = LanguageRegisteredUser(idP, "Not008BE")
        return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
        #return Response({"status": "Usuario no existe o no pertenece\na Polipay, favor de verificar los datos."},
        #                status=status.HTTP_400_BAD_REQUEST)

    pk_persona          = queryIdPersona[0]["persona_cuenta_id"]
    queryExistePersona  = persona.objects.filter(id=pk_persona).exists()
    if not queryExistePersona:
        msg = LanguageRegisteredUser(pk_persona, "Not002BE")
        return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
        #return Response({"status": "Usuario no existe o no pertenece\na Polipay, favor de verificar los datos."},
        #                status=status.HTTP_400_BAD_REQUEST)

    # construyo json_content
    tmpIdioma_titulo    = ""
    tmpIdioma_cuerpo    = ""
    # Caso especial: Polipay a Polipay y se le notifica unicamente al beneficiario. (Escenario 1)
    if opcion == 1:
        msg = LanguageRegisteredUser(pk_persona, "Not002")
        data_jsonContent["titulo"]  = msg
        tmpIdioma_titulo            = msg
        msg = LanguageRegisteredUser(pk_persona, "Not004")
        msg = msg.replace("<nombreEmisor>", str(data_nombreEmisor))
        msg = msg.replace("<monto>", str(data_monto))
        data_jsonContent["cuerpo"]  = msg
        tmpIdioma_cuerpo            = msg

        #data_jsonContent["titulo"] = "Transferencia Recibida"
        #data_jsonContent["cuerpo"]  = str(data_nombreEmisor) + " te envió una transferencia de $" + str(data_monto) + \
        #                             ", movimiento Polipay a Polipay."

    # Escenario 2 : Cambio de estados
    if opcion == 2:
        # (1) LIQUIDADA
        if str(data_status) == "1":
            msg = LanguageRegisteredUser(pk_persona, "Not001")
            data_jsonContent["titulo"]  = msg
            tmpIdioma_titulo            = msg
            msg = LanguageRegisteredUser(pk_persona, "Not007")
            msg = msg.replace("<nombreBeneficiario>", str(data_nombreEmisor))
            msg = msg.replace("<monto>", str(data_monto))
            data_jsonContent["cuerpo"]  = msg
            tmpIdioma_cuerpo            = msg

            #data_jsonContent["titulo"] = "Transferencia Enviada"
            #data_jsonContent["cuerpo"] = "La transferencia de $" + str(data_monto) + " a " + \
            #                             str(data_nombreBene) + " se envió correctamente."

        # (7) DEVUELTO
        if str(data_status) == "7":
            msg = LanguageRegisteredUser(pk_persona, "Not003")
            data_jsonContent["titulo"]  = msg
            tmpIdioma_titulo            = msg
            msg = LanguageRegisteredUser(pk_persona, "Not008")
            msg = msg.replace("<nombreBeneficiario>", str(data_nombreEmisor))
            msg = msg.replace("<monto>", str(data_monto))
            data_jsonContent["cuerpo"]  = msg
            tmpIdioma_cuerpo            = msg

            #data_jsonContent["titulo"] = "Transferencia Retornada"
            #data_jsonContent["cuerpo"] = "La transferencia de $" + str(data_monto) + " a " + \
            #                             str(data_nombreBene) + " no pudo ser procesada."

    # Escenario 3 : Tercero a Polipay
    if opcion == 3:
        msg = LanguageRegisteredUser(pk_persona, "Not002")
        data_jsonContent["titulo"]  = msg
        tmpIdioma_titulo            = msg
        msg = LanguageRegisteredUser(pk_persona, "Not005")
        msg = msg.replace("<nombreEmisor>", str(data_nombreEmisor))
        msg = msg.replace("<monto>", str(data_monto))
        data_jsonContent["cuerpo"]  = msg
        tmpIdioma_cuerpo            = msg

        #data_jsonContent["titulo"] = "Transferencia Recibida"
        #data_jsonContent["cuerpo"] = str(data_nombreEmisor) + " te envió una transferencia de $" + str(data_monto) + \
        #                             ", movimiento interbancario."

    # Escenario 4 : Dispersión (centroDeCostos a polipay)
    if opcion == 4:
        msg = LanguageRegisteredUser(pk_persona, "Not002")
        data_jsonContent["titulo"]  = msg
        tmpIdioma_titulo            = msg
        msg = LanguageRegisteredUser(pk_persona, "Not004")
        msg = msg.replace("<nombreEmisor>", str(data_nombreEmisor))
        msg = msg.replace("<monto>", str(data_monto))
        data_jsonContent["cuerpo"]  = msg
        tmpIdioma_cuerpo            = msg

        #data_jsonContent["titulo"] = "Transferencia Recibida"
        #data_jsonContent["cuerpo"] = str(data_nombreEmisor) + " te envió una transferencia de $" + str(data_monto) + \
        #                            ", movimiento Polipay a Polipay."

    # detalle de trasnferencia
    objJsonDetalle = {}
    queryTransferencia = transferencia.objects.filter(id=data_idDeTransf).values("id",
        "tipo_pago_id", "tipo_pago__nombre_tipo", "concepto_pago", "referencia_numerica", "fecha_creacion", "monto",
        "nombre_emisor", "cuenta_emisor", "transmitter_bank__institucion",
        "nombre_beneficiario", "cta_beneficiario", "receiving_bank__institucion",
        "status_trans_id", "status_trans__nombre")
    if len(
        queryTransferencia) == 0 or queryTransferencia == False or queryTransferencia == None or queryTransferencia == "":
        objJsonDetalle["detalle"] = {}
    else:
        for rowTransferencia in queryTransferencia:
            rowTransferencia["tipo_pago"] = rowTransferencia.pop("tipo_pago__nombre_tipo")
            rowTransferencia["banco_emisor"] = rowTransferencia.pop("transmitter_bank__institucion")
            rowTransferencia["banco_beneficiario"] = rowTransferencia.pop("receiving_bank__institucion")
            rowTransferencia["status"] = rowTransferencia.pop("status_trans__nombre")
            rowTransferencia["fecha_creacion"] = str(rowTransferencia["fecha_creacion"])
            objJsonDetalle = rowTransferencia

    data_jsonContent["detalle"]    = objJsonDetalle

    # registro notificación
    instanciaNotificacion   = notification(
        creation_date=datetime.now(),
        is_active=True,
        json_content=json.dumps(data_jsonContent),
        notification_type_id=1,
        person_id=pk_persona,
        transaction_id=data_idDeTransf
    )
    instanciaNotificacion.save()

    numDeNotiSinLeer_ = getNumeroDeNotiSinLeer(pk_persona)

    # recupero id de la notificación
    queryIdNotificacion = notification.objects.filter(person_id=pk_persona, is_active=True).values("id").last()
    if len(queryIdNotificacion) == 0 or queryIdNotificacion == None or queryIdNotificacion == "":
        msg = LanguageRegisteredUser(pk_persona, "Not009BE")
        return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
        #return Response({"status": "Problema al recuperar ID de Notificación."},
        #                status=status.HTTP_400_BAD_REQUEST)

    # asigno id de notificación
    objJsonDetalle["id_notificacion"] = queryIdNotificacion["id"]

    # Escenario 1
    if opcion == 1:
        # recupera el monto actual
        montoActual                     = getMontoActualCuentaTarjeta(account=queryTransferencia[0]["cta_beneficiario"])
        objJsonDetalle["monto_actual"]  = montoActual

        # notifica al beneficiario
        if hasTokenDevice(idPersona=pk_persona):
            sendNotify(idPersona=pk_persona, tituloNoti=tmpIdioma_titulo, msgNoti=tmpIdioma_cuerpo,
                tituloData=tmpIdioma_titulo, msgData=tmpIdioma_cuerpo, detail=json.dumps(objJsonDetalle), numDeNotiSinLeer=numDeNotiSinLeer_)

    # Escenario 2
    if opcion == 2:
        # recupera el monto actual
        montoActual = getMontoActualCuentaTarjeta(account=queryTransferencia[0]["cuenta_emisor"])
        objJsonDetalle["monto_actual"] = montoActual

        if str(data_status) == "1":
            # notifica al emisor (LIQUIDADA)
            if hasTokenDevice(idPersona=pk_persona):
                sendNotify(idPersona=pk_persona, tituloNoti=tmpIdioma_titulo, msgNoti=tmpIdioma_cuerpo,
                    tituloData=tmpIdioma_titulo, msgData=tmpIdioma_cuerpo, detail=json.dumps(objJsonDetalle), numDeNotiSinLeer=numDeNotiSinLeer_)

        if str(data_status) == "7":
            # notifica al emisor (DEVUELTA)
            if hasTokenDevice(idPersona=pk_persona):
                sendNotify(idPersona=pk_persona, tituloNoti=tmpIdioma_titulo, msgNoti=tmpIdioma_cuerpo,
                    tituloData=tmpIdioma_titulo, msgData=tmpIdioma_cuerpo, detail=json.dumps(objJsonDetalle), numDeNotiSinLeer=numDeNotiSinLeer_)

    # Escenario 3 y 4
    if opcion == 3 or opcion == 4:
        # recupera el monto actual
        montoActual = getMontoActualCuentaTarjeta(account=queryTransferencia[0]["cta_beneficiario"])
        objJsonDetalle["monto_actual"] = montoActual

        # notifica al beneficiario (LIQUIDADA o RECIBIDA)
        if hasTokenDevice(idPersona=pk_persona):
            sendNotify(idPersona=pk_persona, tituloNoti=tmpIdioma_titulo, msgNoti=tmpIdioma_cuerpo,
                tituloData=tmpIdioma_titulo, msgData=tmpIdioma_cuerpo, detail=json.dumps(objJsonDetalle), numDeNotiSinLeer=numDeNotiSinLeer_)




# Se ejecuta desde la app Wallet
def notifyAppUser(objJson : dict, opcion : int):
    # Resgitar y envia una notificación al smartphone del usuario de la app (wallet) mediante FireBase.
    #   Esta función es para cuando el usuario de la wallet realiza/recibe una dispersión/transferencia
    #   opcion = 1 ---> Polipay a Polipay
    #   opcion = 2 ---> Polipay a Terceros
    #   opcion = 3 ---> Interno (De cuenta polipay a tarjeta polipay)



    data_jsonContent    = {}
    objJsonBeneficiario = {}
    data_tipoMovimiento = objJson["tipo_pago"]
    data_status         = objJson["status_trans"]
    data_monto          = objJson["monto"]
    data_nombreEmisor   = objJson["nombre_emisor"]
    data_nombreBene     = objJson["nombre_beneficiario"]
    data_referenciaNum  = objJson["referencia_numerica"]
    data_idDeCuenta     = objJson["cuentatransferencia"]


    # valido id cuenta
    queryExisteCuenta   = cuenta.objects.filter(id=data_idDeCuenta).exists()
    if not queryExisteCuenta:
        idP = get_id(campo="idAccount", valorInt=data_idDeCuenta)
        msg = LanguageRegisteredUser(idP, "Not007BE")
        return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
        #return Response({"status": "La cuenta no existe o no pertenece\na Polipay, favor de verificar los datos."},
        #                status=status.HTTP_400_BAD_REQUEST)

    # recupero id de persona
    queryIdPersona  = cuenta.objects.filter(id=data_idDeCuenta).values("persona_cuenta_id")
    if len(queryIdPersona) == 0 or queryIdPersona == None or queryIdPersona == "":
        idP = get_id(campo="idAccount", valorInt=data_idDeCuenta)
        msg = LanguageRegisteredUser(idP, "Not008BE")
        return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
        #return Response({"status": "Usuario no existe o no pertenece\na Polipay, favor de verificar los datos."},
        #                status=status.HTTP_400_BAD_REQUEST)

    pk_persona          = queryIdPersona[0]["persona_cuenta_id"]
    queryExistePersona  = persona.objects.filter(id=pk_persona).exists()
    if not queryExistePersona:
        msg = LanguageRegisteredUser(pk_persona, "Not002BE")
        return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
        #return Response({"status": "Usuario no existe o no pertenece\na Polipay, favor de verificar los datos."},
        #                status=status.HTTP_400_BAD_REQUEST)

    # construyo json_content
    tmpIdioma_titulo    = ""
    tmpIdioma_cuerpo    = ""

    msg = LanguageRegisteredUser(pk_persona, "Not001")
    data_jsonContent["titulo"]  = msg
    tmpIdioma_titulo            = msg
    #data_jsonContent["titulo"]  = "Transferencia Enviada"

    # Polipay a Polipay
    if str(data_status) == "1":
        msg = LanguageRegisteredUser(pk_persona, "Not007")
        msg = msg.replace("<nombreBeneficiario>", str(data_nombreEmisor))
        msg = msg.replace("<monto>", str(data_monto))
        data_jsonContent["cuerpo"]  = msg
        tmpIdioma_cuerpo            = msg

        #data_jsonContent["cuerpo"]  = "La transferencia de $" + str(data_monto) + " a " + \
        #                              str(data_nombreBene) + " se envió correctamente."

    # Polipay a Tercero
    if str(data_status) == "3":
        msg = LanguageRegisteredUser(pk_persona, "Not006")
        msg = msg.replace("<nombreBeneficiario>", str(data_nombreEmisor))
        msg = msg.replace("<monto>", str(data_monto))
        data_jsonContent["cuerpo"]  = msg
        tmpIdioma_cuerpo            = msg

        #data_jsonContent["cuerpo"] = "La transferencia de $" + str(data_monto) + " a " + \
        #                             str(data_nombreBene) + " está siendo procesada."

    queryUltimoMovimiento = transferencia.objects.filter(cuentatransferencia=data_idDeCuenta,
                                                         referencia_numerica=data_referenciaNum).values("id").last()
    if len(queryUltimoMovimiento) == 0 or queryUltimoMovimiento == None or queryUltimoMovimiento == "":
        msg = LanguageRegisteredUser(pk_persona, "Not010BE")
        return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
        #return Response({"status": "Error al recuperar ultima trasnferencia."},
        #                status=status.HTTP_400_BAD_REQUEST)

    # detalle de trasnferencia
    objJsonDetalle = {}
    queryTransferencia = transferencia.objects.filter(id=queryUltimoMovimiento["id"]).values("id",
        "tipo_pago_id", "tipo_pago__nombre_tipo", "concepto_pago", "referencia_numerica", "fecha_creacion", "monto",
        "nombre_emisor", "cuenta_emisor", "transmitter_bank__institucion",
        "nombre_beneficiario", "cta_beneficiario", "receiving_bank__institucion",
        "status_trans_id", "status_trans__nombre")
    if len(
        queryTransferencia) == 0 or queryTransferencia == False or queryTransferencia == None or queryTransferencia == "":
        objJsonDetalle["detalle"] = {}
    else:
        for rowTransferencia in queryTransferencia:
            rowTransferencia["tipo_pago"] = rowTransferencia.pop("tipo_pago__nombre_tipo")
            rowTransferencia["banco_emisor"] = rowTransferencia.pop("transmitter_bank__institucion")
            rowTransferencia["banco_beneficiario"] = rowTransferencia.pop("receiving_bank__institucion")
            rowTransferencia["status"] = rowTransferencia.pop("status_trans__nombre")
            rowTransferencia["fecha_creacion"] = str(rowTransferencia["fecha_creacion"])
            objJsonDetalle = rowTransferencia

    data_jsonContent["detalle"]    = objJsonDetalle

    # registro notificación
    fecha   = datetime.now()
    instanciaNotificacion   = notification(
        creation_date=fecha,
        is_active=True,
        json_content=json.dumps(data_jsonContent),
        notification_type_id=1,
        person_id=pk_persona,
        transaction_id=queryTransferencia[0]["id"]
    )
    instanciaNotificacion.save()

    numDeNotiSinLeer_ = getNumeroDeNotiSinLeer(pk_persona)

    # recupero id de la notificación
    queryIdNotificacion = notification.objects.filter(person_id=pk_persona, is_active=True).values("id").last()
    if len(queryIdNotificacion) == 0 or queryIdNotificacion == None or queryIdNotificacion == "":
        msg = LanguageRegisteredUser(pk_persona, "Not009BE")
        return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
        #return Response({"status": "Problema al recuperar ID de Notificación."},
        #                status=status.HTTP_400_BAD_REQUEST)

    # asigno id de notificación
    objJsonDetalle["id_notificacion"] = queryIdNotificacion["id"]

    # recupera el monto actual
    montoActual = getMontoActualCuentaTarjeta(account=queryTransferencia[0]["cuenta_emisor"])
    objJsonDetalle["monto_actual"] = montoActual

    objJsonBeneficiario["monto"] = data_monto
    objJsonBeneficiario["tipo_pago"] = "5"
    objJsonBeneficiario["referencia_numerica"] = data_referenciaNum
    objJsonBeneficiario["status_trans"] = data_status
    objJsonBeneficiario["nombre_emisor"] = data_nombreEmisor
    objJsonBeneficiario["nombre_beneficiario"] = data_nombreBene
    objJsonBeneficiario["fecha"] = fecha
    objJsonBeneficiario["id_transferencia"] = queryUltimoMovimiento["id"]

    # envío notificación (emisor)
    if hasTokenDevice(idPersona=pk_persona):
        sendNotify(idPersona=pk_persona, tituloNoti=tmpIdioma_titulo, msgNoti=tmpIdioma_cuerpo,
            tituloData=tmpIdioma_titulo, msgData=tmpIdioma_cuerpo, detail=json.dumps(objJsonDetalle), numDeNotiSinLeer=numDeNotiSinLeer_)

    # envío notificación a beneficiario polipay, unicamente para el escenario de Polipay a Polipay (beneficiario)
    if str(data_tipoMovimiento) == "1":
        queryExisteCuentaBene   = cuenta.objects.filter(cuenta=objJson["cta_beneficiario"]).exists()
        if not queryExisteCuentaBene:
            msg = LanguageRegisteredUser(pk_persona, "Not011BE")
            return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
            #return Response({"status": "La cuenta beneficiario no existe o no pertenece\na Polipay, favor de verificar"
            #                           "los datos."}, status=status.HTTP_400_BAD_REQUEST)

        queryCuentaBene = cuenta.objects.filter(cuenta=objJson["cta_beneficiario"]).values("id")
        if len(queryCuentaBene) == 0 or queryCuentaBene == None or queryCuentaBene == "":
            msg = LanguageRegisteredUser(pk_persona, "Not012BE")
            return Response({"status": msg}, status=status.HTTP_400_BAD_REQUEST)
            #return Response({"status": "Cuenta beneficiario no existe o no pertenece\na Polipay, favor de verificar los datos."},
            #                status=status.HTTP_400_BAD_REQUEST)

        objJsonBeneficiario["cuentatransferencia"]  = queryCuentaBene[0]["id"]

        notifyAppUserFromWeb(objJsonBeneficiario, 1)


