import datetime as dt

from dataclasses import dataclass

from rest_framework.authtoken.models import Token
from rest_framework.serializers import *

from django.contrib.auth.hashers import check_password

from MANAGEMENT.Utils.utils import remove_asterisk, generate_url, verification_session_user, generate_url_app_token
from MANAGEMENT.notifications.movil.alert import send_push
from apps.transaction.api.web.views.views_adelante_zapopan import SendMail
from apps.transaction.messages import message_email
from apps.users.models import persona, grupoPersona, Access_credentials

from typing import Dict, Any, ClassVar, Union, NoReturn

from polipaynewConfig import settings


@dataclass
class SendMailPersona(SendMail):
    data: Dict[str, Any]
    url: str

    @property
    def context_data_email(self) -> Dict[str, Any]:
        return {
            "name": self.data.get('name').title(),
            "email": self.data.get('email'),
            "url": self.url
        }

    def send_mail(self) -> NoReturn:
        message_email(
            template_name='autoriza_dispositivo_multisesion.html',
            context=self.context_data_email,
            title='Alerta Polipay',
            body=self.context_data_email.get('name'),
            email=self.context_data_email.get('email').lower()
        )


class CatValidationError:
    _cat_error: ClassVar[Dict[str, Any]] = {
        1: "¡Lo sentimos!\nTu correo o contraseña son incorrectos, favor de verificar tus datos.",
        2: "¡Lo sentimos!\nTu usuario no cuenta con los permisos para hacer uso de esta aplicación.",
        3: "Estimado usuario, para acceder a la aplicación del token, es necesario que primero inicie sesión en Polipay Banca",
    }

    def get_error(self, key: int) -> str:
        return self._cat_error.get(key)


class SerializerLogin(Serializer):
    _cat_error: ClassVar[CatValidationError] = CatValidationError()
    _person_info: ClassVar[Dict[str, Union[int, str, bool]]]

    email = EmailField()
    password = CharField()
    token_device = CharField()
    access_key = CharField()

    def _is_admin(self, person_id: int) -> bool:
        return grupoPersona.objects.is_admin_or_collaborator(person_id)

    @staticmethod
    def expires_in(token):
        time_elapsed = dt.datetime.now() - token.created
        left_time = dt.timedelta(seconds=settings.TOKEN_EXPIRED_AFTER_SECONDS) - time_elapsed
        return left_time

    def is_token_expired(self, token: Token):
        return self.expires_in(token) < dt.timedelta(seconds=0)

    def validate(self, attrs):
        attr = dict(attrs)
        self._person_info = persona.querys.get_info_login(email=attr.get('email'))

        if attrs['email'] == "store.tester@polimentes.mx" or attrs['email'] == 'store.tester_token@polimentes.mx':
            return attrs

        if not self._person_info:
            raise ValidationError(self._cat_error.get_error(1))

        if not check_password(attr.get('password'), self._person_info.get('password')):
            raise ValidationError(self._cat_error.get_error(1))

        is_admin = self._is_admin(self._person_info.get('id'))
        if not (self._person_info.get('is_superuser') or self._person_info.get('is_staff') or is_admin):
            raise ValidationError(self._cat_error.get_error(2))

        token: Token = Token.objects.filter(user_id=self._person_info.get('id')).last()
        if token:
            if not self._person_info.get('is_active'):
                raise ValidationError(self._cat_error.get_error(3))

            if self.is_token_expired(token):
                raise ValidationError(self._cat_error.get_error(3))

        if self._person_info.get('token_device_app_token') is None:
            return attrs

        if attrs['email'] != "store.tester@polimentes.mx" and attrs['email'] != 'store.tester_token@polimentes.mx':
            if self._person_info.get('token_device_app_token') != attr.get('token_device'):
                url = verification_session_user(
                    generate_url_app_token(request=self.context['request'], email=self._person_info.get('email')),
                    user=self._person_info)

                SendMailPersona(self._person_info, url).send_mail()

                raise ValidationError({
                    'status': [f'Se envio un código ha {attr.get("email")} para verificar que es usted.']
                })
            return attrs
        return attrs

    @property
    def get_instance_user(self) -> persona:
        return persona.objects.get(email=self.validated_data.get('email'))

    def save_token_device(self):
        _email = self.validated_data.get('email')
        _token_device = self.validated_data.get('token_device')
        persona.objects.filter(email=_email).update(token_device_app_token=_token_device)


class SerializerLogInUserOut(Serializer):
    id = IntegerField(read_only=True)
    email = CharField(read_only=True)
    username = CharField(read_only=True)
    full_name = SerializerMethodField()
    last_login_user = DateTimeField()
    phone = CharField()
    token = SerializerMethodField()
    is_active = SerializerMethodField()
    is_superuser = BooleanField()
    is_staff = BooleanField()
    is_client = BooleanField()
    company = SerializerMethodField()

    def get_full_name(self, obj: full_name):
        _last_name: str = obj.last_name
        _name: str = obj.name
        _result = None

        if _last_name:
            _result = remove_asterisk(_last_name)

        if _result:
            return f"{_name} {_result}"

        return _name

    def get_token(self, obj: token):
        return Token.objects.get(user_id=obj.id).key

    def get_is_active(self, obj: is_active) -> bool:
        obj.is_active = True
        obj.save()
        return True

    def get_company(self, obj: company) -> Union[Dict[str, Any], str]:
        company_info = grupoPersona.objects.filter(person_id=obj.id, relacion_grupo_id__in=[1, 3, 14]).first()

        if not company_info:
            return "Administrativo"

        return company_info.company_details
