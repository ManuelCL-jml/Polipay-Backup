import datetime as dt
from dataclasses import dataclass
from abc import ABC, abstractmethod
from os import remove
from typing import Any, Dict, NoReturn, ClassVar, Union

from django.db.transaction import atomic
from jwcrypto.jwk import JWK
from rest_framework.viewsets import GenericViewSet
from rest_framework.generics import RetrieveAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework import status

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError

from apps.api_dynamic_token.CreateJWT import EncodeJWT
from apps.api_dynamic_token.Credentials import ImportKeysJWE
from apps.api_dynamic_token.exc import TokenDoesNotExist, JwtDynamicTokenException
from apps.users.models import persona, Access_credentials
from apps.api_dynamic_token.models import Token_detail, User_token
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from apps.api_dynamic_token.api.mobile.serializers.serializers_token import SerializerCreateConfiguration


class Configuration(ABC):
    @abstractmethod
    def data(self) -> NoReturn:
        ...

    @abstractmethod
    def add_configuration(self) -> NoReturn:
        ...


@dataclass
class RequestDataTokenConfiguration:
    request_data: Dict[str, Any]

    @property
    def get_expiration_minutes(self) -> int:
        return self.request_data.get('TimeConfig')


class CreateConfiguration(Configuration):
    _serializer_class: ClassVar[SerializerCreateConfiguration] = SerializerCreateConfiguration

    def __init__(self, request_data: RequestDataTokenConfiguration, owner: persona):
        self._request_data = request_data
        self._owner = owner
        self.add_configuration()

    @property
    def data(self) -> NoReturn:
        return {
            "time_config": self._request_data.get_expiration_minutes,
            "person_id_id": self._owner.get_only_id()
        }

    def add_configuration(self) -> NoReturn:
        serializer = self._serializer_class(data=self.data)
        serializer.is_valid(raise_exception=True)
        serializer.create()


