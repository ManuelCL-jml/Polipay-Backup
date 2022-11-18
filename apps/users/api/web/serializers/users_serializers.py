from django.core.cache import cache
from django.db.models import Q
from django.core.files import File

from rest_framework.authtoken.models import Token
from rest_framework.serializers import *

from MANAGEMENT.Utils.utils import get_id_cuenta_eje_adelante_zapopan, get_data_empresa_adelante_zapopan, \
    remove_asterisk
from apps.commissions.models import Commission
from apps.users.management import *
from apps.permision.manager import *
from MANAGEMENT.notifications.web.test import send_push
from apps.users.models import persona, t_persona, grupoPersona, trelacion, documentos, cuenta, Comisiones
from apps.solicitudes.api.web.serializers.centro_costos_serializers import SerializerDocumentsOut


class SerializerTipoPersona(Serializer):
    """
    Serializador de entrada para la creación de tipo_persona

    """

    class Meta:
        model = t_persona
        fields = ['tPersona']


class SerializerLoginClientIn(Serializer):
    email = EmailField()
    password = CharField(write_only=True)
    token_device = CharField(max_length=255, allow_null=False, allow_blank=False)

    def validate(self, attrs):
        client = get_Object_orList_error(persona, email=attrs['email'])
        person_group = grupoPersona.objects.filter(person_id=client.id, relacion_grupo_id__in=[6,9])

        if not client.check_password(attrs['password']):
            raise ValidationError({'status': ['Credenciales incorrectas']})

        if not client.state:
            raise ValidationError(
                {'status': ['Estimado cliente su cuenta ha sido desactivada, por favor contacte a su ejecutivo Polipay']})

        if person_group:
            raise ValidationError({'status': ['Estimado usuario: '
                                          'No podemos iniciar sesion con su cuenta en Banca Polipay, este servicio no esta disponible. '
                                          'Para un mejor manejo de su cuenta por favor acceda a su aplicación móvil Polipay']})

        # if is_admin_or_collaborator(client, grupoPersona) != 5:
        #     raise ValidationError({'status': ['Su documentación personal no ha sido autorizada.']})

        if client.token_device is None:
            return attrs

        if client.token_device != attrs['token_device']:
            state, e = send_push('Se esta intentando iniciar sesión en otro equipo. ¿Fuiste tu?', client.token_device)

            verification_session_user(generate_url(self.context['request'], client.email), client)
            raise ValidationError({
                'status': [f'Se envio un codigo ha {client.email} para verificar que es usted.']
            })

        return attrs


class GetInfoCliente:
    info_cuenta_eje: ClassVar[Dict[str, Any]]

    def __init__(self, person: persona):
        self._person = person
        self._cuenta_eje_id = self._get_cuenta_eje
        self.info_cuenta_eje = self.render_json

    @property
    def _get_cuenta_eje(self) -> int:
        return get_id_cuenta_eje(admin_id=self._person.get_only_id())

    @property
    def _get_cost_center(self) -> List[int]:
        return grupoPersona.objects.filter(
            person_id=self._person.get_only_id(),
            relacion_grupo_id__in=[5, 8]
        ).values_list('empresa_id', flat=True)

    @property
    def _get_account_cost_center(self) -> List[Dict[str, Any]]:
        return cuenta.objects.filter(
            persona_cuenta_id__in=self._get_cost_center
        ).values('persona_cuenta_id', 'persona_cuenta__name', 'cuenta', 'cuentaclave', 'is_active', 'monto')

    @property
    def _get_info_cuenta_eje(self) -> Dict[str, Any]:
        return cuenta.objects.filter(persona_cuenta_id=self._cuenta_eje_id).values(
            'id',
            'monto',
            'cuenta',
            'is_active',
            'cuentaclave',
            'persona_cuenta_id',
            'persona_cuenta__name',
            #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
            'persona_cuenta__name_stp',
            'persona_cuenta__state',
            'persona_cuenta__is_active',
        ).first()

    @property
    def _get_comission_info(self) -> List[Dict[str, Any]]:
        return Commission.objects.select_related('person_debtor', 'person_payer', 'commission_rel').filter(
            Q(person_payer_id=self._cuenta_eje_id) | Q(person_debtor_id=self._cuenta_eje_id)
        ).values(
            'commission_rel__servicio__product_id',
            'commission_rel__servicio__service__nombre',
            'commission_rel__percent',
            'commission_rel__amount',
            'commission_rel__type',
        )

    @staticmethod
    def render_json_comission(**kwargs):
        type_comission = kwargs.pop('commission_rel__type')

        return {
            "id": kwargs.pop('commission_rel__servicio__product_id'),
            "producto": kwargs.pop('commission_rel__servicio__service__nombre'),
            "Porcentaje": float(kwargs.pop('commission_rel__percent')) * 100,
            "MontoFijo": float(kwargs.pop('commission_rel__amount')),
            "Comision": True if type_comission == 1 else False
        }

    @staticmethod
    def render_json_cuenta(**kwargs):
        return {
            "id": kwargs.get('id'),
            "cuenta": kwargs.get('cuenta'),
            "cuentaclabe": kwargs.get('cuentaclave'),
            "is_active": kwargs.get('is_active'),
            "monto": round(kwargs.get('monto'), 2)
        }

    @staticmethod
    def render_json_cuenta_eje(**kwargs):
        return {
            "id": kwargs.get('persona_cuenta_id'),
            "name": kwargs.get('persona_cuenta__name'),
            #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
            "name_stp": kwargs.get('persona_cuenta__name_stp'),
            "state": kwargs.get('persona_cuenta__state'),
            "is_active": kwargs.get('persona_cuenta__is_active'),
        }

    @property
    def render_json(self) -> Dict[str, Any]:
        return {
            "cuenta_eje": self.render_json_cuenta_eje(**self._get_info_cuenta_eje),
            "cuenta": self.render_json_cuenta(**self._get_info_cuenta_eje),
            "commissions": [self.render_json_comission(**comission) for comission in self._get_comission_info],
            "centro_costos": self._get_account_cost_center
        }


