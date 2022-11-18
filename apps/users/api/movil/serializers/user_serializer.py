from datetime import datetime
from typing import Any, Dict, List, ClassVar, Union

from django.core.files import File
from django.core.cache import cache
from django.db.models import Q

from requests import request
from rest_framework.authtoken.models import Token
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField

from MANAGEMENT.notifications.movil.alert import send_push
from apps.commissions.models import Commission
from apps.permision.manager import ListPermission
from .account_serializer import serializerCuentaOutUser
from apps.users.models import persona, t_persona, cuenta, tarjeta, grupoPersona
from apps.users.management import get_Object_orList_error, verification_session_user, \
    generate_url, filter_object_if_exist
from MANAGEMENT.EncryptDecrypt.encdec_nip_cvc_token4dig import encdec_nip_cvc_token4dig
from apps.productos.models import producto
from apps.languages.models import Cat_languages, Language_Person
from MANAGEMENT.Language.LanguageUnregisteredUser import LanguageUnregisteredUser
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog

from polipaynewConfig.inntec import change_status

# -------------------------------------------------------------------------------------


class serializerUserWalletIn(serializers.Serializer):
    name				= serializers.CharField()
    email				= serializers.CharField()
    password			= serializers.CharField()
    fecha_nacimiento	= serializers.DateField()
    phone				= serializers.CharField()
    token				= serializers.CharField()
    tipo_persona		= serializers.IntegerField()
    last_name			= serializers.CharField()

    def validate(self, attrs):
        query			= persona.objects.filter(email=str(attrs['email']).lower())
        query_tpersona	= t_persona.objects.filter(id=attrs['tipo_persona'])

        if len(query) != 0:
            msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Reg001BE")
            #raise serializers.ValidationError({"status": "Correo ya ha sido registrado"})
            raise serializers.ValidationError({"status": msg})
        if len(query_tpersona) == 0:
            msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Reg002BE")
            #raise serializers.ValidationError({"status": "Tipo de persona no encontrada"})
            raise serializers.ValidationError({"status": msg})
        else:
            return attrs

    def save(self):
        kward			= self.validated_data
        kward["email"]  = str(kward["email"]).lower()
        # Cifrado
        objJson			= encdec_nip_cvc_token4dig("1", "BE", self.data["token"])
        kward["token"]	= objJson["data"]
        instance		= persona.objects.create_client(
            **kward,
            ip_address=self.context['ip']
        )
        return instance


# -------------------------------------------------------------------------------------

class serializerPutUserWalletChangeStatusIn(serializers.Serializer):
    status = serializers.BooleanField()


# -------------------------------------------------------------------------------------