class UpdateConfiguration(Configuration):
    _serializer_class: ClassVar[SerializerCreateConfiguration] = SerializerCreateConfiguration

    def __init__(self, request_data: RequestDataTokenConfiguration, owner: persona, token: Dict[str, int]):
        self._request_data = request_data
        self._owner = owner
        self._token_detail_id = token
        self.add_configuration()

    @property
    def data(self) -> NoReturn:
        return {
            "time_config": self._request_data.get_expiration_minutes,
            "person_id_id": self._owner.get_only_id()
        }

    def add_configuration(self) -> NoReturn:
        serializer = self._serializer_class(data=self.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(self._token_detail_id.get('id'))


class CreateOrUpdateToken:
    _create: ClassVar[CreateConfiguration] = CreateConfiguration
    _update: ClassVar[UpdateConfiguration] = UpdateConfiguration

    def __init__(self, request_data: RequestDataTokenConfiguration, user: persona):
        self._user = user
        _token_detail = self.exists_configuration

        if _token_detail is None:
            self._create(request_data, user)

        if _token_detail:
            self._update(request_data, user, _token_detail)

    @property
    def exists_configuration(self) -> Union[Dict[str, int], None]:
        return Token_detail.objects.filter(person_id=self._user.get_only_id()).values('id').first()


# (ChrGil 2022-01-17) Configurar tiempo de expiración de un token
# Endpoint: http://127.0.0.1:8000/keys/mobile/v3/TokCon/update/
class TokenConfiguration(UpdateAPIView):
    def update(self, request, *args, **kwargs):
        try:
            user: persona = request.user

            with atomic():
                request_data = RequestDataTokenConfiguration(request.data)
                CreateOrUpdateToken(request_data, user)

        except ObjectDoesNotExist as e:
            err = MyHttpError(message="Ocurrio un error al actualizar el tiempo de expiración", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except IntegrityError as e:
            err = MyHttpError(message="Ocurrio un error al actualizar el tiempo de expiración", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        else:
            succ = MyHtppSuccess(message="El tiempo de expiración del token se editó correctamente")
            return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


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


class GenerateFilePEM:
    file_name: ClassVar[str]

    def __init__(self, owner: persona):
        self._owner = owner
        self.create_file(self._get_key.get('credential_access'))

    @property
    def _get_key(self) -> Dict[str, str]:
        return Access_credentials.objects.filter(
            person_id=self._owner.get_only_id()).values('credential_access').first()

    def create_file(self, key: str):
        with open(f"TMP/mobile/PubKeyPerson{self._owner.get_only_id()}.pem", "wb") as file:
            file.write(key.encode('utf-8'))
        self.file_name = file.name


class LoadTokenUser:
    minute_expired: ClassVar[dt.datetime]

    def __init__(self, owner: persona):
        self._owner = owner
        iat: dt.datetime = self.get_user_token.get('creation_date')
        exp: dt.datetime = self.get_user_token.get('effective_date')
        minute_expired: dt.timedelta = exp - iat
        self.minute_expired = minute_expired

    @property
    def get_user_token(self) -> Dict[str, dt.datetime]:
        return User_token.objects.filter(
            is_active=True,
            person_id_id=self._owner.get_only_id()
        ).values('effective_date', 'creation_date').last()


class CreateJWT:
    jwt_serialize: ClassVar[str]

    def __init__(self, owner: persona, user_token: LoadTokenUser, generate: GenerateFilePEM):
        self._owner = owner
        _token = self._get_token
        _jwe_pub = self._import_key(generate.file_name)

        jwt = EncodeJWT(_token.get('token'), _jwe_pub, user_token.minute_expired)
        self.jwt_serialize = jwt.serialize_token
        remove(generate.file_name)

    @staticmethod
    def _import_key(file_name: str) -> JWK:
        return ImportKeysJWE(file_name).get_key()

    @property
    def _get_token(self) -> Dict[str, str]:
        return User_token.objects.get_encryption_token(self._owner.get_only_id())


class UpdateUserToken:
    def __init__(self, jwt_token: CreateJWT, owner: persona):
        self._jwt = jwt_token.jwt_serialize
        self._owner = owner
        self._update_token()

    def _update_token(self) -> NoReturn:
        token = User_token.objects.filter(person_id=self._owner.get_only_id()).last()
        token.json_content = self._jwt
        token.save()


class ValidateTimeExpire:
    jwt: ClassVar[Dict[str, str]]
    _create_jwt: ClassVar[CreateJWT] = CreateJWT
    _file_pem: ClassVar[GenerateFilePEM] = GenerateFilePEM

    def __init__(self, user: persona, user_token: LoadTokenUser):
        self._user = user
        last_token = self._get_last_dynamic_token

        if last_token:
            if last_token.get('json_content') == 'null':
                jwt = self._create_jwt(user, user_token, self._file_pem(user))
                UpdateUserToken(jwt, user)
                self._jwt_response(jwt.jwt_serialize)

            if last_token.get('json_content') != "null":
                self._jwt_response(last_token.get('json_content'))

        if not last_token:
            raise TokenDoesNotExist('No cuentas con ningun token activo.')

    @property
    def _get_last_dynamic_token(self) -> Dict[str, Union[bool, dt.datetime, str]]:
        return User_token.objects.get_last_dynamic_token(owner=self._user)

    def _jwt_response(self, jwe: str):
        self.jwt = {
            "json_content": jwe
        }


# (ChrGil 2022-01-18) Regresa una cadena de caracteres que sería el codigo cifrado
# Endpoint: http://127.0.0.1:8000/keys/web/v3/GetDynTok/get/
class GetDynamicToken(RetrieveAPIView):
    def retrieve(self, request, *args, **kwargs):
        try:
            user: persona = request.user
            user_token = LoadTokenUser(user)
            token = ValidateTimeExpire(user, user_token)
        except JwtDynamicTokenException as e:
            err = MyHttpError(message=e.message, real_error=None)
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            message = "No se pudo obtener su token debido a un error inesperado. Comuníquese con su Ejecutivo Polipay"
            err = MyHttpError(message=message, real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(token.jwt, status=status.HTTP_200_OK)
