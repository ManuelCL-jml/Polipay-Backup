from django.core.cache import cache

from rest_framework import serializers

from twilio.rest import Client

from polipaynewConfig.settings import account_sid,auth_token,phone_twilio
import os
import random

# (JM 2021/12/06) LLama al numero del usuario para dar el codigo
def SendCallCode(code_call, instance):
    try:
        phone = instance.phone
        client = Client(account_sid, auth_token)
        voice_message = "Tu código de verificación para Polipay es" + code_call[0] + code_call[1] + code_call[2] + code_call[3]

        call = client.calls.create(
        twiml='<Response><Pause length="2"/><Say voice="alice" language="es-MX">'+ voice_message + '</Say></Response>',
        from_= phone_twilio,
        to = str(phone)
        ) 

        return
    except:
        raise serializers.ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [{"field":"", "data":instance.phone,"message": "No se pudo realizar la llamada"}]})