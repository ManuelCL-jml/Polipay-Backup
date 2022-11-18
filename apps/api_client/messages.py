from rest_framework.serializers import ValidationError

from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings
from apps.users.models import persona
from .management import *
from .models import *
from typing import List


def create_structure_and_send_email(template_mail: str, context: dict, title, body):
    try:
        template = get_template(template_name=template_mail)
        content = template.render(context)
        email = EmailMultiAlternatives(title, body, settings.EMAIL_HOST_USER, [context['email']])
        email.attach_alternative(content, 'text/html')
        email.send()
        return True

    except Exception as e:
        raise ValidationError(
            {'status': [f'Error al enviar el correo: {e}']})


def create_structure_context(instance, cuenta_eje_name, url=None):
    return {
        'email': instance.email,
        'instance': instance,
        'cuenta_eje_name': cuenta_eje_name,
        'url': url,
    }


def create_structure_context_credentials(instance, username, password):
    return {
        'email': instance.email,
        'instance': instance,
        'username': username,
        'password': password,
    }


def send_mail_superuser(id_cuenta_eje):
    instance_superuser = persona.objects.get(is_superuser=1, id=1690)
    cuenta_eje = persona.objects.get(id=id_cuenta_eje)
    context = create_structure_context(instance=instance_superuser, cuenta_eje_name=cuenta_eje.name)
    create_structure_and_send_email(
        'admin_APIrequest.html',
        context,
        'Solicitud API-Cliente Dispersa',
        'Administrador'
    )

    return True


def send_reject_mail_admin(id_cuenta_eje):
    list_admin = get_list_admins(id_cuenta_eje)
    for admin in list_admin:
        context = create_structure_context(instance=admin, cuenta_eje_name=None)
        create_structure_and_send_email(
            'admin_APIresponseD.html',
            context,
            'Respuesta solicitud API-Cliente Dispersa',
            'Administrador'
        )
    return True


def send_acceptance_mail_admin(id_cuenta_eje):
    list_admin = get_list_admins(id_cuenta_eje)
    instance_credencial = CredencialesAPI.objects.get(personaRel_id=id_cuenta_eje)
    for admin in list_admin:
        context_username = create_structure_context_credentials(instance=admin, username=instance_credencial.username,
                                                                password=None)
        create_structure_and_send_email(
            'admin_APIresponseA_U.html',
            context_username,
            'Respuesta solicitud API-Cliente Dispersa',
            'Administrador'
        )
        context_password = create_structure_context_credentials(instance=admin, username=None,
                                                                password=instance_credencial.password)
        create_structure_and_send_email(
            'admin_APIresponseA_P.html',
            context_password,
            'Respuesta solicitud API-Cliente Dispersa',
            'Administrador'
        )
    return True


def send_block_mail_admin(id_cuenta_eje):
    list_admin = get_list_admins(id_cuenta_eje)
    for admin in list_admin:
        context = create_structure_context(instance=admin, cuenta_eje_name=None)
        create_structure_and_send_email(
            'admin_APICredential_block.html',
            context,
            'Bloqueo de credenciales API-Cliente Dispersa',
            'Administrador'
        )
    return True


def resend_credentials_mail(id_cuenta_eje):
    list_admin = get_list_admins(id_cuenta_eje)
    instance_credencial = CredencialesAPI.objects.get(personaRel_id=id_cuenta_eje)
    for admin in list_admin:
        context_username = create_structure_context_credentials(instance=admin, username=instance_credencial.username,
                                                                password=None)
        create_structure_and_send_email(
            'admin_UpdateAPICredentials_U.html',
            context_username,
            'Nuevas credenciales para API-Cliente Dispersa',
            'Administrador'
        )
        context_password = create_structure_context_credentials(instance=admin, username=None,
                                                                password=instance_credencial.password)
        create_structure_and_send_email(
            'admin_UpdateAPICredentials_P.html',
            context_password,
            'Nuevas credenciales para API-Cliente Dispersa',
            'Administrador'
        )
    return True


def createWelcomeMessageExternalPerson(instance, password, Cuenta, nombre):
    try:

        diccionario = {'name': instance.get_full_name, 'usario': instance.email, 'pass': password,
                       'NumeroCuenta': Cuenta}
        plaintext = get_template('welcomePersonaExterna.txt')
        htmly = get_template('welcomePersonaExterna.html')

        subject, from_email, to = 'Avisos Polipay', 'noreply@polipay.mx', instance.email
        text_content = plaintext.render(diccionario)
        html_content = htmly.render(diccionario)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True

    except Exception as e:
        raise ValidationError({'status': ['Error al enviar el correo y/o el correo no es valido']})


"""
    Funcion para email en dispersiones masivas
"""


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
            template_name='dispersion_mas_API_emisor.html',
            context=context,
            title=context['observation'],
            body=context['observation'],
            email=context['email']
        )


def send_email_beneficiario(list_beneficiario: List[Dict]):
    for context in list_beneficiario:
        message_email(
            template_name='dispersion_mas_API_beneficiario.html',
            context=context,
            title='Dispersion',
            body=context['observation'],
            email=context['email']
        )


def send_massive_email(list_beneficiario: List[Dict], list_emisor: List[Dict]):
    send_email_beneficiario(list_beneficiario)
    send_email_emisor(list_emisor)
    return True


"""
    Mensajes para dispersiones individuales
"""

def createMessageTransactionSend(instancePersona, InstancePass, transferencia):
    diccionario = {}
    diccionario['user'] = instancePersona.name
    diccionario['folio'] = InstancePass.id
    diccionario['status'] = transferencia.status_trans.nombre
    plaintext = get_template('dispersion_ind_API.txt')
    htmly = get_template('dispersion_ind_API.html')

    subject, from_email, to = 'Avisos Polipay', settings.EMAIL_HOST_USER, instancePersona.email
    text_content = plaintext.render(diccionario)
    html_content = htmly.render(diccionario)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    return True
