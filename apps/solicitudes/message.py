from typing import List, Dict
from django.core.mail import EmailMultiAlternatives, send_mass_mail
from django.template.loader import get_template
from django.conf import settings
from rest_framework.exceptions import ValidationError


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


def send_email_admins_and_superadmin(list_email_admin_and_superadmin: List[Dict]):
    for context in list_email_admin_and_superadmin:
        message_email(
            template_name='solicitud_tarjetas.html',
            context=context,
            title='Solicitud de saldos',
            body='referencia',
            email=context['email']
        )


def send_email_admins_and_colaborators(list_email_admins_and_colaborators: List[Dict]):
    for context in list_email_admins_and_colaborators:
        message_email(
            template_name='solicitud_tarjetas_admin.html',
            context=context,
            title='Solicitud de Saldos',
            body='referencia',
            email=context['person__email']
        )


def send_massive_email(list_email_admins_and_colaborators: List[Dict], list_email_admin_and_superadmin: List[Dict]):
    send_email_admins_and_superadmin(list_email_admin_and_superadmin)
    send_email_admins_and_colaborators(list_email_admins_and_colaborators)
    return True


def send_email_authorization_balances(list_email_admins_and_colaborators: List[Dict]):
    for context in list_email_admins_and_colaborators:
        message_email(
            template_name='autorizacion_saldos.html',
            context=context,
            title='Autorización de Saldo',
            body='referencia',
            email=context['person__email']
        )


def send_email_authorization(list_email_admins_and_colaborators: List[Dict]):
    send_email_authorization_balances(list_email_admins_and_colaborators)
    return True