class SerializerLoginClientOut(Serializer):
    id = IntegerField()
    name = SerializerMethodField()
    email = EmailField()
    last_login_user = DateTimeField()
    cuenta_id = SerializerMethodField()
    token = SerializerMethodField()
    token_device = CharField()
    is_superuser = BooleanField()
    is_staff = BooleanField()
    is_new = BooleanField()
    tipo_persona_id = IntegerField()
    empresa = SerializerMethodField()
    permisos = SerializerMethodField()
    razon_social_brigadista = SerializerMethodField()
    user_type = SerializerMethodField()
    name_stp = SerializerMethodField()

    def get_name(self, obj: name):
        _last_name: str = obj.last_name
        _name: str = obj.name
        _result = None

        if _last_name:
            _result = remove_asterisk(_last_name)

        if _result:
            return f"{_name} {_result}"

        return _name

    def get_token(self, obj: token):
        return Token.objects.filter(user_id=obj.id).values_list('key', flat=True)[0]

    def get_cuenta_id(self, obj: cuenta_id):
        try:
            return get_id_cuenta_eje(admin_id=obj.id)
        except Exception as e:
            return None

    def get_empresa(self, obj: empresa):
        try:
            info = GetInfoCliente(obj)
            return info.info_cuenta_eje
        except Exception as e:
            return None

    def get_permisos(self, obj: permisos):
        pk = obj.id
        permiso = ListPermission(pk)
        return permiso

    def get_razon_social_brigadista(self, obj: razon_social_brigadista):
        try:
            return get_data_empresa_adelante_zapopan(obj.id)
        except Exception as e:
            return None

    # (ChrGil 2022-02-21) Regresa que tipo de persona es, si es admin o colaborador
    def get_user_type(self, obj: user_type):
        person: Dict[str, Any] = grupoPersona.objects.filter(person_id=obj.id).values('relacion_grupo_id').first()
        if person:
            return person.get('relacion_grupo_id')
        return None

    # (AAF 2022-06-10) Regresa el campo name_stp, alias para transacciones por STP
    def get_name_stp(self, obj: name_stp):
        name_stp = obj.name_stp
        return name_stp

class CheckCodeLogin(Serializer):
    email = EmailField()
    code = CharField()

    def validate(self, attrs):
        client = get_Object_orList_error(persona, email=attrs['email'])

        # (ChrGil 2022-01-03) Se comenta codigo
        # if client.is_active:
        #     raise ValidationError({'status': ['No es posible iniciar sesión, cierre su sesión anterior']})

        if not client.state:
            raise ValidationError({'status': ['Ya no es posible acceder a esta cuenta']})

        if attrs['code'] != cache.get(client.email, None):
            raise ValidationError({'status': ['Codigo no valido o expirado']})

        create_or_delete_token(Token, client)
        return attrs


class ChangePasswordSerializerIn(Serializer):
    current_password = CharField()
    new_password = CharField()
    confirm_password = CharField()

    # token_security = IntegerField()

    def validate(self, attrs):
        client = get_Object_orList_error(persona, username=self.context['user'])

        if not client.check_password(attrs['current_password']):
            raise ValidationError({'status': ['Contraseña incorrecta']})

        if attrs['new_password'] != attrs['confirm_password']:
            raise ValidationError({'status': ['Las contraseñas no coinciden']})

        return attrs

    def update(self, instance, *args, **kwargs):
        instance.set_password(self.validated_data.get("new_password"))
        instance.save()
        return instance


