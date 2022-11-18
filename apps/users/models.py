import uuid
from typing import Dict, Any

from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
import datetime
# from productos.models import producto
from rest_framework.settings import api_settings

from .managerUser import UserManager, QueryPersonaManager
from apps.users.manager import ManagerDomicilio, ManagerTarjeta, CuentaManager, GrupoPersonaManager, DocumentsManager, \
    ManagerAccessCredentials
from apps.users.choices import STATUS_DOCUMENT, CREDENCIALS_PLATAFORM


class t_persona(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    tPersona = models.CharField(max_length=6, null=False, unique=True)


class persona(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True, editable=False)
    email = models.CharField(max_length=254, null=False, blank=False, unique=True)
    password = models.CharField(max_length=255, null=False, blank=True)
    username = models.CharField(max_length=45, null=False, blank=False, unique=True)
    is_active = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_client = models.BooleanField(default=True)
    fecha_nacimiento = models.DateField(null=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    date_modify = models.DateTimeField(auto_now_add=True)
    token = models.CharField(max_length=50, null=True, blank=True, default=None)
    last_login_user = models.DateTimeField(auto_now_add=True, null=True)
    is_new = models.BooleanField(default=True)
    name = models.CharField(max_length=80, null=False, blank=False)
    last_name = models.CharField(max_length=80, null=True, blank=True)
    phone = models.CharField(max_length=14, null=False, blank=False, default="999999999999")
    tipo_persona = models.ForeignKey(t_persona, on_delete=models.DO_NOTHING, default=1, related_name="t_persona")
    curp = models.CharField(max_length=13, null=False, blank=False, default="CURPNOVALIDO")
    ip_address = models.CharField(max_length=25, null=True, blank=True, default=None)
    token_device = models.CharField(max_length=255, null=True, blank=True)
    state = models.BooleanField(default=False)
    photo = models.FileField(upload_to="Photo", default=None)
    rfc = models.CharField(max_length=13, default="NoData")
    motivo = models.TextField(max_length=1000, null=True, blank=True)
    giro = models.CharField(max_length=30, null=True, blank=True)
    homoclave = models.CharField(max_length=4, null=True, blank=True)  # propiedad de cuenta?

    # Se añadio unique directamente en la bd
    clabeinterbancaria_uno = models.CharField(max_length=18, null=True, blank=True)  # propiedad de cuenta ?

    # Se añadio unique directamente en la bd
    clabeinterbancaria_dos = models.CharField(max_length=18, null=True, blank=True)  # propiedad de cuenta ?

    banco_clabe = models.CharField(max_length=3, null=True, blank=True)  # propiedad de banco ?
    # fdomicilio = models.ForeignKey(domicilio, on_delete=models.DO_NOTHING, null=True, blank=True)
    clave_traspaso = models.CharField(blank=True, max_length=16, null=True)  # propiedad de banco?
    token_device_app_token = models.CharField(max_length=255, null=True, blank=True)
    name_stp = models.CharField(max_length=45, null=True, blank=True)
    USERNAME_FIELD = "username"
    objects = UserManager()
    querys = QueryPersonaManager()

    class Meta:
        permissions = [('can_create_user_v2', 'Puede crear usuario'),
                       ('can_edit_user_v2', 'Puede editar usuario'),
                       ('can_get_user_v2', 'Puede ver usuario'),
                       ('can_do_all_user_v1', 'Puede hacer todo')]

    def __str__(self):
        return self.username

    @property
    def get_username(self):
        return self.username

    def get_only_id(self):
        return self.id

    def get_email(self):
        return self.email

    @property
    def get_is_superuser(self):
        return self.is_superuser

    def get_cuenta_eje(self):
        return {
            "id": self.id,
            "name": self.name,
            "is_active": self.is_active
        }

    def get_razon_social(self):
        return {
            "id": self.id,
            "name": self.name,
            "clabeinterbancaria_uno": self.clabeinterbancaria_uno,
            "is_active": self.is_active
        }

    def get_full_name(self):
        return f'{self.name} {self.last_name}'

    def get_last_name(self):
        return self.last_name

    def get_centro_costo(self):
        return {
            "id": self.id,
            "name": self.name,
            "date_joined": self.date_joined,
            "state": self.state
        }

    def get_centro_costo_all_data(self):
        return {
            "id": self.id,
            "name": self.name,
            "rfc": self.rfc,
            "clabe_traspaso": self.clave_traspaso,
            "banco_clabe": self.banco_clabe,
            "motivo": self.motivo
        }

    def get_staff_or_superusers(self):
        return {
            "id": self.id,
            "is_superuser": self.is_superuser,
            "is_staff": self.is_staff
        }

    def get_administratives(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone
        }

    def get_fisic_person(self):
        return {
            "id": self.id,
            "name": self.get_full_name()
        }

    def get_persona_wallet(self):
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "name": self.name,
            "last_name": self.last_name,
            "date_joined": self.date_joined
        }

    def get_name_company(self):
        return self.name

    def get_admin(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'last_name': self.last_name,
            'email': self.email,
            'fecha_nacimiento': self.fecha_nacimiento,
            'phone': self.phone
        }

    def get_id_and_name(self):
        return {
            'id': self.id,
            'name': self.name
        }

    @property
    def get_token_device_app(self):
        return self.token_device_app_token


class domicilio(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    codigopostal = models.CharField(max_length=6, null=True, blank=True)
    colonia = models.CharField(max_length=50, null=True, blank=True)
    alcaldia_mpio = models.CharField(max_length=50, null=True, blank=True)
    estado = models.CharField(max_length=50, null=True, blank=True)
    calle = models.CharField(max_length=250, null=True, blank=True)
    no_exterior = models.CharField(max_length=5, null=True, blank=True)
    no_interior = models.CharField(max_length=4, null=True, blank=True)
    pais = models.CharField(max_length=60, null=True, blank=True)
    historial = models.BooleanField(default=False)
    dateUpdate = models.DateTimeField(blank=True, null=True)
    domicilioPersona = models.ForeignKey(persona, on_delete=models.DO_NOTHING, blank=True, null=True)

    objects = ManagerDomicilio()

    def get_domicilio(self):
        return {
            "codigopostal": self.codigopostal,
            "colonia": self.colonia,
            "alcaldia_mpio": self.alcaldia_mpio,
            "estado": self.estado,
            "calle": self.calle,
            "no_exterior": self.no_exterior,
            "no_interior": self.no_interior,
            "pais": self.pais
        }


class trelacion(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nombrerel = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=255, null=True, blank=True)


class grupoPersona(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    person = models.ForeignKey(persona, on_delete=models.DO_NOTHING, related_name="persona")
    empresa = models.ForeignKey(persona, on_delete=models.DO_NOTHING, related_name="empresa")
    is_admin = models.BooleanField(default=False, null=False)
    nombre_grupo = models.CharField(max_length=60, null=True, default=None)
    relacion_grupo = models.ForeignKey(trelacion, on_delete=models.DO_NOTHING, null=True, default=None)
    addworker = models.BooleanField(default=False)
    delworker = models.BooleanField(default=False)
    fechacreacion = models.DateTimeField(auto_now_add=True)
    fechamod = models.DateTimeField(auto_now=True)
    objects = GrupoPersonaManager()

    def __str__(self):
        return self.nombre_grupo

    @property
    def person_details(self) -> Dict:
        return {
            "person_id": self.person.get_only_id(),
            "name": self.person.get_full_name(),
            "email": self.person.get_email()
        }

    @property
    def company_details(self) -> Dict:
        return {
            "id": self.empresa.get_only_id(),
            "name": self.empresa.get_name_company(),
            "is_active": self.empresa.is_active,
            #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
            "name_stp": self.empresa.name_stp
        }

    def get_only_id_empresa(self) -> int:
        return self.empresa_id

    def get_name_comany(self):
        return self.empresa.get_name_company()

    def get_cuenta_eje(self) -> Dict:
        return {
            "cuenta_eje": self.empresa.get_cuenta_eje()
        }

    def get_empresa(self) -> Dict:
        data = self.company_details
        data['create'] = self.empresa.date_joined
        data['clabe'] = self.empresa.clabeinterbancaria_uno
        return data

    def get_person_and_empresa(self):
        return {
            "empresa_id": self.empresa.get_only_id(),
            "person_id": self.person.get_only_id(),
            "name": self.empresa.get_name_company(),
            "is_admin": self.is_admin
        }

    def get_cost_center(self) -> Dict:
        data = self.company_details
        data['cuenta'] = cuenta.objects.get(persona_cuenta_id=self.empresa_id).get_all_cuentas()
        return data

    def get_cost_center_name(self):
        return {
            "cost_center_name":self.person.name
        }


class TDocumento(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nombreTipo = models.CharField(max_length=50, blank=False, null=False)
    descripcion = models.CharField(max_length=255, blank=True, null=True)


class documentos(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    tdocumento = models.ForeignKey(TDocumento, on_delete=models.DO_NOTHING, related_name="tipo_documento", default=1)
    person = models.ForeignKey(persona, on_delete=models.DO_NOTHING, related_name="user_doctos")
    userauth = models.ForeignKey(persona, on_delete=models.DO_NOTHING, null=True, default=None, related_name="autoriza")
    comentario = models.CharField(max_length=254, null=True, default=None)
    authorization = models.BooleanField(default=0)
    dateauth = models.DateTimeField(default=None, null=True)
    load = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=1, choices=STATUS_DOCUMENT, default='P')
    documento = models.FileField(upload_to='documento', default="No se cargo el documento")
    historial = models.BooleanField(default=False)  #
    dateupdate = models.DateTimeField(null=True, blank=True)
    objects = DocumentsManager()

    class Meta:
        permissions = [('can_create_documents_v2', 'Puede crear documentos'),
                       ('can_edit_documents_v2', 'Puede editar documentos'),
                       ('can_get_user_v2', 'Puede ver documentos'),
                       ('can_delete_documents_v2', 'Puede eliminar documentos')]

    @property
    def get_tipo_documento(self) -> Dict[str, Any]:
        return {
            "id": self.tdocumento_id,
            "tipo": self.tdocumento.nombreTipo
        }

    @property
    def get_owner(self) -> str:
        return self.person.name


    def is_authorization(self):
        return self.authorization

    # (ChrGil 2021-11-22) Obtiene la ubicación actual en AWS del documento, si no regresa una exception de DoesNotExist
    def get_url_aws_document(self) -> str:
        value = getattr(self, 'documento', api_settings.UPLOADED_FILES_USE_URL)
        return value.url


class tcuenta(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nTCuenta = models.CharField(max_length=25, unique=True)


class cuenta(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    cuenta = models.CharField(max_length=16, blank=False, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    monto = models.FloatField(null=True, default=0)
    is_active = models.BooleanField(default=False)
    persona_cuenta = models.ForeignKey(persona, on_delete=models.DO_NOTHING, blank=True, null=True)
    cuentaclave = models.CharField(max_length=18, blank=True, null=True, editable=False)
    expire = models.DateTimeField(null=True, blank=True)
    rel_cuenta_prod = models.ForeignKey("productos.producto", on_delete=models.CASCADE, default=1)
    objects = CuentaManager()

    class Meta:
        permissions = [('can_create_transactions_v2', 'Puede crear transacciones'),
                       ('can_edit_transactions_v2', 'Puede editar transacciones'),
                       ('can_get_transactions_v2', 'Puede ver transacciones')]

    @property
    def get_person_id(self) -> int:
        return self.persona_cuenta_id

    def get_only_id(self):
        return self.id

    def get_cuenta(self):
        return self.cuenta

    def get_cuentaclabe(self):
        return self.cuentaclave

    def get_all_cuentas(self):
        return {
            "id": self.id,
            "cuenta": self.cuenta,
            "cuentaclabe": self.cuentaclave,
            "is_active": self.is_active,
            "monto": self.monto,
            "persona_cuenta_id": self.persona_cuenta_id
        }

    def get_monto_emisor(self):
        return self.monto

    def get_email(self):
        return self.persona_cuenta.get_email()

    @property
    def details_cuenta(self) -> Dict:
        return {
            "id": self.id,
            "account": self.cuenta,
            "company_name": self.persona_cuenta.get_name_company(),
            "state": self.is_active,
            "monto": self.monto
        }

    @property
    def get_persona_cuenta(self) -> str:
        return self.persona_cuenta.get_full_name()

    @property
    def get_account_stp(self) -> str:
        return self.cuentaclave[0:10]

    @property
    def muestra_numero_centro_costos(self) -> int:
        return int(self.cuentaclave[13:17])

    @property
    def get_last_digits(self) -> str:
        return self.cuentaclave[13:18]


class proveedores_tarj(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    nombre = models.CharField(max_length=20, null=True, unique=True)
    descripcion = models.CharField(max_length=20, null=True)


class paramsProveedores(
    models.Model):  # tabla para status y/o parametros de tarjetas proporcionados por los proveedores
    id = models.AutoField(primary_key=True, unique=True)
    pametro = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=50)
    tipo = models.CharField(max_length=50)
    fproveedor = models.ForeignKey(proveedores_tarj, on_delete=models.DO_NOTHING, default=1)


class statusPolipay(models.Model):  # Tabla para status internos de polipay
    id = models.AutoField(primary_key=True, unique=True)
    nombreStatus = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=50)


class cat_tarjeta(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    nombreCom = models.TextField(max_length=30, null=False, blank=False)
    descripcion = models.TextField(max_length=254)
    costoUnit = models.FloatField(default=10)


class tarjeta(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    tarjeta = models.CharField(max_length=16, null=True, unique=True)
    nip = models.CharField(max_length=24, null=True, blank=True, default=None)
    is_active = models.BooleanField(default=False)
    tipo_cuenta = models.ForeignKey(tcuenta, on_delete=models.DO_NOTHING, blank=False, default=1)
    cuenta = models.ForeignKey(cuenta, on_delete=models.DO_NOTHING, blank=True, null=True, default=None)
    monto = models.FloatField(null=True, default=0)
    status = models.CharField(max_length=10, null=True)
    TarjetaId = models.BigIntegerField(unique=True)
    ClaveEmpleado = models.CharField(max_length=50, null=True)
    NumeroCuenta = models.CharField(max_length=50, null=True)
    cvc = models.CharField(max_length=24, blank=True, default="n/a")
    fechaexp = models.DateField(null=True, blank=True)
    alias = models.CharField(max_length=150, null=True, default=None, blank=True)
    fecha_register = models.DateTimeField(auto_now_add=True)
    rel_proveedor = models.ForeignKey(proveedores_tarj, on_delete=models.DO_NOTHING, default=1)
    statusInterno = models.ForeignKey(statusPolipay, on_delete=models.DO_NOTHING, default=1)
    tipo_tarjeta = models.ForeignKey(cat_tarjeta, on_delete=models.DO_NOTHING, blank=True, null=True)
    clientePrincipal = models.ForeignKey(persona, on_delete=models.DO_NOTHING, blank=True, null=True)
    deletion_date = models.DateTimeField(default=None)
    was_eliminated = models.BooleanField(default=False)
    objects = ManagerTarjeta()

    class Meta:
        permissions = [('can_create_transactions_v2', 'Puede crear transacciones'),
                       ('can_edit_transactions_v2', 'Puede editar transacciones'),
                       ('can_get_transactions_v2', 'Puede ver transacciones')]

    def get_tarjeta(self):
        return self.tarjeta

    # (ChrGil 2021-11-17) Obtiene el nombre completo del personal externo, cuenta y numero de tarjeta
    def get_tarjeta_personal_externo(self):
        return {
            "Tarjeta": self.tarjeta,
            "Cuenta": self.cuenta.get_persona_cuenta
        }

    # [clientePrincipal] cliente directo de polipay
    """
        Bitacora:
            Cambio: (campo) clientePrincipal 
            Quien lo solicita: Christian Gil
            Cuando: 30-09-2021
            Razón: dhasjkdhajksdn    
    """


class corte(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    cuenta = models.ForeignKey(cuenta, on_delete=models.DO_NOTHING, blank=False)
    saldo = models.FloatField(null=False, blank=False)
    fecha = models.DateField(auto_now_add=True, null=False, blank=False)


class Productos(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nombre_producto = models.CharField(max_length=30)

    def __str__(self):
        return self.nombre_producto


class Comisiones(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    f_producto = models.ForeignKey(Productos, on_delete=models.DO_NOTHING, blank=False)
    comision = models.BooleanField(default=True)
    porc_comision = models.FloatField(null=False, blank=False, default=.001)
    f_persona = models.ForeignKey(persona, on_delete=models.DO_NOTHING, blank=False, related_name="Comision_cliente")
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_autorizacion = models.DateTimeField(null=False, blank=False)
    usuario_autorizacion = models.ForeignKey(persona, on_delete=models.DO_NOTHING, blank=False,
                                             related_name="SU_autoriza")

    def __str__(self):
        return self.f_producto.nombre_producto

    def get_producto(self):
        return self.f_producto.nombre_producto

    def get_comision(self):
        return {
            'producto': self.f_producto.nombre_producto,
            'Porcentaje': self.porc_comision,
            'Comision': self.comision
        }


class Access_credentials(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    credentials_type = models.BooleanField(default=False)
    person = models.ForeignKey(persona, on_delete=models.DO_NOTHING)
    credential_access = models.TextField(max_length=None)
    created_date = models.DateTimeField(auto_now_add=True)
    credential_app = models.CharField(max_length=1, choices=CREDENCIALS_PLATAFORM, default='M')

    objects = ManagerAccessCredentials()



class ConcentradosAuxiliar(models.Model):
    id              = models.AutoField(primary_key=True, editable=False)
    creation_date   = models.DateTimeField(default=None, null=True)
    json_content    = models.TextField(default={}, null=True)
    persona         = models.ForeignKey(persona, on_delete=models.DO_NOTHING, blank=True, null=True)
