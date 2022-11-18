from typing import List, Dict

from django.core.mail import EmailMultiAlternatives, send_mass_mail
from django.template.loader import get_template
from django.conf import settings
from rest_framework.exceptions import ValidationError

from polipaynewConfig.settings import EMAIL_USER_NC, EMAIL_PASSWORD_NC, EMAIL_NC_TO
from apps.users.models import *
from apps.transaction.models import Status
import smtplib
from email.message import EmailMessage


def createMessageTransactionRecieved(instance, InstancePass):
    instancePerson = persona.objects.get(id=instance.persona_cuenta_id)
    diccionario = {}
    diccionario['name'] = instancePerson.name + ' ' + instancePerson.last_name
    diccionario['folio'] = InstancePass.id
    diccionario['ordenante'] = InstancePass.cuenta_emisor
    plaintext = get_template('deposito-recibido.txt')
    htmly = get_template('deposito-recibido.html')

    subject, from_email, to = 'Avisos Polipay', settings.EMAIL_HOST_USER, instancePerson.email
    text_content = plaintext.render(diccionario)
    html_content = htmly.render(diccionario)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    return True


def createMessageTransactionSend(instancePersona, InstancePass, transferencia):
    diccionario = {}
    diccionario['user'] = instancePersona.name
    diccionario['folio'] = InstancePass.id
    diccionario['status'] = transferencia.status_trans.nombre
    plaintext = get_template('transaccion.txt')
    htmly = get_template('transaccion.html')

    subject, from_email, to = 'Avisos Polipay', settings.EMAIL_HOST_USER, instancePersona.email
    text_content = plaintext.render(diccionario)
    html_content = htmly.render(diccionario)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    return True


##Email para transacciones Masivas
def createMessageTransactionMassive(instanceM, IdPersona, IdStatus):
    diccionario = {}
    diccionario['name'] = IdPersona.name + ' ' + IdPersona.last_name
    diccionario['folio'] = instanceM.id
    diccionario['status'] = IdStatus.nombre
    plaintext = get_template('transferenciaMasiva-usuario-colab.txt')
    htmly = get_template('transferenciaMasiva-usuario-colab.html')

    subject, from_email, to = 'Avisos Polipay', settings.EMAIL_HOST_USER, IdPersona.email
    text_content = plaintext.render(diccionario)
    html_content = htmly.render(diccionario)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def createMessageReceptionContact(ValidateEmail, name):
    try:
        message = "Hemos recibido su mensaje: " + name + "\nPronto nos comunicaremos"
        subject = "Avisos Competitividad21: Recepción de contacto"
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER_NC, EMAIL_PASSWORD_NC)

        email = EmailMessage()
        email.set_content(message)
        email["To"] = ValidateEmail
        email["From"] = EMAIL_USER_NC
        email["Subject"] = subject
        server.send_message(email)
        server.quit()
        return True
    except:
        return False


def createMessageNewClient(instance):
    message = "Alguien quiere contactarte:" + "\nNombre: " + instance.name + "\nCorreo: " + instance.email + "\nPais: " + instance.country + " \nTelefono: " + instance.phone + " \nMensaje: " + instance.message
    subject = "Avisos Competitividad21: Nuevo cliente"
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(EMAIL_USER_NC, EMAIL_PASSWORD_NC)

    email = EmailMessage()
    email.set_content(message)
    email["To"] = EMAIL_NC_TO
    email["From"] = EMAIL_USER_NC
    email["Subject"] = subject
    server.send_message(email)
    server.quit()


def message_email(template_name: str, context: Dict, title: str, body: str, email: str):
    try:
        template = get_template(template_name=template_name)
        content = template.render(context)
        email = EmailMultiAlternatives(title, body, settings.EMAIL_HOST_USER, [email])
        email.attach_alternative(content, 'text/html')
        email.send()
        return True

    except Exception as e:
        raise ValidationError(
            {'status': [f'Error al enviar el correo: {e}']})


def send_email_emisor(list_emisor: List[Dict]):
    for context in list_emisor:
        message_email(
            template_name='MailDispersionesEmisor.html',
            context=context,
            title=context['observation'],
            body=context['observation'],
            email=context['email']
        )


