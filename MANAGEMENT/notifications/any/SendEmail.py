import smtplib
from email.message import EmailMessage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mass_mail
from django.template.loader import get_template


def SendEmail(pathToTemplate : str, pathToAttachment : str, objJson : dict):
    # objJson   ={"tipo":"Card | Cards | Account | AccountCards", "nombre": "Nombre", "rango": "YYYY-MM-DD al YYYY-MM-DD", "email":"usu@e.com"}

    # Se confirma ruta de la plantilla

    # Se confirma ruta del adjunto

    #diccionario                 = {}
    #diccionario['name']         = instancePerson.name + ' ' + instancePerson.last_name
    #diccionario['folio']        = InstancePass.id
    #diccionario['ordenante']    = InstancePass.cuenta_emisor

    plaintext                   = get_template(pathToTemplate + str(".txt"))
    htmly                       = get_template(pathToTemplate + str(".html"))

    titulo          = "Reporte de Movimientos"
    remitente       = settings.EMAIL_HOST_USER
    destinatario    = objJson["email"]
    objJson.pop("email")

    text_content    = plaintext.render(objJson)
    html_content    = htmly.render(objJson)

    msg = EmailMultiAlternatives(titulo, text_content, remitente, [destinatario])
    msg.attach_alternative(html_content, "text/html")
    msg.attach_file(pathToAttachment)

    if msg.send():
        return False
    else:
        return True