class RecoverPasswordSerializerIn(Serializer):
    email = EmailField()
    new_password = CharField()
    confirm_password = CharField()
    code = CharField()

    def validate(self, attrs):
        instance = persona.objects.filter(email=attrs['email']).first()

        if instance is None:
            raise ValidationError({'status': [
                'No encontramos un usuario asociado a este correo electronico. Verifica la información y vuelve a intentar']})

        if attrs['new_password'] != attrs['confirm_password']:
            raise ValidationError({'status': ['Las contraseñas no coinciden']})

        if attrs['code'] != cache.get(instance.email, None):
            raise ValidationError({'status': ['Codigo no valido o expirado']})

        if instance.is_new:
            password = 'Temporal123.$'
            instance.password = 'Temporal123.$'
            instance.set_password(instance.password)
            instance.save()

            send_mail_superuser(instance, password)
            raise ValidationError({'status': [
                'Para poder cambiar tu contraseña, necesitas iniciar sesión por primera vez. Hemos enviado de nuevo la carta de bienvenida a tu correo electrónico con tus datos de acceso']})

        return attrs

    def update(self, instance, *args, **kwargs):
        instance.set_password(self.validated_data.get("new_password"))
        instance.save()
        return instance


class SerializerNewPasswordEditIn(Serializer):
    password = CharField()
    passwordConfirm = CharField()

    def update(self, instance, **kwargs):
        if instance.is_new:
            if self.validated_data.get("passwordConfirm") == self.validated_data.get("password"):
                instance.set_password(self.validated_data.get("password"))
                instance.is_new = False
                instance.save()
                return True
            else:
                raise ValidationError("Las contraseñas no coinciden")
        else:
            return False


########### personal externo ###########3


class SerializerEditarPersonalExternoIn(Serializer):
    id = ReadOnlyField()
    name = CharField()
    last_name = CharField()
    rfc = CharField()
    email = CharField()

    def update_personal_externo(self, instance, file):
        instance.name = self.validated_data.get("name")
        instance.last_name = self.validated_data.get("last_name")
        instance.email = self.validated_data.get("email")
        instance.rfc = self.validated_data.get("name")
        instance.save()
        create_pdf_data(file)
        actualizarDocumento(instance)
        return instance


class SerializerPersonalExternoIn(Serializer):
    name = CharField()
    last_name = CharField()
    rfc = CharField()
    email = CharField()
    fecha_nacimiento = DateField()
    motivo = CharField(allow_blank=True, allow_null=True)

    def validate_email(self, data):
        emails = persona.objects.filter(email=data)
        if len(emails) != 0:
            raise ValidationError("Email ya registrado")
        else:
            return data

    def create_personalExterno(self, file, pk_user):
        name = self.validated_data.get("name")
        last_name = self.validated_data.get("last_name")
        motivo = "Descripcion de Actividades: " + self.validated_data.get("motivo")

        if file != None:
            username = GenerarUsername(name, last_name)
            instance = persona.objects.create(
                username=username,
                motivo=motivo,
                name=name,
                last_name=last_name,
                rfc=self.validated_data.get("rfc"),
                fecha_nacimiento=self.validated_data.get("fecha_nacimiento"),
                email=self.validated_data.get("email"))

            create_pdf_data(file)
            SubirDocumento(instance)
            PersonaExternaGrupoPersona(pk_user, instance)
            Cuenta = OrderCuenta(instance)
        return Cuenta


class EliminarPersonaExternaIn(Serializer):
    id = ReadOnlyField()
    motivo = CharField(allow_null=False, allow_blank=False)

    def Eliminar_persona_externa(self, instance):
        documento = documentos.objects.filter(person_id=instance.id)
        for i in documento:
            i.historial = False
            i.save()
        cuentas = cuenta.objects.filter(persona_cuenta_id=instance.id)
        for i in cuentas:
            i.is_active = False
            i.save()
        instance.motivo = str(instance.motivo) + " Motivo: " + str(self.validated_data.get("motivo"))
        instance.save()
        return


class list(Serializer):
    id = ReadOnlyField()
    name = CharField()
    last_name = CharField()
    rfc = CharField()
    email = CharField()
    fecha_nacimiento = DateField()
    documento = SerializerMethodField()

    def get_documento(self, obj: documento):
        documents = documentos.objects.filter(person_id=obj.id, historial=True)
        return listD(documents, many=True).data


class listD(Serializer):
    id = ReadOnlyField()
    documento = FileField()
    person_id = ReadOnlyField()

    def update_personalExterna(self, instance):
        instance.name = self.validated_data.get("name", instance.name)
        instance.last_name = self.validated_data.get("last_name", instance.last_name)
        instance.rfc = self.validated_data.get("rfc", instance.rfc)
        instance.email = self.validated_data.get("email", instance.email)
        instance.save()
        return