def send_email_beneficiario(list_beneficiario: List[Dict]):
    for context in list_beneficiario:
        message_email(
            template_name='MailDispersionesBeneficiario.html',
            context=context,
            title='Dispersion',
            body=context['observation'],
            email=context['email']
        )


def send_massive_email(list_beneficiario: List[Dict], list_emisor: List[Dict]):
    send_email_beneficiario(list_beneficiario)
    send_email_emisor(list_emisor)
    return True


# (ChrGil 2021-11-25) Envia correo a la persona que emitio la transacción masiva cuando se cancela o autoriza
def send_email_transaction_massive(list_emisor: List[Dict]):
    for context in list_emisor:
        message_email(
            template_name='notificacion-movimientos.html',
            context=context,
            title="Estado de Transacción",
            body=f"Estado {context['status']}",
            email=context['email']
        )

def send_email_authorize_transaction(instance, persona_emisor_email, name_user_autoriza):
    try:
        get_name_status= Status.objects.get(id=instance.status_trans_id)
        diccionario = {'name': instance.nombre_emisor, 'folio':instance.id,'status':get_name_status.nombre, 'user_autoriza':name_user_autoriza}
        plaintext = get_template('autorizacion_transferencia_polipay_terceros.txt')
        htmly = get_template('autorizacion_transferencia_polipay_terceros.html')

        subject, from_email, to = 'Avisos Polipay', 'noreply@polipay.mx', persona_emisor_email
        text_content = plaintext.render(diccionario)
        html_content = htmly.render(diccionario)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True

    except Exception as e:
        raise ValidationError({'status': ['Error al enviar el correo y/o el correo no es valido']})

def send_email_cancel_transaction_emisor(instance, persona_emisor_email, name_user_cancela):
    try:
        get_name_status= Status.objects.get(id=instance.status_trans_id)
        diccionario = {'name': instance.nombre_emisor, 'folio':instance.id,'status':get_name_status.nombre, 'user_cancela': name_user_cancela}
        plaintext = get_template('cancelar_transaction_person_emisor.txt')
        htmly = get_template('cancelar_transaction_person_emisor.html')

        subject, from_email, to = 'Avisos Polipay', 'noreply@polipay.mx', persona_emisor_email
        text_content = plaintext.render(diccionario)
        html_content = htmly.render(diccionario)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True

    except Exception as e:
        raise ValidationError({'status': ['Error al enviar el correo y/o el correo no es valido']})

def send_email_cancel_transaction_user_autorize(instance, persona_emisor_email, name_user_cancela):
    try:
        get_name_status= Status.objects.get(id=instance.status_trans_id)
        diccionario = {'name': instance.nombre_emisor, 'folio':instance.id,'status':get_name_status.nombre, 'user_cancela': name_user_cancela}
        plaintext = get_template('cancelar_transaction_user_autorize.txt')
        htmly = get_template('cancelar_transaction_user_autorize.html')

        subject, from_email, to = 'Avisos Polipay', 'noreply@polipay.mx', persona_emisor_email
        text_content = plaintext.render(diccionario)
        html_content = htmly.render(diccionario)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True

    except Exception as e:
        raise ValidationError({'status': ['Error al enviar el correo y/o el correo no es valido']})


def send_email_emisor_polipay_to_polipay(instance_transferecia, persona_emisor_email):
    try:
        get_name_status= Status.objects.get(id=instance_transferecia.status_trans_id)
        diccionario = {'user': instance_transferecia.nombre_emisor, 'folio':instance_transferecia.id,'status':get_name_status.nombre}
        plaintext = get_template('transaccion_polipay_to_polipay.txt')
        htmly = get_template('transaccion_polipay_to_polipay.html')

        subject, from_email, to = 'Avisos Polipay', 'noreply@polipay.mx', persona_emisor_email
        text_content = plaintext.render(diccionario)
        html_content = htmly.render(diccionario)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True

    except Exception as e:
        raise ValidationError({'status': ['Error al enviar el correo y/o el correo no es valido']})


