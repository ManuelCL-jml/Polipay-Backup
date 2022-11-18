# Download the helper library from https://www.twilio.com/docs/python/install
from django.core.cache import cache
from apps.users import messages

from rest_framework import serializers

from twilio.rest import Client

from polipaynewConfig.settings import account_sid,auth_token,phone_twilio
import os
import random



# (JM 2021/12/06) Envia un mensaje con el codigo al usuario
def EnviarCodigoSMS(code, instance):
    try:
        #account_sid = 'ACba1591c9a283e6f4f5c8b882c863b5fc' #Prueba
        #auth_token = '66b8af8a96837cc34d4bbccfddc8be49' #Prueba
        phone = instance.phone
        client = Client(account_sid, auth_token)

        message_send = ("Tu código de verificación para Polipay es: " + str(code) + ". Tu código sera valido por 5 minutos")

        message = client.messages \
            .create(
            body=message_send,
            from_= phone_twilio,
            to = str(phone)
            #from_= '+14092152770', #Prueba
            #to = str("+525562189994") #Prueba
        )
        return
    except:
        raise serializers.ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [{"field":"", "data":instance.phone,"message": "No se pudo enviar el mensaje"}]})

