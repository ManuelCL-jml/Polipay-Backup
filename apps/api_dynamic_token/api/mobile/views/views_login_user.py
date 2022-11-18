import datetime as dt
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Dict, Any, ClassVar, NoReturn, List

from rest_framework.generics import CreateAPIView, UpdateAPIView, DestroyAPIView
from django.contrib.auth import login, logout
from rest_framework.response import Response
from rest_framework import status

from apps.api_dynamic_token.api.mobile.serializers.serializers_login_user import SerializerLogin, SerializerLogInUserOut
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from apps.transaction.api.web.views.views_adelante_zapopan import SendMail
from apps.transaction.messages import message_email
from apps.users.models import persona, Access_credentials
from apps.api_dynamic_token.models import User_token


class Login(ABC):
    instance_user: ClassVar[persona]

    @abstractmethod
    def data(self) -> NoReturn:
        ...

    @abstractmethod
    def context(self) -> NoReturn:
        ...

    @abstractmethod
    def login_user(self) -> NoReturn:
        ...


@dataclass
class RequestDataLogin:
    _request_data: Dict[str, Any]

    @property
    def get_email(self) -> str:
        return self._request_data.get('email')

    @property
    def get_password(self) -> str:
        return self._request_data.get('password')

    @property
    def get_token_device(self) -> str:
        return self._request_data.get('token_device')

    @property
    def get_access_key(self) -> str:
        return self._request_data.get('access_key')


class LoginUser(Login):
    _serializer_class: ClassVar[SerializerLogin] = SerializerLogin
    pub_key: ClassVar[str]

    def __init__(self, request_data: RequestDataLogin, request):
        self._request_data = request_data
        self._request = request
        self.login_user()

    @property
    def data(self) -> Dict[str, Any]:
        return {
            "email": self._request_data.get_email,
            "password": self._request_data.get_password,
            "token_device": self._request_data.get_token_device,
            "access_key": self._request_data.get_access_key
        }

    @property
    def context(self) -> Dict[str, Any]:
        return {
            "request": self._request
        }

    def login_user(self) -> NoReturn:
        serializer = self._serializer_class(data=self.data, context=self.context)
        serializer.is_valid(raise_exception=True)
        serializer.save_token_device()
        self.pub_key = serializer.data.get('access_key')
        self.instance_user = serializer.get_instance_user
        login(self._request, self.instance_user)


# (ChrGil 2022-02-04) Valida que si el cliente cambia su llave pública, su anterior llave
# (ChrGil 2022-02-04) pasa a ser una llave expirada, por lo que se elimina y se guarda la nueva llave
class CreateOrDeletePublicKey:
    def __init__(self, owner: LoginUser):
        self._owner_id = owner.instance_user.get_only_id()
        self._pub_key = owner.pub_key

        if not self._validate_exists_key:
            for i in self._get_all_keys:
                i.delete()

            Access_credentials.objects.create(self._owner_id, self._pub_key)

    @property
    def _get_all_keys(self) -> List[Access_credentials]:
        return Access_credentials.objects.all_keys(owner=self._owner_id)

    @property
    def _validate_exists_key(self) -> bool:
        return Access_credentials.objects.exists_key(self._owner_id, self._pub_key)


@dataclass
class UserOutData:
    _log_in: Login
    _serializer_class: ClassVar[SerializerLogInUserOut] = SerializerLogInUserOut

    @property
    def out(self) -> Dict[str, Any]:
        serialier = self._serializer_class(instance=self._log_in.instance_user)
        return serialier.data


# (ChrGil 2022-01-17) Inicio de sesión para la app (Polipay Token)
# Endpoint: http://127.0.0.1:8000/keys/mobile/v3/LogIn/create/
class EndpointLoginUser(CreateAPIView):
    permission_classes = ()

    def create(self, request, *args, **kwargs):
        request_data = RequestDataLogin(request.data)
        user = LoginUser(request_data, request)
        CreateOrDeletePublicKey(user)
        return Response(UserOutData(user).out, status=status.HTTP_200_OK)


# (ChrGil 2022-01-17) Inicio de sesión para la app (Polipay Token)
# Endpoint: http://127.0.0.1:8000/keys/mobile/v3/LogOut/update/
class EndpointLogoutUser(UpdateAPIView):
    permission_classes = ()

    def update(self, request, *args, **kwargs):
        user_id: int = request.user.get_only_id()
        persona.objects.filter(id=user_id).update(is_active=True, last_login_user=dt.datetime.now())
        logout(request)

        scc = MyHtppSuccess(message="Nos vemos!")
        return Response(scc.standard_success_responses(), status=status.HTTP_200_OK)


# (ChrGil 2022-04-08) Eliminar todos los token, si el cliente cambia de usuario
# (ChrGil 2022-04-08) DELETE http://127.0.0.1:8000/keys/mobile/v3/DelAllTok/delete/?id=6
class DeleteAllOldToken(DestroyAPIView):
    permission_classes = ()

    def delete(self, request, *args, **kwargs):
        person_id: int = self.request.query_params['id']
        token = User_token.objects.filter(person_id_id=person_id)

        if token:
            for i in token:
                i.delete()

        return Response(status=status.HTTP_200_OK)
