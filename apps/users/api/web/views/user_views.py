from dataclasses import field
from django.contrib.auth import login, logout
from django.db.models import FilteredRelation
from django.shortcuts import get_object_or_404

from MANAGEMENT.notifications.movil.push import push_notify, push_notify_logout
from apps import permision
from polipaynewConfig.exceptions import get_Object_Or_Error

from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status

from polipaynewConfig.exceptions import *
from apps.users.models import *
from apps.users.api.movil.serializers.user_serializer import *
from apps.users.api.web.serializers.users_serializers import *
from apps.users.views import GeneralLoginGenericViewSet, GeneralEditPassword
from apps.users.management import *


class ChangePassword(GeneralEditPassword):
    """ Cambiar contraseña """

    serializer_class = ChangePasswordSerializerIn


class ResendEmail(GeneralEditPassword):
    """ Reenviar email """

    permission_classes = ()


class RecoverPassword(GeneralEditPassword):
    """ Recuperar contraseña """

    serializer_class = RecoverPasswordSerializerIn
    permission_classes = ()

    def put(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.get_queryset(email=request.data['email'])
        serializer.update(user)
        send_change_password(user)

        return Response({'status': 'Felicidades, tu nueva contraseña se ha guardado exitosamente.'},
                        status=status.HTTP_200_OK)


class SendNotificationAppTokenLogout:
    _default_message: ClassVar[str] = 'Su sesión ha finalizado'

    def __init__(self, person: persona):
        self._person = person
        self._send()

    def _send(self):
        push_notify_logout(
            user_id=self._person.get_only_id(),
            messages=self._default_message,
            registration_token=self._person.get_token_device_app
        )


class Login(GeneralLoginGenericViewSet):
    """ Enviar codigo de verificación antes de iniciar sesión """

    serializer_class = SerializerLoginClientIn
    permission_classes = ()

    def create(self, request):
        context = {'request': request, 'ip': get_information_client(request)}
        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)

        instance = self.get_queryset(email=serializer.data['email'])
        client = persona.objects.filter(email=serializer.data['email'])
        client.update(token_device=serializer.data['token_device'])
        createCodeCache(instance)

        return Response({'status': 'Hemos enviado a su email un codigo de verificación'}, status=status.HTTP_200_OK)

    def put(self, request):
        client = persona.objects.filter(email=request.data['email']).first()
        if client:
            client.is_active = False
            client.last_login_user = datetime.datetime.now()
            client.token_device = None
            client.save()

            # Envia notificación a la app del token si el cliente de la banca cierra sesión

            try:
                SendNotificationAppTokenLogout(client)
            except Exception as e:
                logout(request)
                return Response({'status': 'Su sesión ha sido cerrada exitosamente'}, status=status.HTTP_200_OK)

        logout(request)
        return Response({'status': 'Su sesión ha sido cerrada exitosamente'}, status=status.HTTP_200_OK)


class LoginCheckCodeClient(GeneralLoginGenericViewSet):
    """ Verificar codigo e iniciar sesión """

    serializer_class = CheckCodeLogin
    serializer_class_out = SerializerLoginClientOut
    permission_classes = ()

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = self.get_queryset(email=request.data['email'])
        login(request, client)

        client.is_active = True
        client.save()

        serializer = self.serializer_class_out(client)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChangePasswordNew(GenericViewSet):
    """ Cambiar contraseña cuando es nuevo """

    serializer_class = SerializerNewPasswordEditIn
    permission_classes = ()

    def create(self):
        pass

    def put(self, request):
        pk_user = self.request.query_params["id"]
        if pk_user:
            instance = get_Object_orList_error(persona, id=pk_user)
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid(raise_exception=True):
                if serializer.update(instance):
                    return Response({"status": "Contraseña actualizada"}, status=status.HTTP_200_OK)
                else:
                    return Response({"status": "Algo ocurrio"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"status": "Se esperaba id del usuario"}, status=status.HTTP_400_BAD_REQUEST)


class ListUser(GenericViewSet):
    serializer_class = serializerListUser
    permission_classes = ()

    def list(self, request):
        try:
            segurity = self.request.query_params["admin"]
            if segurity == '123':
                # queryUser = persona.objects.order_by('-date_joined').filter(state=True)
                c = cuenta.objects.annotate(
                    persona=FilteredRelation(
                        "persona_cuenta",
                        condition=Q(persona_cuenta__is_superuser=False) & Q(persona_cuenta__is_staff=False) & Q(
                            persona_cuenta__state=True)
                    ),
                ).filter(persona__tipo_persona_id=2).exclude(cuentaclave__iendswith='X').values(
                    'persona_cuenta_id',
                    'persona_cuenta__is_superuser'
                )
                l = [persona.objects.get(id=i['persona_cuenta_id']).get_persona_wallet() for i in c]
                # serializer = self.serializer_class(queryUser, many=True)
                return Response(l, status=status.HTTP_200_OK)
            else:
                return Response({"status": "No tienes acceso"}, status=status.HTTP_400_BAD_REQUEST)
        except:
            pk_user = self.request.query_params["id"]
            if get_Object_orList_error(persona, id=pk_user, state=True):
                queryAccount = cuenta.objects.filter(persona_cuenta_id=pk_user)
                datos = []
                for data in queryAccount:
                    queryCard = tarjeta.objects.filter(cuenta_id=data.id)
                    for datosCard in queryCard:
                        datos.append(datosCard)
                serializer = serializerListCard(datos, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)


class EditAccountsUser(GenericViewSet):
    serializer_class = serializerAccountsUser
    serializer_class_update = serializerUpdateAccount
    permission_classes = ()

    def list(self, request):
        try:
            pk_user = self.request.query_params["id"]
            queryUser = cuenta.objects.filter(persona_cuenta_id=pk_user)
            serializer = self.serializer_class(queryUser, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response({"status": "Se esperaba una id de usuario"}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        try:
            pk_account = self.request.query_params["id"]
            instance = get_Object_orList_error(cuenta, id=pk_account)
            serializer = self.serializer_class_update(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.update_account(instance)
                return Response({"status": "Cuenta actualizada"}, status=status.HTTP_200_OK)
        except:
            return Response({"status": "Se esperaba una id de cuenta"}, status=status.HTTP_400_BAD_REQUEST)


class EnviarCodigoPorSMS(GenericViewSet):
    serializer_class = None
    permission_classes = ()

    def create(self, request):
        instance = get_Object_orList_error(persona, email=request.data["email"])
        createCodeSMSCache(instance)
        mensaje, data, field = "Se envio un codigo de verificacion por SMS", instance.phone, "Null"
        respuesta = MessageOK(mensaje, data, field)
        return Response(respuesta, status=status.HTTP_200_OK)


"""class CompararCodigo(GenericViewSet):
    serializer_class = CheckCode
    permission_classes = ()

    def create(self, request):
        serializers = self.serializer_class(data=request.data)
        if serializers.is_valid(raise_exception=True):
            mensaje,data,field = "El código fue verificado exitosamente","Null","Null"
            respuesta = MessageOK(mensaje, data, field)
            return Response(respuesta,status=status.HTTP_200_OK) """


class SendCodeCall(GenericViewSet):
    serializer_class = None
    permission_classes = ()

    def create(self, request):
        instance = GetObjectOrError(persona, email=request.data["email"])
        createCodeCallCache(instance)
        mensaje, data, field = "Se realizara la llamada", "Null", "Null"
        respuesta = MessageOK(mensaje, data, field)
        return Response(respuesta, status=status.HTTP_200_OK)
