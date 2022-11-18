from typing import List, Dict
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from rest_framework.exceptions import ValidationError

def message_email(template_name: str, context: Dict, title: str, body: None, email: str):
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