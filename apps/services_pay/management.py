from .models import LogEfectiva, TransmitterHaveTypes, TranTypes, Transmitter
from datetime import date
from rest_framework import serializers
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from apps.users.models import cuenta, persona
from apps.transaction.models import tipo_transferencia
from apps.transaction.models import transferencia, Status, bancos
from MANAGEMENT.EncryptDecrypt.encdec_nip_cvc_token4dig import encdec_nip_cvc_token4dig
from MANAGEMENT.Utils.utils import generate_clave_rastreo_with_uuid


import datetime
"""
    Funcion para generar el numero de ticket asociado a la transaccion
"""


def generate_ticket():
    today = date.today()
    string_date = str(today).split("-")
    ticket = "PP" + string_date[2] + string_date[1] + string_date[0][2:4]  # Ejemplo: PP230322
    query = LogEfectiva.objects.filter(payment_date__year=today.year, payment_date__month=today.month,
                                       payment_date__day=today.day)  # buscamos todos los registros de hoy

    if len(query) <= 0:
        ticket = ticket + "0001"
    else:
        # recuperamos los ultimos 4 digitos del ultimo ticket e incrementamos en 1
        no_ticket = int(query.last().ticket[8:12]) + 1
        last_numbers = str(no_ticket)

        # convertimos en cadena el numero de ticket actual y le concatenamos Ceros para que tenga una longitud de 4
        if len(last_numbers) < 4:
            missing_zeros = 4 - len(last_numbers)
            for i in range(missing_zeros):
                last_numbers = "0" + last_numbers
        ticket = ticket + last_numbers
    return ticket


"""
    Funcion para verificar que la cuenta existe
"""


def existing_account(no_cuenta, endpoint):
    instance_cuenta = cuenta.objects.filter(cuenta=no_cuenta)
    if len(instance_cuenta) <= 0:
        message_not_register = {
            "status": ["Cuenta no encontrada"]
        }

        RegisterSystemLog(idPersona=-1, type=1,
                          endpoint=endpoint,
                          objJsonResponse=message_not_register)
        raise serializers.ValidationError(message_not_register)
    return instance_cuenta[0].persona_cuenta_id


"""
    Funcion para ordenar en una lista de diccionarios los servicios frecuentes
"""


def generate_list_frequents(query):
    list_transmitters = []
    for i in query:
        query_transmitter = Transmitter.objects.get(id=i.transmmiter_Rel.id)
        list_transmitters.append(query_transmitter)
    return list_transmitters


"""
    Funcion para obtener los datos de cuenta de una persona
"""


def get_info_account_from_person(id_persona):
    instance_person = cuenta.objects.get(persona_cuenta_id=id_persona)
    dict_person = {
        "cuenta": instance_person.cuenta,
        "cuentaclave": instance_person.cuentaclave,
        "monto": instance_person.monto
    }
    return dict_person


"""
    Funcion para verificar el token
"""


def test_verify_token(id_persona):
    instance_person = persona.objects.get(id=id_persona)
    decrypt_token = encdec_nip_cvc_token4dig(accion="2", area="BE", texto=instance_person.token)
    print("TOKEN DE DB!!!")
    print(decrypt_token['data'])


"""
    Funcion para construir la respuesta del trantype 30
"""


def create_response_trantype30(response, context):
    if response.solicitaResult != 0:
        message_invalid_ref = {
            "status": ["Numero de referencia no encontrado, por favor verifica los datos"]
        }

        RegisterSystemLog(idPersona=context["person_id"], type=1,
                          endpoint=context["endpoint"],
                          objJsonResponse=message_invalid_ref)
        raise serializers.ValidationError(message_invalid_ref)
    else:
        message_data_trantype30 = {
            "status": "Consulta de saldo exitosa",
            "data": {
                "monto": int(response.info3["Saldo"]["SaldoTotal"])/100 #lo transformamos a decimales
            }
        }
        return message_data_trantype30


"""
    Funcion para construir la respuesta del trantype 30
"""


def create_response_trantype32(response, context):
    if response.solicitaResult != 0:
        message_invalid_ref = {
            "status": ["Emisor no encontrado, por favor verifica los datos"]
        }

        # RegisterSystemLog(idPersona=context["person_id"].id, type=1,
        #                   endpoint=context["endpoint"],
        #                   objJsonResponse=message_invalid_ref)
        raise serializers.ValidationError(message_invalid_ref)
    else:
        if 'Comision' in response.info3["Servicio"]:
            comision = int(response.info3["Servicio"]["Comision"])/100
        else:
            comision = 0
        if 'Cargo' in response.info3["Servicio"]:
            cargo = int(response.info3["Servicio"]["Cargo"])/100
        else:
            cargo = 0
        message_data_trantype31 = {
            "status": "Consulta de emisor exitosa",
            "data": {
                "comision": comision,
                "cargo": cargo
            }
        }
        return message_data_trantype31


"""
    Funcion para crear el registro de la transaccion de red efectiva (Pago del servicio y Pago de la comision)
"""


def create_transference_register(dict_transference):
    status_trans_id = 1 if dict_transference["solicitaResult"] == 0 else 7
    instance_tipo_pago = tipo_transferencia.objects.get(id=8)
    instance_status_trans = Status.objects.get(id=status_trans_id)
    instance_transmitter_bank = bancos.objects.get(id=86)

    # Registro de la transaccion del monto
    transferencia.objects.create(
        cta_beneficiario=8960010002,
        clave_rastreo=generate_clave_rastreo_with_uuid(),
        nombre_beneficiario=dict_transference["nombre_servicio"],
        rfc_curp_beneficiario="N/A",
        tipo_cuenta="N/A",
        monto=dict_transference["monto"],
        concepto_pago="Pago de servicio " + dict_transference["nombre_servicio"] + " Por medio de red efectiva",
        referencia_numerica=dict_transference["referencia"],
        empresa="RedEfectiva",
        nombre_emisor=dict_transference["nombre_emisor"],
        cuenta_emisor=dict_transference["cuenta"],
        cuentatransferencia=dict_transference["cuentatransferencia"],
        status_trans=instance_status_trans,
        tipo_pago=instance_tipo_pago,
        email=dict_transference["email"],
        saldo_remanente=dict_transference["saldoRemanente"],
        transmitter_bank=instance_transmitter_bank,
        date_modify=datetime.datetime.now()
    )
    # Registro de la transaccion de la comision
    transferencia.objects.create(
        cta_beneficiario=8960010002,
        clave_rastreo=generate_clave_rastreo_with_uuid(),
        nombre_beneficiario=dict_transference["nombre_servicio"],
        rfc_curp_beneficiario="N/A",
        tipo_cuenta="N/A",
        monto=dict_transference["comision"],
        concepto_pago="Comision de Pago de servicio " + dict_transference["nombre_servicio"] + " Por medio de red efectiva",
        referencia_numerica=dict_transference["referencia"],
        empresa="RedEfectiva",
        nombre_emisor=dict_transference["nombre_emisor"],
        cuenta_emisor=dict_transference["cuenta"],
        cuentatransferencia=dict_transference["cuentatransferencia"],
        status_trans=instance_status_trans,
        tipo_pago=instance_tipo_pago,
        email=dict_transference["email"],
        saldo_remanente=dict_transference["saldoRemanente"],
        transmitter_bank=instance_transmitter_bank,
        date_modify=datetime.datetime.now()
    )