class serializerLoginIn(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField()
    token_device = serializers.CharField()
    product         = serializers.IntegerField()
    lang            = serializers.CharField()

    def validate_email(self, value):
        queryExisteEmail    = persona.objects.filter(email=value).exists()
        if not queryExisteEmail:
            msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log002")
            #raise serializers.ValidationError({"status":"¡Lo sentimos!\n\nEl correo que ingresaste no\nse encuentra registrado."})
            raise serializers.ValidationError({"status": msg})
        return value

    def validate_product(self, value):
        queryExisteProduct  = producto.objects.filter(id=value).exists()
        if not queryExisteProduct:
            msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log001BE")
            #raise serializers.ValidationError({"status":"Debe proporcionar un producto correcto."})
            raise serializers.ValidationError({"status": msg})
        return value

    def validate_lang(self, value):
        #queryExisteIdioma   = Cat_languages.objects.filter(id=value).exists()
        #if not queryExisteIdioma:
        #    raise serializers.ValidationError({"status":"Debe proporcionar un idioma correcto."})
        return value

    def confirmaUsuarioLogin(self, data):
        # Confirma que el usuario este haciendo login a la app apropiada (Dispersa o Liberate).
        msjProd             = ""
        emailPersona        = data["email"]
        productoPersona     = data["product"]

        queryExisteEmail    = persona.objects.filter(email=emailPersona).exists()
        if not queryExisteEmail:
            msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log002")
            #raise serializers.ValidationError({"status": "¡Lo sentimos!\n\nEl correo que ingresaste no\nse encuentra registrado."})
            raise serializers.ValidationError({"status": msg})
        # Si el correo existe (registrado)
        else:
            # PASO1: Recupersar el tipo de producto
            #   Obterngo id de persona atravez del correo (users_persona)
            queryIdPersona = persona.objects.filter(email=emailPersona).values("id")
            idPersona = queryIdPersona[0]["id"]
            #   Recupero id del producto atravez del id de persona (users_cuenta)
            queryCuentaPersona = cuenta.objects.filter(persona_cuenta_id=idPersona).values("id", "rel_cuenta_prod_id")
            idCuenta = queryCuentaPersona[0]["id"]
            idProducto = queryCuentaPersona[0]["rel_cuenta_prod_id"]
            if idProducto != productoPersona:
                if idProducto == 1:  # Dispersa
                    msjProd = "BECPolipay Dispersa"
                if idProducto == 2:  # Liberate
                    msjProd = "BECPolipay Libérate"
                msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log002BE")
                msg = msg.replace("<app>", msjProd)
                #raise serializers.ValidationError({"status": "¡Lo sentimos!\n\n Estas usando la aplicación incorrecta busca " + str(msjProd) + " para poder acceder."})
                raise serializers.ValidationError({"status": msg})

    def confirmaTarjeta(self, data):
        emailPersona    = data["email"]
        #   Obterngo id de persona atravez del correo (users_persona)
        queryIdPersona  = persona.objects.filter(email=emailPersona).values("id")
        idPersona       = queryIdPersona[0]["id"]

        queryIdCuenta   = cuenta.objects.filter(persona_cuenta_id=idPersona).values("id")
        idCuenta        = queryIdCuenta[0]["id"]

        queryTarjetas   = tarjeta.objects.filter(cuenta_id=idCuenta).values("id", "tarjeta")
        if len(queryTarjetas) == 0 or queryTarjetas == False or queryTarjetas == None or queryTarjetas == "":
            msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log003BE")
            #raise serializers.ValidationError({"status": "¡Lo sentimos!\n\nNo tienes tarjetas asignadas, favor de\nverificar tus datos."})
            raise serializers.ValidationError({"status": msg})

    def validate(self, attrs):
        # Validación de usuario para el login correcto por apps
        self.confirmaUsuarioLogin(attrs)

        user = get_Object_orList_error(persona, email=attrs['email'])

        if not user.check_password(attrs['password']):
            msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log001")
            #raise serializers.ValidationError({"status": "¡Lo sentimos!\n\nTu correo o contraseña\nson incorrectos, favor de\nverificar tus datos."})
            raise serializers.ValidationError({"status": msg})

        if not user.state:
            msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log004BE")
            #raise serializers.ValidationError({"status": ["Esta cuenta ya no se encuentra disponible o no existe."]})
            raise serializers.ValidationError({"status": msg})

        if filter_object_if_exist(Token, user=user):
            get_Object_orList_error(Token, user=user).delete()
            Token.objects.create(user=user)
        else:
            Token.objects.create(user=user)

        #  (ChrGil 2021-10-28) Se descomenta sección de codigo se soluciono el problema con la cuenta APPLE (Firebase)
        #  (ChrAva 2021.11.08) Se agrega correo que utilizará Apple para pruebas, para que no se valide la multi-sesión
        if attrs['email'] != "store.tester@polimentes.mx" and attrs['email'] != "store.tester_token@polimentes.mx":
            # Valida que el usuario tenga al menos una tarjeta
            self.confirmaTarjeta(attrs)

            if user.token_device is None:
                return attrs

            if user.token_device != attrs['token_device']:
                verification_session_user(generate_url(self.context['request'], user.email), user)
                msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log005BE")
                msg = msg.replace("<email>", user.email)
                #raise serializers.ValidationError({"status": [f"Dispositivo no identificado.\n Se le notifico a \n{user.email}"]})
                raise serializers.ValidationError({"status": msg})
        return attrs


# -------------------------------------------------------------------------------------

class ComponentGetInfoUserCompany:
    def __init__(self, user: persona):
        self.user = user
        razon_social = self.get_razon_social_id

        if razon_social:
            is_cuenta_eje = self.get_cuenta_eje_info(razon_social.get("empresa_id"))
            if is_cuenta_eje:
                self.cuenta_eje = is_cuenta_eje.get("empresa_id")
            if not is_cuenta_eje:
                self.cuenta_eje = razon_social.get("empresa_id")

            self.comission = self.render_json

        if not razon_social:
            raise ValueError("El usuario no pertece a ninguna cuenta padre")

    @property
    def get_razon_social_id(self) -> Dict[str, Any]:
        return grupoPersona.objects.filter(
            person_id=self.user.get_only_id(),
            relacion_grupo_id__in=[6, 9]
        ).values(
            "empresa_id",
            "relacion_grupo_id"
        ).first()

    @staticmethod
    def get_cuenta_eje_info(empresa_id: int) -> Dict[str, Any]:
        return grupoPersona.objects.filter(
            person_id=empresa_id,
            relacion_grupo_id=5
        ).values(
            "empresa_id",
            "empresa__name",
            "relacion_grupo_id"
        ).first()

    @property
    def _get_comission_info(self) -> List[Dict[str, Any]]:
        return Commission.objects.select_related('person_debtor', 'person_payer', 'commission_rel').filter(
            Q(person_payer_id=self.cuenta_eje) | Q(person_debtor_id=self.cuenta_eje)
        ).filter(
            commission_rel__servicio_id=3
        ).values(
            'commission_rel__servicio__product_id',
            'commission_rel__servicio__service__nombre',
            'commission_rel__amount',
            'commission_rel__type',
        )

    @staticmethod
    def render_json_comission(**kwargs):
        type_comission = kwargs.pop('commission_rel__type')

        return {
            "id": kwargs.pop('commission_rel__servicio__product_id'),
            "producto": kwargs.pop('commission_rel__servicio__service__nombre'),
            "MontoFijo": float(kwargs.pop('commission_rel__amount')),
            "Comision": True if type_comission == 1 else False
        }

    @property
    def render_json(self) -> Dict[str, Any]:
        return {
            "commissions": [self.render_json_comission(**comission) for comission in self._get_comission_info],
        }




class serializerUserOut(serializers.Serializer):
    _comission_info: ClassVar[ComponentGetInfoUserCompany] = ComponentGetInfoUserCompany

    id                  = serializers.ReadOnlyField()
    email               = serializers.CharField()
    username            = serializers.CharField()
    is_superuser        = serializers.BooleanField()
    is_client           = serializers.BooleanField()
    fecha_nacimiento    = serializers.DateField()
    name                = serializers.CharField()
    last_name           = serializers.CharField()
    type_person         = serializers.SerializerMethodField()
    is_new              = serializers.BooleanField()
    last_login_user     = serializers.DateTimeField()
    date_joined         = serializers.DateTimeField()
    has_token           = serializers.SerializerMethodField()
    Counts              = serializers.SerializerMethodField()
    phone               = serializers.CharField()
    saldoActual         = serializers.SerializerMethodField()
    token               = serializers.SerializerMethodField()
    photo               = serializers.ImageField()
    comission           = serializers.SerializerMethodField()

    def get_type_person(self, obj: type_person):
        try:
            query = t_persona.objects.get(id=obj.tipo_persona_id)
            return query.tPersona
        except:
            return None

    def get_has_token(self, obj: has_token):
        hasToken    = False
        query = persona.objects.filter(id=obj.id).values("token")
        if len( str(query[0]["token"]) ) == 24:
            hasToken    = True
        return hasToken

    def get_Counts(self, obj: Counts):
        query = cuenta.objects.filter(persona_cuenta_id=obj.id)
        return serializerCuentaOutUser(query, many=True).data

    def get_saldoActual(self, obj: saldoActual):
        saldos = cuenta.objects.filter(persona_cuenta_id=obj.id)
        total = 0
        for saldo in saldos:
            total += saldo.monto
        return total

    def get_token(self, obj: token):
        token = get_Object_orList_error(Token, user_id=obj.id)
        return token.key

    def get_comission(self, obj: comission) -> Union[Dict[str, Any], None]:
        try:
            comission = self._comission_info(obj)
            return comission.comission
        except ValueError as e:
            return None


# -------------------------------------------------------------------------------------

class serializerChangePassIn(serializers.Serializer):
    code = serializers.CharField()
    email = serializers.CharField()
    password = serializers.CharField()
    passwordConfirm = serializers.CharField()
    product = serializers.IntegerField()
    lang = serializers.CharField()

    def validate_product(self, value):
        queryExisteProduct  = producto.objects.filter(id=value).exists()
        if not queryExisteProduct:
            msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log001BE")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            #raise serializers.ValidationError({"status":"Debe proporcionar un producto correcto."})
            raise serializers.ValidationError(r)
        return value

    def validate_lang(self, value):
        #queryExisteIdioma   = Cat_languages.objects.filter(id=value).exists()
        #if not queryExisteIdioma:
        #    raise serializers.ValidationError({"status":"Debe proporcionar un idioma correcto."})
        return value

    def confirmaUsuarioLogin(self, data):
        # Confirma que el usuario este haciendo login a la app apropiada (Dispersa o Liberate).
        msjProd             = ""
        emailPersona        = data["email"]
        productoPersona     = data["product"]

        queryExisteEmail    = persona.objects.filter(email=emailPersona).exists()
        if not queryExisteEmail:
            msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log002")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            #raise serializers.ValidationError({"status": "¡Lo sentimos!\n\nEl correo que ingresaste no\nse encuentra registrado."})
            raise serializers.ValidationError(r)
        # Si el correo existe (registrado)
        else:
            # PASO1: Recupersar el tipo de producto
            #   Obterngo id de persona atravez del correo (users_persona)
            queryIdPersona = persona.objects.filter(email=emailPersona).values("id")
            idPersona = queryIdPersona[0]["id"]
            #   Recupero id del producto atravez del id de persona (users_cuenta)
            queryCuentaPersona = cuenta.objects.filter(persona_cuenta_id=idPersona).values("id", "rel_cuenta_prod_id")
            idCuenta = queryCuentaPersona[0]["id"]
            idProducto = queryCuentaPersona[0]["rel_cuenta_prod_id"]
            if idProducto != productoPersona:
                if idProducto == 1:  # Dispersa
                    msjProd = "BECPolipay Dispersa"
                if idProducto == 2:  # Liberate
                    msjProd = "BECPolipay Libérate"
                msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log002BE")
                msg = msg.replace("<app>", str(msjProd))
                r = {"status": msg}
                RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
                #raise serializers.ValidationError({"status": "¡Lo sentimos!\n\n Estas usando la aplicación incorrecta busca " + str(msjProd) + " para poder acceder."})
                raise serializers.ValidationError(r)

    def validate(self, attrs):
        # Validación de usuario para el login correcto por apps
        self.confirmaUsuarioLogin(attrs)

        instance = get_Object_orList_error(persona, email=attrs['email'])
        code = cache.get(instance.email)
        if attrs['password'] == attrs['passwordConfirm']:
            if attrs['code'] == code:
                return attrs
            else:
                msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log006BE")
                r = {"status": [msg]}
                RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
                #raise serializers.ValidationError({"status": ["Codigo expirado o no encontrado"]})
                raise serializers.ValidationError(r)
        else:
            msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Log007BE")
            #raise serializers.ValidationError({"status": "Contraseñas no coinciden"})
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            raise serializers.ValidationError(r)

    def save(self, instance):
        instance.set_password(self.validated_data.get('password'))
        instance.save()


# -----------------------------------------------------------------------------------------

class serializerUpdateUser(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.CharField()
    fecha_nacimiento = serializers.DateField()
    phone = serializers.CharField()

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.email = validated_data.get('email', instance.email)
        instance.fecha_nacimiento = validated_data.get('fecha_nacimiento', instance.fecha_nacimiento)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.save()
        print(instance)

        return instance


# -----------------------------------------------------------------------------------------
# Manuel

class serializerUpdateUser(serializers.Serializer):
    name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.CharField()
    fecha_nacimiento = serializers.DateField()
    phone = serializers.CharField()

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.last_name = validated_data.get('last_name', instance.name)
        instance.email = validated_data.get('email', instance.email)
        instance.fecha_nacimiento = validated_data.get('fecha_nacimiento', instance.fecha_nacimiento)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.save()

        return instance


# ------------------------------------------------------------------------------------------------------------

class serializerEditPasswordIn(serializers.Serializer):
    password = serializers.CharField()
    email = serializers.CharField()
    new_password = serializers.CharField()
    new_password_confirm = serializers.CharField()

    def validate(self, data):
        if data["new_password"] == data["new_password_confirm"]:
            emails = persona.objects.filter(email=data["email"])

            if len(emails) > 0:
                pwd = emails[0].check_password(data["password"])
                if pwd:
                    return data
                else:
                    msg = LanguageRegisteredUser(self.initial_data.get("id"), "Das001BE")
                    r = {"status": [msg]}
                    RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
                    #raise serializers.ValidationError({"status": ["Datos Incorrectos"]})
                    raise serializers.ValidationError(r)
            else:
                msg = LanguageRegisteredUser(self.initial_data.get("id"), "Das002BE")
                r = {"status": [msg]}
                RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
                #raise serializers.ValidationError({"status": ["Dirección de correo electronico no encontrado"]})
                raise serializers.ValidationError(r)
        else:
            msg = LanguageRegisteredUser(self.initial_data.get("id"), "Das003BE")
            r = {"status": [msg]}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            #raise serializers.ValidationError({"status": ["Las contraseñas no coinciden"]})
            raise serializers.ValidationError(r)

    def update(self, instance, validated_data):
        instance.set_password(validated_data.get("new_password"))
        instance.save()
        return instance


# ------------------------------------------------------------------------------------------------------------

# Serializador para cambiar token_device segunda versión. Aun se esta desarrollando
class ChangeDeviceSerializerIn(serializers.Serializer):
    code = serializers.IntegerField()
    email = serializers.EmailField()
    token_device = serializers.CharField()

    def validate(self, attrs):
        user = get_Object_orList_error(persona, email=attrs['email'])
        code = cache.get(user.email, None)

        if attrs['code'] == int(code):
            return attrs
        else:
            raise serializers.ValidationError({"status": ["Codigo expirado o no encontrado"]})

    def update(self, instance, validated_data):
        send_push("Alerta Polipay", "Este dispositivo dejo de ser el pricipal.", instance.token_device)
        instance.token_device = validated_data.get('token_device', instance.name)
        instance.save()
        return instance


# -----------------------------------------------------------------------------------------

class serializerEditTokenIn(serializers.Serializer):
    token = serializers.CharField()

    def update(self, instance, validated_data):
        instance.token = validated_data.get("token", instance.token)
        instance.save()
        return instance


class SerializerEditPhoto(serializers.Serializer):
    photo = Base64ImageField(required=False)

    def Update_image(self, instance):
        if self.validated_data.get('photo') != None:
            instance.photo = self.validated_data['photo']
            instance.save()
            URL_photo = instance.photo.url
        return URL_photo


class serializerListUser(serializers.Serializer):
    id = serializers.ReadOnlyField()
    email = serializers.CharField()
    username = serializers.CharField()
    name = serializers.CharField()
    last_name = serializers.CharField()
    date_joined = serializers.DateTimeField()


class serializerListCard(serializers.Serializer):
    id = serializers.ReadOnlyField()
    tarjeta = serializers.CharField()


class serializerAccountsUser(serializers.Serializer):
    id = serializers.ReadOnlyField()
    cuenta = serializers.CharField()
    cuentaclave = serializers.CharField()
    monto = serializers.CharField()


class serializerUpdateAccount(serializers.Serializer):
    id = serializers.ReadOnlyField()
    cuenta = serializers.CharField()
    cuentaclave = serializers.CharField()
    monto = serializers.CharField()

    def update_account(self, instance):
        instance.cuenta = self.validated_data.get('cuenta', instance.cuenta)
        instance.cuentaclave = self.validated_data.get('cuentaclave', instance.cuentaclave)
        instance.monto = self.validated_data.get('monto', instance.monto)
        instance.save()
        return True


class serializerChangeNip(serializers.Serializer):
    id = serializers.IntegerField()
    nip = serializers.CharField()
    #persona = serializers.IntegerField()

    #def validate_persona(self, value):
    #    queryExistePersona = persona.objects.filter(id=value).exists()
    #    if not queryExistePersona:
    #        msg = LanguageRegisteredUser(self.initial_data.get("persona"), "Das012BE")
    #        raise serializers.ValidationError({"status": msg})
    #    return value

    def changeNip(self):
        instance		= get_Object_orList_error(tarjeta, id=self.validated_data.get('id'))
        # Cifrado
        objJson			= encdec_nip_cvc_token4dig("1", "BE", self.validated_data.get('nip'))
        instance.nip	= objJson["data"]
        instance.save()

# (JM 2021/12/06) Se corrigio los mensajes de error antiguos
class CheckCode(serializers.Serializer):
    code = serializers.CharField()
    email = serializers.CharField()

    def validate(self, attrs):
        client = get_Object_orList_error(persona, email=attrs['email'])

        if attrs['code'] != cache.get(client.phone, None):
            raise serializers.ValidationError({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [{"field":"code", "data":attrs["code"],"message": "Codigo expirado o no valido"}]})
        else:
            cache.get(client.phone)
            return attrs



# -------- (ChrAvaBus Jue25.11.2021) v3 --------

class SerializerUpdateToken(serializers.Serializer):
    id          = serializers.IntegerField()
    token       = serializers.CharField()
    password    = serializers.CharField()

    def validate_token(self, value):
        # Confirma que sean unicamente numeros
        arrayNumeros    = [0,1,2,3,4,5,6,7,8,9]
        arrayToken      = list( str(value) )
        digito          = 0
        try:
            for num in arrayToken:
                digito	= num
                if int(num) in arrayNumeros == False:
                    print("...")
        except Exception:
            """
            result	= {
                "code":[400],
                "status":"ERROR",
                "detail":[
                    {
                        "field":"token",
                        "data":value,
                        "message":"El caracter ("+ str(digito) +") no es un valor numérico."
                    }
                ]	
            }
            raise serializers.ValidationError(result)
            """
            msg = LanguageRegisteredUser(self.initial_data.get("id"), "Das009BE")
            msg = msg.replace("<digito>", str(digito))
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            raise serializers.ValidationError(r)
            #raise serializers.ValidationError({"status":"El caracter ("+ str(digito) +") no es un valor numérico."})

        # Confrima que sean 4 digitos
        if len(value) != 4:
            msg = LanguageRegisteredUser(self.initial_data.get("id"), "Das010BE")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            raise serializers.ValidationError(r)
            #raise serializers.ValidationError({"status":"Debe contener 4 digitos."})

    def validate(self, data):
        user	= get_Object_orList_error(persona, id=data["id"])
        if not user.check_password(data["password"]):
            msg = LanguageRegisteredUser(self.initial_data.get("id"), "Das011BE")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            raise serializers.ValidationError(r)
            #raise serializers.ValidationError({"status":"Datos incorrectos."})
        return data

    def updateToken(self, data):
        instance	= get_Object_orList_error(persona, id=self.validated_data.get("id"))
        # Cifrado
        objJson			= encdec_nip_cvc_token4dig("1", "BE", data["token"])
        instance.token	= objJson["data"]
        instance.save()



# -------- (ChrAvaBus Mie23.12.2021) v3 --------

class SerializerUpdateLanguage(serializers.Serializer):
    id      = serializers.IntegerField()
    lang    = serializers.IntegerField()

    def validate_id(self, value):
        if value == False or value == None or value == "":
            r = {"status":"Debes proporcionar un id."}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            raise serializers.ValidationError(r)

        queryExistePersona = persona.objects.filter(id=value).exists()
        if not queryExistePersona:
            r = {"status": "Persona no existe, nada por hacer."}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            raise serializers.ValidationError(r)

        return value

    def validate_lang(self, value):
        if value == False or value == None or value == "":
            r = {"status": "Debes proporcionar un idioma correcto."}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            raise serializers.ValidationError(r)

        queryExisteIdioma = Cat_languages.objects.filter(id=value).exists()
        if not queryExisteIdioma:
            r = {"status": "Idioma no existe, nada por hacer."}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            raise serializers.ValidationError(r)

        return value

    def validate(self, data):
        queryExisteConfLang = Language_Person.objects.filter(person_id=data["id"]).exists()
        if not queryExisteConfLang:
            instanciaConfLang   = Language_Person(
                creation_date=datetime.now(),
                person_id=data["id"],
                selected_language_id=data["lang"]
            )
            instanciaConfLang.save()

        return data

    def updateLanguage(self, data):
        instance                        = get_Object_orList_error(Language_Person, person_id=data["id"])
        instance.selected_language_id   = data["lang"]
        instance.creation_date          = datetime.now()
        instance.save()


class SerializerDeleteCard(serializers.Serializer):
    persona = serializers.IntegerField()
    tarjeta = serializers.IntegerField()
    alias   = serializers.CharField()

    def validate_persona(self, value):
        queryExistePersona  = persona.objects.filter(id=value).exists()
        if not queryExistePersona:
            msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd003")
            r   = {"status": msg}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            raise serializers.ValidationError(r)
        return value

    def validate_tarjeta(self, value):
        queryExisteTarjeta  = tarjeta.objects.filter(tarjeta=value).exists()
        if not queryExisteTarjeta:
            msg = LanguageRegisteredUser(self.initial_data.get("persona"), "Das005BE")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            raise serializers.ValidationError(r)
        return value

    def validate(self, data):
        queryCuenta     = cuenta.objects.filter(persona_cuenta_id=data["persona"]).values("id")
        queryPertenece  = tarjeta.objects.filter(cuenta_id=queryCuenta[0]["id"], tarjeta=data["tarjeta"]).exists()
        if not queryPertenece:
            msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd005")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            raise serializers.ValidationError(r)
        else:
            queryTarjeta    = tarjeta.objects.filter(cuenta_id=queryCuenta[0]["id"], tarjeta=data["tarjeta"]).values("id")
            data["idCard"]  = queryTarjeta[0]["id"]
        return data

    def deleteCard(self, data):
        instance                = get_Object_orList_error(tarjeta, id=data["idCard"])
        instance.deletion_date  = datetime.now()
        instance.was_eliminated = True
        instance.status         = "28"
        instance.is_active      = False
        r   = {"deleteCard":{"INNTEC":"cambiando status de tarjeta en inntec"}}
        RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
        response    = change_status(instance.TarjetaId, "28", "Bloqueada ")
        r = {"deleteCard": {"INNTEC": str(response)}}
        RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
        if response[1] == 200 and response[0]["Respuesta"] == 0:
            instance.save()
            r = {"deleteCard": {"INNTEC": "cambio correctamente"}}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
        elif response[1] == 200 and response[0]["Respuesta"] == 1:
            instance.save()
            #msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd006")
            #r = {"status": msg}
            r   = {"status": "Tarjeta no pudo ser bloqueada ante INNTEC, pero en la bdd se elimina."}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            #raise serializers.ValidationError(r)
        elif response[1] == 400 or response[1] == 500:
            msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd007")
            r = {"status": msg}
            RegisterSystemLog(idPersona=self.context["idUser"], type=1, endpoint=self.context["url"], objJsonResponse=r)
            raise serializers.ValidationError(r)


