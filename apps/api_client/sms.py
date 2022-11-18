from rest_framework import serializers
from twilio.rest import Client
from polipaynewConfig.settings import account_sid, auth_token, phone_twilio


# (JM 2021/12/06) Envia un mensaje con el codigo al usuario
def enviarSMS(monto,instance):
    try:
        phone = instance.phone
        client = Client(account_sid, auth_token)

        message_send = ("Una dispersion fue realizada a tu cuenta por el monto de "+ str(monto))

        message = client.messages \
            .create(
            body=message_send,
            from_= phone_twilio,
            to = "+" + str(phone)
        )
        return
    except:
        message_errorSMS = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": instance.phone,
                    "field": "Phone",
                    "message": "Couldn´t send message",
                }
            ]
        }
        raise serializers.ValidationError(message_errorSMS)


