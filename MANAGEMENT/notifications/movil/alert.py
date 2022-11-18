from typing import Union, Tuple

from rest_framework.serializers import ValidationError

import datetime
import firebase_admin
from firebase_admin import credentials, messaging, exceptions

cred = credentials.Certificate("MANAGEMENT/FireBase/keys/serviceAccountKey.json")
push_alerta = firebase_admin.initialize_app(cred, name='alert')


def send_push(title, message, registration_token):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=message
            ),
            token=registration_token,
        )

        messaging.send(message)
        return True

    except exceptions.NotFoundError as e:
        # raise ValidationError({"status": "Error al enviar notificación. Ya puede iniciar sesión"})
        return False, 'NotFoundError'
    except exceptions.InvalidArgumentError as e:
        return False, e
        # raise ValidationError({"status": "Hubo un error al momento de enviar la notificación"})
    except exceptions.UnknownError as e:
        return False, e
        # raise ValidationError({"status": ["Error deconocido", e]})
