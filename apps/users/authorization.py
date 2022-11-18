import datetime as dt

from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed

# Modulos nativos de django
from django.utils import timezone
from django.conf import settings

# Modulos de python
from datetime import timedelta

from apps.users.models import persona


def expires_in(token):
    time_elapsed = timezone.now() - token.created
    left_time = timedelta(seconds=settings.TOKEN_EXPIRED_AFTER_SECONDS) - time_elapsed
    return left_time


def is_token_expired(token):
    return expires_in(token) < timedelta(seconds=0)


def token_expire_handler(token):
    is_expired = is_token_expired(token)
    if is_expired:
        token.delete()
        token = Token.objects.create(user=token.user)
    return is_expired, token


class ExpiringTokenAuthentication(TokenAuthentication):

    def authenticate_credentials(self, key):
        try:
            token = Token.objects.get(key=key)

        except Exception as e:
            raise AuthenticationFailed({"status": ["El token fue eliminado o no es valido."]})

        if not token.user.is_active:
            raise AuthenticationFailed({"status": ["Usuario no esta activo"]})

        if not token.user.state:
            raise AuthenticationFailed(
                {"status": ["Su cuenta ha sido desactivada, por favor consulte a su ejecutivo Polipay"]})

        is_expired, token = token_expire_handler(token)

        if is_expired:
            token_expire_user = Token.objects.get(key=token).user
            user = persona.objects.filter(username=token_expire_user)
            user.update(is_active=False, token_device=None, last_login_user=dt.datetime.now())
            raise AuthenticationFailed({"status": ["El token ha expirado"]})

        return token.user, token
