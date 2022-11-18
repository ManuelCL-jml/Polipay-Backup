import datetime

"""
import firebase_admin
from firebase_admin import credentials, messaging, exceptions

cred = credentials.Certificate("./serviceAccountKey.json")
push_cerrar_sesion = firebase_admin.initialize_app(cred)
"""

class NotificacionFireBase():
	def __init__(self):
		# agregar clase para log de actividad (historico)
		print("(class:NotificacionFireBase, metodo:__init__) iniciando envio de notificación ...");

	def push_notify(self, clickAction, typeTitle, title, user_id, messages, registration_token, e=None):
		print("(class:NotificacionFireBase, metodo:push_notify, params:"+str(clickAction)+", "+str(typeTitle)+", "+str(title)+", "+str(user_id)+", "+str(messages)+", "+str(registration_token)+") dentro del método ...");
		"""
		try:
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
						color='#f45342'
					),
				),
				apns=messaging.APNSConfig(
					payload=messaging.APNSPayload(
						aps=messaging.Aps(badge=42),
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
			return True, e

		except exceptions.NotFoundError as e:
			return False, 'NotFoundError'
		except exceptions.InvalidArgumentError as e:
			return False, e
		except exceptions.UnknownError as e:
			return False, e
		"""

