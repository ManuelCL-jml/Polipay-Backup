import datetime as dt
import json
from typing import Dict, Any, ClassVar, NoReturn, Union
from decouple import config

from django.db.transaction import atomic
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response

from MANAGEMENT.notifications.movil.push import pushNotifyAppUser, push_notify_dynamic_token
from apps.notifications.models import notification
from apps.transaction.models import transferencia
from polipaynewConfig.settings import PUB_KEY_MOBILE
from apps.api_dynamic_token.CreateJWT import EncodeJWT
from apps.api_dynamic_token.Credentials import ImportKeysJWE
from apps.api_dynamic_token.exc import TokenAlreadyActive, JwtDynamicTokenException, TokenDoesNotExist
from apps.api_dynamic_token.models import Token_detail, User_token
from apps.api_dynamic_token.api.web.serializers.serializers_dynamic_token import SerializerDynamicToken
from apps.users.models import persona, Access_credentials
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from MANAGEMENT.Standard.errors_responses import MyHttpError
from apps.api_dynamic_token.SymetricKey import (
    EncryptWithAES,
    GenerateCodeCache,
    GenerateCodeAES16Bytes,
    CreateCodeCache)

from polipaynewConfig.settings import PASS_FRONTEND, IV_FRONTEND, PASS_MOBILE, IV_MOBILE


class ValidateTokenDynamic:
    _serializer_class: ClassVar[SerializerDynamicToken] = SerializerDynamicToken

    def __init__(self, token: str, person: persona):
        self.token = token
        self.person = person
        self._validate_token()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "token": self.token,
            "email": self.person.get_username
        }

    def _validate_token(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)


# (ChrGil 2021-12-22) Genera un token dinamico al cliente como metodo de prueba
# (ChrGil 2021-12-22) url_demo: http://127.0.0.1:8000/keys/web/DemDynTok/get/
# class DemoDynamicToken(RetrieveAPIView):
#     def retrieve(self, request, *args, **kwargs):
#         user: persona = request.user
#
#         code_cache = GenerateCodeCache()
#         code_aes = GenerateCodeAES16Bytes()
#         CreateCodeCache(code_cache, user)
#         token = EncryptWithAES(code_cache, code_aes, secret_key=PASS_FRONTEND, iv=IV_FRONTEND)
#
#         succ = MyHtppSuccess(message="Token generado de manera exitosa", extra_data=token.encrypt_mode_cbc)
#         return Response(succ.ok(), status=status.HTTP_200_OK)


# (ChrGil 2022-01-12) Envia notificación a la aplicación movil por medio de FireBase
class SendFireBaseNotification:
    _default_title_notification: ClassVar[str] = "Token generado"
    _default_message_notification: ClassVar[str] = "Se ha establecido un nuevo Token para realizar tus movimientos."

    def __init__(self, owner: persona):
        self._owner = owner
        self._send_notification()

    def _send_notification(self) -> NoReturn:
        push_notify_dynamic_token(
            title=self._default_title_notification,
            body=self._default_message_notification,
            owner=self._owner.get_only_id(),
            message=self._default_message_notification,
            token=self._owner.get_token_device_app,
            number_notification=notification.objects.get_number_notification(self._owner.get_only_id()),
        )


class LoadConfigurationUser:
    expiration_minutes: ClassVar[int] = 3

    def __init__(self, user: persona):
        self._user = user
        _expiration_minutes = self._get_configuration

        if _expiration_minutes:
            self.expiration_minutes = _expiration_minutes.get('time_config')

    @property
    def _get_configuration(self) -> Dict[str, Any]:
        return Token_detail.objects.filter(person_id=self._user.get_only_id()).values('time_config').first()


class EncrypCode:
    code_encryp: ClassVar[str]

    def __init__(self, user: persona, code_cache: GenerateCodeCache, code_aes: GenerateCodeAES16Bytes, condifg: LoadConfigurationUser):
        CreateCodeCache(code_cache, user, condifg.expiration_minutes)
        _code_encryp = EncryptWithAES(code_cache, code_aes, PASS_MOBILE, IV_MOBILE)
        self.code_encryp = _code_encryp.encrypt_mode_cbc


class RegisterUserToken:
    _effective_date: ClassVar[dt.datetime]

    def __init__(self, user: persona, token: EncrypCode, conf: LoadConfigurationUser):
        self._user = user
        self._token = token

        self._effective_date = dt.datetime.now() + dt.timedelta(minutes=conf.expiration_minutes)
        self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "token": self._token.code_encryp,
            "json_content": "null",
            "is_active": True,
            "effective_date": self._effective_date,
            "person_id": self._user,
            "token_related_id": 1,
        }

    def _create(self):
        User_token.objects.create(**self._data)


class ValidateTimeExpire:
    _msg = "Se ha enviado satisfactoriamente tu token de seguridad vigente a tu App Token, por favor consulta tu clave"

    def __init__(self, user: persona):
        self._user = user
        last_token = self._get_last_dynamic_token

        if last_token:
            if last_token.get('effective_date') < dt.datetime.now():
                self._kill_token()

            if last_token.get('effective_date') > dt.datetime.now():
                SendFireBaseNotification(user)
                raise TokenAlreadyActive(self._msg)

    @property
    def _get_last_dynamic_token(self) -> Dict[str, Union[bool, dt.datetime]]:
        return User_token.objects.get_last_dynamic_token(owner=self._user)

    def _kill_token(self) -> NoReturn:
        token = User_token.objects.filter(person_id=self._user).last()
        token.is_active = False
        token.save()


# (ChrGil 2022-01-17) Generar token dinamico
# Endpoint: http://127.0.0.1:8000/keys/web/v3/GenDynTok/get/
class GenerateDynamicToken(RetrieveAPIView):
    def retrieve(self, request, *args, **kwargs):
        user: persona = request.user

        try:
            with atomic():
                ValidateTimeExpire(user)
                cache = GenerateCodeCache()
                aes = GenerateCodeAES16Bytes()

                config = LoadConfigurationUser(user)
                encryp = EncrypCode(user, cache, aes, config)
                RegisterUserToken(user, encryp, config)
                SendFireBaseNotification(user)

        except JwtDynamicTokenException as e:
            err = MyHttpError(message=e.message, real_error=None)
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            err = MyHttpError(message="Error general. No se pudo generar el token", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        msg = "Se ha enviado satisfactoriamente tu nuevo token de seguridad a la App Token, por favor consulta tu clave"
        succ = MyHtppSuccess(message=msg)
        return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)
