from polipaynewConfig.settings import PRIVATE_KEY_STP
from rest_framework.serializers import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings

from typing import List, Dict

from polipaynewConfig.exceptions import *

from apps.users.models import *


def createMessageWelcome(instance, password):
    try:

        diccionario = {'name': instance.get_full_name(), 'usario': instance.email, 'pass': password}
        plaintext = get_template('welcome.txt')
        htmly = get_template('welcome.html')

        subject, from_email, to = 'Avisos Polipay', 'noreply@polipay.mx', instance.email
        text_content = plaintext.render(diccionario)
        html_content = htmly.render(diccionario)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True

    except Exception as e:
        raise ValidationError({'status': ['Error al enviar el correo y/o el correo no es valido']})


def createMessageAsigmentCode(user, code, type):
    diccionario = {}
    diccionario['name'] = user.get_full_name()
    diccionario['code'] = code
    diccionario['type'] = type
    plaintext = get_template('codigo.txt')
    htmly = get_template('codigo.html')

    subject, from_email, to = 'Avisos Polipay', 'noreply@polipay.mx', user.email
    text_content = plaintext.render(diccionario)
    html_content = htmly.render(diccionario)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    return True


# TMP (ChrGil 2022-01-27) Envio de corre a brigadistas de Adelante Zapopan
def send_mail_brigadistas(user: persona, code: str):
    diccionario = {}
    diccionario['name'] = user.name
    diccionario['code'] = code
    htmly = get_template('brigadista_enviar_codigo.html')

    subject, from_email, to = 'Avisos Polipay', 'noreply@polipay.mx', user.email
    html_content = htmly.render(diccionario)
    msg = EmailMultiAlternatives(subject, html_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    return True


def create_structure_context(instance, password=None, url=None):
    return {
        'email': instance.email,
        'instance': instance,
        'pass': password,
        'url': url,
    }


def create_structure_context_extern_client(nombre, email, cliente, Estado):
    return {
        'name': nombre,
        'email': email,
        'ClienteExterno': cliente,
        'Estado': Estado,
    }

def create_structure_context_cost_center(nombre, email, cliente: Dict[str, Any]):
    return {
        'name': nombre,
        'email': email,
        'CentroCostos': cliente.get('RazonSocial')['data']['CentroCosto'],
        'Estado': 'Pendiente',
    }


def create_structure_context_edit_fiscal_address_and_clabe_traspaso(nombre, email, cliente, Estado):
    return {
        'name': nombre,
        'email': email,
        'CentroCostos': cliente,
        'Estado': Estado,
    }

def create_structure_context_returned_cost_center(nombre, email, cliente):
    return {
        'name': nombre,
        'email': email,
        'CentroCostos': cliente,
        'Estado': 'Devuelto',
    }


def create_structure_context_auth_cost_center(nombre, email, cliente):
    return {
        'name': nombre,
        'email': email,
        'CentroCostos': cliente,
        'Estado': 'Autorizado',
    }


def create_context(date, instance, password=None, url=None):
    return {
        'email': instance.email,
        'instance': instance,
        'pass': password,
        'url': url,
        'date': date
    }


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


# Se cambio el metodo create_structure_context por create_context
def send_mail_warnign(user, url):
    date = datetime.datetime.now().strftime('%d-%m-%Y a las %H:%M:%S')
    context = create_context(date, instance=user, url=url)
    create_structure_and_send_email(
        'warning_msg.html',
        context,
        'Alerta de seguridad Polipay',
        'Movimientos sospechosos.'
    )

    return True


def send_change_password(user):
    context = create_structure_context(instance=user)
    create_structure_and_send_email(
        'change_password.html',
        context,
        'Notificación de cambio de contraseña',
        'Cambio de contraseña'
    )

    return True


def send_mail_superuser(user, password):
    context = create_structure_context(instance=user, password=password)
    create_structure_and_send_email(
        'admin_email.html',
        context,
        'Usuario administrador Polipay',
        'Administrador'
    )

    return True


def sendNotificationCreateCostCenter(nombre, email, cliente: Dict[str, Any]):
    context = create_structure_context_cost_center(nombre=nombre, email=email, cliente=cliente)
    create_structure_and_send_email('notificacion-centro-costos.html',
                                    context,
                                    'Notificacion apertura centro de costos',
                                    'Centro de Costos')


def send_notifications_returned_cost_center(nombre, email, cliente):
    context = create_structure_context_returned_cost_center(nombre=nombre, email=email, cliente=cliente)
    create_structure_and_send_email('notificacion-centro-costos-devuelto.html',
                                    context,
                                    'Devolución de centro de costos',
                                    'Centro de Costos')


def send_notification_auth_cost_center(nombre, email, client):
    context = create_structure_context_auth_cost_center(nombre=nombre, email=email, cliente=client)
    create_structure_and_send_email('notificacion-centro-costos-autorizado.html',
                                    context,
                                    'Autorizacion de centro de costos',
                                    'Centro de Costos')


def sendNotificationAmendExternClient(nombre, email, cliente, Estado):
    context = create_structure_context_extern_client(nombre=nombre, email=email, cliente=cliente, Estado=Estado)
    create_structure_and_send_email('notificacion-amend-cliente-externo.html',
                                    context,
                                    'Notificación de edicion de cliente externo',
                                    'Cliente Externo')
    return True


def sendNotificationEditFiscalAddress(nombre, email, cliente, Estado):
    context = create_structure_context_edit_fiscal_address_and_clabe_traspaso(nombre=nombre, email=email, cliente=cliente, Estado=Estado)
    create_structure_and_send_email('notificacion-edit-fiscal-address.html',
                                    context,
                                    'Edicion domicilio fiscal',
                                    'Domicilio Fiscal')
    return True


def sendNotificationEditClaveTraspaso(nombre, email, cliente, Estado):
    context = create_structure_context_edit_fiscal_address_and_clabe_traspaso(nombre=nombre, email=email, cliente=cliente, Estado=Estado)
    create_structure_and_send_email('notificacion-edit-clabe_traspaso_final.html',
                                    context,
                                    'Edicion clabe traspaso final',
                                    'Clabe Traspaso Final')


def createMessageWelcomeExternalPerson(instance, password, Cuenta, nombre):
    try:
        diccionario = {'name': nombre, 'usario': instance.email, 'pass': password, 'NumeroCuenta': Cuenta}
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


def createMessageWelcomeExternalPerson(nombre, email, password, Cuenta):
    try:
        diccionario = {'name': nombre, 'usario': email, 'pass': password, 'NumeroCuenta': Cuenta}
        plaintext = get_template('welcomePersonaExterna.txt')
        htmly = get_template('welcomePersonaExterna.html')

        subject, from_email, to = 'Avisos Polipay', 'noreply@polipay.mx', email
        text_content = plaintext.render(diccionario)
        html_content = htmly.render(diccionario)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True
    except:
        message = "No se pudo enviar el correo electronico"
        error = {'field': '', "data": email, 'message': message}
        MensajeError(error)


def messageAddAdminToCompany(instance, password, name, last_name):
    try:

        diccionario = {'name': f'{name} {last_name}', 'usario': instance.email, 'pass': password}
        plaintext = get_template('welcomeAddAdminCompany.txt')
        htmly = get_template('welcomeAddAdminCompany.html')

        subject, from_email, to = 'Avisos Polipay', 'noreply@polipay.mx', instance.email
        text_content = plaintext.render(diccionario)
        html_content = htmly.render(diccionario)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True

    except Exception as e:
        raise ValidationError({'status': ['Error al enviar el correo y/o el correo no es valido']})


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


#############
import itertools


def pruebas():
    datos = []
    letras = "C"
    for num in itertools.count(start=1):
        print(num)
        PersonList = {
            "Correo_Electronico": "PruebaMasivoben" + letras + str(num) + "@gggmaiil.com",
            "Apellido_Paterno": "PruebaMasivoben" + letras + str(num),
            "Apellido_Materno": "",
            "Nombres": "PruebaMasivoben" + letras + str(num),
            "Fecha_de_Nacimiento": "",
            "Descripcion_de_Actividades": "PruebaMasivoben" + letras + str(num),
            "RFC": "1234Prueba1"
        }

        datos.append(PersonList)
        if num == 500:
            return datos


def send_email_beneficario_masivo(beneficiario):
    error = []
    for datos in beneficiario:
        try:
            user = persona.objects.get(id=datos["id"])
            diccionario = {'name': user.name, 'usario': user.email,
                           'pass': str(user.name).replace(" ", "").replace("*", "") + "9/P",
                           'NumeroCuenta': datos["NumeroCuenta"]}
            plaintext = get_template('welcomePersonaExterna.txt')
            htmly = get_template('welcomePersonaExterna.html')
            subject, from_email, to = 'Avisos Polipay', 'noreply@polipay.mx', user.email
            text_content = plaintext.render(diccionario)
            html_content = htmly.render(diccionario)
            msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
        except:
            user = persona.objects.get(id=datos["id"])
            error.append({"field": "Correo_Electronico", "data": user.email,
                          "message": "No se pudo enviar el correo correo electronico"})
    MensajeError(error)
    return


def send_email_access_extern_client(instance):
    try:
        diccionario = {'name': instance.get_full_name, "email": instance.email, "password":instance.password}
        plaintext = get_template('welcome_extern_client.txt')
        htmly = get_template('welcome_extern_client.html')

        subject, from_email, to = 'Apertura Cliente Externo', 'noreply@polipay.mx', instance.email
        text_content = plaintext.render(diccionario)
        html_content = htmly.render(diccionario)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True
    except:
        message = "No se pudo enviar el correo electronico"
        error = {'field': '', "data": instance.email, 'message': message}
        MensajeError(error)
