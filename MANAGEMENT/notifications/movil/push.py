import datetime
import json

import firebase_admin
from firebase_admin import credentials, messaging, exceptions

from apps.notifications.models import notification

cred = credentials.Certificate("MANAGEMENT/FireBase/keys/serviceAccountKey.json")
push_cerrar_sesion = firebase_admin.initialize_app(cred)


# def push_notify(user_id, messages, registration_token, e=None):
#     try:
#         message = messaging.Message(
#             notification=messaging.Notification(
#                 title="Alerta PoliPay Wallet",
#                 body="Su sesión a sido finalizada."
#             ),
#             android=messaging.AndroidConfig(
#                 ttl=datetime.timedelta(seconds=3600),
#                 priority='high',
#                 notification=messaging.AndroidNotification(
#                     icon='stock_ticker_update',
#                     color='#f45342'
#                 ),
#             ),
#             apns=messaging.APNSConfig(
#                 payload=messaging.APNSPayload(
#                     aps=messaging.Aps(),
#                     #aps=messaging.Aps(badge=42),
#                 ),
#             ),
#             data={
#                 "click_action": "FLUTTER_NOTIFICATION_CLICK",
#                 "type": "Session",
#                 "title": "Alerta Polipay",
#                 "id": str(user_id),
#                 "message": messages
#             },
#             token=registration_token,
#         )
#
#         response = messaging.send(message)
#         print('Successfully sent message:', response)
#         return True, e
#
#     except exceptions.NotFoundError as e:
#         return False, 'NotFoundError'
#     except exceptions.InvalidArgumentError as e:
#         return False, e
#     except exceptions.UnknownError as e:
#         return False, e

def push_notify(user_id: int, messages: str, registration_token: str):
    message = messaging.Message(
        notification=messaging.Notification(
            title="Alerta PoliPay Wallet",
            body="Su sesión a sido finalizada."
        ),
        android=messaging.AndroidConfig(
            ttl=datetime.timedelta(seconds=3600),
            priority='high',
            notification=messaging.AndroidNotification(
                icon='stock_ticker_update',
                color='#022E92'
            ),
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(),
            ),
        ),
        data={
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "Session",
            "title": "Alerta Polipay",
            "id": str(user_id),
            "message": messages
        },
        token=registration_token,
    )

    response = messaging.send(message)
    print('Successfully sent message:', response)


# Envia notificación a la app del token cuando se cierre sesión
def push_notify_logout(user_id: int, messages: str, registration_token: str):
    message = messaging.Message(
        notification=messaging.Notification(
            title="Alerta Polipay Token",
            body="Su sesión a sido finalizada."
        ),
        android=messaging.AndroidConfig(
            ttl=datetime.timedelta(seconds=3600),
            priority='high',
            notification=messaging.AndroidNotification(
                icon='stock_ticker_update',
                color='#022E92'
            ),
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(),
            ),
        ),
        data={
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "logout",
            "title": "Alerta Polipay",
            "id": str(user_id),
            "message": messages
        },
        token=registration_token,
    )

    response = messaging.send(message)
    print('Successfully sent message:', response)


def pushNotifyAppUser(user_id, tittleNoti, messagesNoti, tittleData, messagesData, registration_token, type, detail,
                      numDeNotiSinLeer, e=None):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=str(tittleNoti),
                body=str(messagesNoti)
            ),
            android=messaging.AndroidConfig(
                ttl=datetime.timedelta(seconds=3600),
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='stock_ticker_update',
                    color='#022E92'
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(badge=numDeNotiSinLeer),
                ),
            ),
            data={
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "type": str(type),
                "title": str(tittleData),
                "id": str(user_id),
                "message": str(messagesData),
                "detail": str(detail)
            },
            token=registration_token,
        )

        response = messaging.send(message, app=push_cerrar_sesion)
        print('Successfully sent message:', response)
        return True, e

    except exceptions.NotFoundError as e:
        return False, 'NotFoundError'
    except exceptions.InvalidArgumentError as e:
        return False, e
    except exceptions.UnknownError as e:
        return False, e


# (ChrGil 2022-02-28) Enviá notificación al cliente cuando generar un token
def push_notify_dynamic_token(**kwargs):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=kwargs.get('title'),
                body=kwargs.get('body')
            ),
            android=messaging.AndroidConfig(
                ttl=datetime.timedelta(seconds=3600),
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='stock_ticker_update',
                    color='#022E92'
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(badge=kwargs.get('number_notification')),
                ),
            ),
            data={
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "type": "token",
                "title": kwargs.get('title'),
                "id": str(kwargs.get('owner')),
                "message": kwargs.get('message'),
            },
            token=kwargs.get('token'),
        )

        response = messaging.send(message)
        # print('Successfully sent message:', response)
    except Exception as e:
        # Si hay una exception, no la caches y continua con el proceso
        return True
    else:
        notification.objects.create(
            person_id=kwargs.get('owner'),
            notification_type_id=4,
            json_content=json.dumps(message.data)
        )


# (ChrGil 2022-02-28) Enviá notificación al cliente cuando generar un token
def push_notify_paycash(**kwargs):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=kwargs.get('title'),
                body=kwargs.get('message')
            ),
            android=messaging.AndroidConfig(
                ttl=datetime.timedelta(seconds=3600),
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='stock_ticker_update',
                    color='#022E92'
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(badge=kwargs.get('number_notification')),
                ),
            ),
            data={
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "type": "paycash",
                "title": kwargs.get("title"),
                "id": str(kwargs.get("person_id")),
                "message": kwargs.get("message"),
                "detail": json.dumps(kwargs.get("detail"))
            },
            token=kwargs.get('token'),
        )

        response = messaging.send(message)
    except Exception as e:
        return True

