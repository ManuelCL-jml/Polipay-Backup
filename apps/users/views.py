import datetime
from typing import Dict, Any, ClassVar, Union, NoReturn

from rest_framework.viewsets import GenericViewSet
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status

from django.contrib.auth import logout, login
from django.shortcuts import render
from django.core.cache import cache

from MANAGEMENT.notifications.movil.push import push_notify
from apps.users.exc import NotificationUserNotExists, NotificationUserCodeInvalid, NotificationCodeExpired, \
    NotificationPolipayExceptions
from apps.users.management import get_information_client, get_Object_orList_error, createCodeCache
from apps.users.models import persona, Access_credentials
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.Language.LanguageUnregisteredUser import LanguageUnregisteredUser
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from MANAGEMENT.Users.get_id import get_id
from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.EncryptDecrypt.encdec_nip_cvc_token4dig import encdec_nip_cvc_token4dig
from firebase_admin.exceptions import NotFoundError, InvalidArgumentError, InternalError, UnknownError


class GeneralLoginGenericViewSet(GenericViewSet):
    serializer_class = None
    serializer_class_out = None

    def get_queryset(self, **kwargs):
        return get_Object_orList_error(persona, **kwargs)

    def create(self, request):
        objJson = encdec_nip_cvc_token4dig("1", "BE", str(request.data["password"]))
        RegisterSystemLog(email=request.data["email"], type=4, endpoint=get_info(request),
                          objJsonRequest={"email": request.data["email"], "password": str(objJson["data"])})
        context = {
            'request': request,
            'ip': get_information_client(request)
        }

        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)

        email = serializer.data['email']
        instance = self.get_queryset(email=email)
        cliente = persona.objects.filter(email=email)
        cliente.update(token_device=serializer.data['token_device'], is_active=True)

        login(request, instance)
        serializer = self.serializer_class_out(instance)
        RegisterSystemLog(idPersona=serializer.data["id"], type=1, endpoint=get_info(request),
                          objJsonResponse=serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        RegisterSystemLog(email=request.data["email"], type=4, endpoint=get_info(request),
                          objJsonRequest={"email": request.data["email"]})
        client = persona.objects.filter(email=request.data['email'])
        client.update(is_active=False, last_login_user=datetime.datetime.now())
        # Token.objects.get(user=client[0]).delete()
        logout(request)
        idPersona = get_id(campo="email", valorStr=request.data["email"])
        msg = LanguageRegisteredUser(idPersona, "Log006")
        RegisterSystemLog(email=request.data["email"], type=4, endpoint=get_info(request),
                          objJsonResponse={"status": msg, "code": status.HTTP_200_OK})
        return Response({"status": msg}, status=status.HTTP_200_OK)
        # return Response({'status': 'Su sesión ha sido cerrada exitosamente'}, status=status.HTTP_200_OK)


class PersonInfo:
    person_info: ClassVar[Union[Dict[str, Any], None]]
    code_cache: ClassVar[Union[None, int]]

    def __init__(self, **kwargs):
        self._email = kwargs.get('email', None)
        self._code = kwargs.get('code', None)
        self.person_info = self._get_info_user
        self._raise_notification()
        self.code_cache = self._get_code_cache

        if self.code_cache != self._code:
            raise NotificationCodeExpired('codigo no valido o ya expiro')

    def _raise_notification(self):
        if not self._email:
            raise NotificationUserNotExists('No se encontró a una persona registrada con este correo')

        if not self._code:
            raise NotificationUserCodeInvalid('Codigo no valido')

        if not self.person_info:
            raise NotificationUserNotExists('No se encontró a una persona registrada con este correo')

    @property
    def _get_info_user(self) -> Dict[str, Any]:
        return persona.objects.filter(
            email=self._email
        ).values(
            'id',
            'email',
            'token_device_app_token',
            'token_device'
        ).first()

    @property
    def _get_code_cache(self) -> Union[str, None]:
        return cache.get(self.person_info.get('email'), None)

    def change_data_user(self, **kwargs) -> NoReturn:
        persona.objects.filter(id=self.person_info.get('id')).update(**kwargs)

    def delete_credential_acces_app_token(self):
        access = Access_credentials.objects.filter(person_id=self.person_info.get('id'))

        if len(access) != 0:
            for i in access:
                i.delete()


class SendNotificationAppToken:
    _default_message: ClassVar[str] = 'Se inicio sesión en otro dispositivo'

    def __init__(self, person: Dict[str, Any]):
        self._person = person
        self._send()

    def _send(self):
        push_notify(
            user_id=self._person.get('id'),
            messages=self._default_message,
            registration_token=self._person.get('token_device_app_token')
        )


class SendNotificationWeb:
    _default_message: ClassVar[str] = 'Se inicio sesión en otro dispositivo'

    def __init__(self, person: Dict[str, Any]):
        self._person = person
        self._send()

    def _send(self):
        push_notify(
            user_id=self._person.get('id'),
            messages=self._default_message,
            registration_token=self._person.get('token_device')
        )


class CheckCodeUserAppToken(GenericAPIView):
    """
    End-point general para verificar codigo

    """
    permission_classes = ()
    template_name: ClassVar[str] = 'verify_url.html'
    person: PersonInfo

    def get(self, request):
        try:
            data = {key: value for key, value in self.request.query_params.items()}
            self.person = PersonInfo(**data)
            SendNotificationAppToken(self.person.person_info)
        except (NotFoundError, InvalidArgumentError, InternalError, UnknownError) as e:
            context = {
                "message": "Código Verificado",
                "detail": "Ya puede iniciar sesión en su nuevo dispositivo."
            }
            self.person.change_data_user(token_device_app_token=None)
            self.person.delete_credential_acces_app_token()
            return render(request, template_name=self.template_name, context=context)

        except NotificationPolipayExceptions as e:
            context = {"message": "El código ya ha sido verificado o ya expiro"}
            return render(request, template_name=self.template_name, context=context)

        except ValueError as e:
            context = {
                "message": "Código Verificado",
                "detail": "Ya puede iniciar sesión en su nuevo dispositivo."
            }
            return render(request, template_name=self.template_name, context=context)

        else:
            context = {
                "message": "Código Verificado",
                "detail": "Ya puede iniciar sesión en su nuevo dispositivo."
            }
            self.person.change_data_user(token_device_app_token=None)
            self.person.delete_credential_acces_app_token()
            return render(request, template_name=self.template_name, context=context)


class CheckCodeUserGenericAPIView(GenericAPIView):
    """
    End-point general para verificar codigo

    """
    permission_classes = ()
    template_name: ClassVar[str] = 'verify_url.html'
    person: PersonInfo

    def get(self, request):
        try:
            data = {key: value for key, value in self.request.query_params.items()}
            self.person = PersonInfo(**data)
            SendNotificationWeb(self.person.person_info)
        except (NotFoundError, InvalidArgumentError, InternalError, UnknownError) as e:
            context = {
                "message": "Código Verificado",
                "detail": "Ya puede iniciar sesión en su nuevo dispositivo."
            }
            self.person.change_data_user(token_device=None)
            return render(request, template_name=self.template_name, context=context)

        except NotificationPolipayExceptions as e:
            context = {"message": "El código ya ha sido verificado o ya expiro"}
            return render(request, template_name=self.template_name, context=context)

        except ValueError as e:
            context = {
                "message": "Código Verificado",
                "detail": "Ya puede iniciar sesión en su nuevo dispositivo."
            }
            return render(request, template_name=self.template_name, context=context)

        else:
            context = {
                "message": "Código Verificado",
                "detail": "Ya puede iniciar sesión en su nuevo dispositivo."
            }
            self.person.change_data_user(token_device=None)
            return render(request, template_name=self.template_name, context=context)

        # except exceptions.NotFoundError as e:
        #     return False, 'NotFoundError'
        # except exceptions.InvalidArgumentError as e:
        #     return False, e
        # except exceptions.UnknownError as e:
        #     return False, e

        # user: Dict[str, Any] = persona.objects.filter(email=self.request.query_params['email']).values('id', 'email',
        #                                                                                                'token_device_app_token').first()
        # # user = get_Object_orList_error(persona, email=request.GET.get('email'))
        # print(user.get('id'))
        # if not user:
        #     ...
        #
        # code = cache.get(user.get('email', ''), None)
        #
        # if self.request.query_params['code'] != code:
        #     return render(request, template_name='verify_url.html', context={'detail': 'El codigo ya expiro'})

        # if request.GET.get('code') != code:
        #     return render(request, template_name='verify_url.html', context={'detail': 'El codigo ya expiro'})

        # push_notify(user_id=user.get('id'), messages="Se inicio sesión en otro dispositivo",
        #             registration_token=user.get('token_device_app_token'))

        # if not state and e == 'NotFoundError':
        #     print(user.get('id'))
        #     # self.change_data_user(user.get('id'))
        #     return render(request, template_name='verify_url.html',
        #                   context={'detail': 'Codigo verificado. Ya es posible iniciar sesión.'})
        #
        # if not state:
        #     return render(request, template_name='verify_url.html', context={'detail': e})

        # self.change_data_user(user.get('id'))
        # return render(request, template_name='verify_url.html',
        #               context={'detail': 'Codigo verificado. Ya es posible iniciar sesión.'})


# class CheckCodeUserGenericAPIView(GenericAPIView):
#     """
#     End-point general para verificar codigo
#
#     """
#     permission_classes = ()
#
#     def change_data_user(self, instance, request):
#         instance.ip_address = get_information_client(request)
#         logout(request)
#         instance.token_device = None
#         instance.is_active = False
#         instance.save()
#         return True
#
#     def get(self, request):
#         user = get_Object_orList_error(persona, email=request.GET.get('email'))
#         code = cache.get(user.email, None)
#
#         if request.GET.get('code') != code:
#             return render(request, template_name='verify_url.html', context={'detail': 'El codigo ya expiro'})
#
#         state, e = push_notify(user_id=user.id, messages="Se inicio sesión en otro dispositivo",
#                                registration_token=user.token_device)
#
#         if not state and e == 'NotFoundError':
#             self.change_data_user(user, request)
#             return render(request, template_name='verify_url.html',
#                           context={'detail': 'Codigo verificado. Ya es posible iniciar sesión.'})
#
#         if not state:
#             return render(request, template_name='verify_url.html', context={'detail': e})
#
#         self.change_data_user(user, request)
#         return render(request, template_name='verify_url.html',
#                       context={'detail': 'Codigo verificado. Ya es posible iniciar sesión.'})
#

class GeneralEditPassword(GenericViewSet):
    serializer_class = None

    def get_queryset(self, *args, **kwargs):
        return get_Object_orList_error(persona, *args, **kwargs)

    def create(self, request):
        client = self.get_queryset(email=request.data['email'])
        createCodeCache(client)
        return Response({'status': 'Hemos enviado a su email un codigo de verificación'}, status=status.HTTP_200_OK)

    def put(self, request):
        user = self.get_queryset(username=request.user)
        serializer = self.serializer_class(data=request.data, context={'user': user})
        serializer.is_valid(raise_exception=True)
        serializer.update(user)
        user.save()
        return Response({'status': 'Se ha actualizado tu contraseña'}, status=status.HTTP_200_OK)
