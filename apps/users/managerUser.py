import datetime
import datetime as dt
import random
import string
from typing import List, Dict, Union, Any
from django.contrib.auth.hashers import make_password
import uuid

from django.contrib.auth.models import (BaseUserManager)
from django.db import models
from django.db.models import Q


def Code_card(size_number):
    valores = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    size = size_number
    code = "".join([str(random.choice(valores)) for i in range(size)])
    return code


def random_number(length: int = 8):
    return "".join(random.choices(string.digits, k=length))


class UserManager(BaseUserManager):
    def create_user(self, email, username, fecha_nacimiento, token, name, last_name, phone, tipo_persona, ip_address, password=None):
        if not email:
            raise ValueError('Email requerido')

        user = self.model(
            email=self.normalize_email(email),
            username=username,
            fecha_nacimiento=fecha_nacimiento,
            token=token,
            name=name,
            last_name=last_name,
            phone=phone,
            tipo_persona_id=tipo_persona,
            ip_address=ip_address
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_admin(
            self,
            email: str,
            name: str,
            phone: str,
            is_superuser: bool,
            is_staff: bool,
            fecha_nacimiento: dt.date,
            a_paterno: str,
            a_materno: str,
            password: str,
            rfc: Union[str] = "",
            homoclave: Union[str, None] = None,
            ip_address: Union[str, None] = None,
            motivo: Union[str, None] = None):

        user = self.model(
            email=self.normalize_email(email),
            name=name,
            last_name=f"{a_paterno}*{a_materno}",
            username=str(uuid.uuid4()),
            phone=phone,
            token=str(random_number(4)),
            is_superuser=is_superuser,
            is_staff=is_staff,
            fecha_nacimiento=fecha_nacimiento,
            ip_address=ip_address,
            motivo=motivo,
            password=password,
            rfc=rfc,
            homoclave=homoclave,
            state=True
        )
        user.is_active = False
        user.is_client = False
        user.is_new = True
        user.tipo_persona_id = 2
        user.set_password(user.password)
        user.save(using=self._db)
        return user

    # (ChrGil 2022-01-05) Creación de un brigadista para dar de alta beneficiarios de la cuenta eje
    # (ChrGil 2022-01-05) de Adelante Zapopan
    def create_brigadista(
            self,
            email: str,
            name: str,
            last_name: str,
            phone: str,
            password: str,
            ip_address: Union[str, None] = None) -> int:

        user = self.model(
            email=self.normalize_email(email),
            name=name,
            last_name=last_name,
            username=str(uuid.uuid4()),
            phone=phone,
            token=random_number(4),
            ip_address=ip_address,
            password=password,
            state=True
        )
        user.fecha_nacimiento = dt.date.today()
        user.is_superuser = False
        user.is_staff = False
        user.is_active = False
        user.is_client = False
        user.is_new = True
        user.tipo_persona_id = 3
        user.set_password(user.password)
        user.save(using=self._db)
        return user.id

    def create_client(self, email, fecha_nacimiento, token, name, last_name, phone, tipo_persona, ip_address, password=None):
        user = self.create_user(
            email=self.normalize_email(email),
            username=str(uuid.uuid4()),
            fecha_nacimiento=fecha_nacimiento,
            token=token,
            name=name,
            last_name=last_name,
            phone=phone,
            tipo_persona=tipo_persona,
            ip_address=ip_address
        )
        user.is_admin = False
        user.is_active = False
        user.is_client = True
        user.is_new = True
        user.state = True
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_razon_social(self, name, rfc, fecha_nacimiento, clabeinterbancaria_uno, giro, name_stp, type):
        email = name.replace(" ", "") + rfc.replace(" ", "") + str(random_number(4))
        #   (2022.08.10 08:00:00 - ChrAvaBus) Mejora: sprint 06/06/2022
        #   Para la Cuenta Eje (PPCE)
        user    = None
        if int(type) == 0:
            # (AAF 2022-06-06 13:21) se quitan las variables clabeinterbancaria_dos, , banco_clabe debido a modificaciones solicitadas
            # (AAF 2022-06-07 12:02) se añade name_stp
            clabeinterbancaria_uno_actualizada = clabeinterbancaria_uno[0:6] + "PPCE" + clabeinterbancaria_uno[10:18]
            user = self.model(
                name=name,
                rfc=rfc,
                email=email,
                username=str(uuid.uuid4()),
                fecha_nacimiento=fecha_nacimiento,
                clabeinterbancaria_uno=clabeinterbancaria_uno_actualizada,
                # clabeinterbancaria_dos=clabeinterbancaria_dos,
                giro=giro,
                name_stp=name_stp
                # banco_clabe=banco_clabe
            )
        elif int(type) == 1:
            user = self.model(
                name="CONCENTRADORA " + name_stp,
                rfc=rfc,
                email=email,
                username=str(uuid.uuid4()),
                fecha_nacimiento=fecha_nacimiento,
                clabeinterbancaria_uno=clabeinterbancaria_uno,
                # clabeinterbancaria_dos=clabeinterbancaria_dos,
                giro=giro,
                name_stp=name_stp
                # banco_clabe=banco_clabe
            )

        user.is_admin = False
        if int(type) == 0:
            user.is_active = False
        elif int(type) == 1:
            user.is_active = True
            user.state = True
        user.is_client = True
        user.is_new = True
        user.tipo_persona_id = 1
        user.save(using=self._db)
        return user

    def create_representante_legal(self, name, last_name, fecha_nacimiento, rfc, phone, email, password, homoclave=None):
        user = self.model(
            name=name,
            last_name=last_name,
            username=str(uuid.uuid4()),
            fecha_nacimiento=fecha_nacimiento,
            token=random_number(4),
            rfc=rfc,
            homoclave=homoclave,
            phone=phone,
            email=email,
            password=password,
        )

        user.is_admin = False
        user.is_active = False
        user.is_client = True
        user.is_new = True
        user.tipo_persona_id = 2
        user.save(using=self._db)
        return user

    def create_admin_razon_social(self, name, last_name, fecha_nacimiento, phone, email, password):
        user = self.model(
            name=name,
            last_name=last_name,
            username=str(uuid.uuid4()),
            fecha_nacimiento=fecha_nacimiento,
            token=random_number(4),
            phone=phone,
            email=email,
            password=password,
        )

        user.is_admin = False
        user.is_active = False
        user.is_client = True
        user.is_new = True
        user.tipo_persona_id = 2
        user.save(using=self._db)
        return user

    def create_admin_cuenta_eje(self, name, last_name, fecha_nacimiento, phone, email, password):
        user = self.model(
            name=name,
            last_name=last_name,
            username=str(uuid.uuid4()),
            fecha_nacimiento=fecha_nacimiento,
            phone=phone,
            email=email,
            password=password,
        )

        user.is_admin = True
        user.is_active = True
        user.is_client = True
        user.is_new = True
        user.state = True
        user.set_password(password)
        user.tipo_persona_id = 2
        user.save(using=self._db)
        return user

    def create_centro_costo(self, centro_costo, razon_social, rfc, banco_clabe, clave_traspaso):
        user = self.model(
            name=centro_costo,
            username=str(uuid.uuid4()),
            email=f"{razon_social}{rfc}",
            last_name=razon_social,
            rfc=rfc,
            banco_clabe=banco_clabe,
            clave_traspaso=clave_traspaso
        )

        user.is_admin = False
        user.is_active = False
        user.is_client = True
        user.is_new = True
        user.tipo_persona_id = 1
        user.fecha_nacimiento = dt.datetime.now()
        user.save(using=self._db)
        return user

    # (ChrGil 2021-12-07) Crea un representante legal y regresa un objeto persona
    def create_representante(self, nombre: str, paterno: str, materno: str, nacimiento, rfc: str, homoclave: str,
                             email: str, telefono: str):

        obj = self.model(
            name=nombre,
            last_name=f"{paterno}*{materno}",
            username=str(uuid.uuid4()),
            email=email,
            fecha_nacimiento=nacimiento,
            phone=telefono,
            rfc=rfc,
            homoclave=homoclave,
            is_active=False,
            is_client=True,
            is_new=True,
            tipo_persona_id=2,
            state=True
        )

        obj.save(using=self._db)
        return obj

    # (ChrGil 2021-12-07) Crea una razón social y regresa un objeto persona
    def create_razon_social_v2(
            self,
            razon_social: str,
            giro: str,
            rfc: str,
            fecha_constitucion: dt.date,
            clb_interbancaria_uno: str,
            clabeinterbancaria_dos: Union[str, None],
            centro_costos_name: Union[str, None],
    ):

        email = razon_social.replace(" ", "") + random_number(4) + rfc + random_number(4)
        obj = self.model(
            name=razon_social if centro_costos_name is None else centro_costos_name,
            last_name=razon_social,
            username=str(uuid.uuid4()),
            email=email.lower(),
            giro=giro,
            rfc=rfc.upper(),
            clabeinterbancaria_uno=clb_interbancaria_uno,
            clabeinterbancaria_dos=clabeinterbancaria_dos,
            fecha_nacimiento=fecha_constitucion,
            is_active=False,
            is_client=True,
            is_new=True,
            tipo_persona_id=1
        )

        obj.save(using=self._db)
        return obj

    def beneficiario(self, name, last_name, fecha_nacimiento, phone, email, password, rfc, motivo):
        user = self.model(
            name=name,
            last_name=last_name,
            phone=phone,
            email=email,
            fecha_nacimiento=fecha_nacimiento,
            password=make_password(password),
            motivo=motivo,
            rfc=rfc,
            username=str(uuid.uuid4()),
            state=True
        )

        user.is_admin = False
        user.is_active = True
        user.is_client = True
        user.is_new = True
        user.tipo_persona_id = 2
        user.save(using=self._db)
        return user

    # (ChrGil 2022-03-02) procedimiendo para añadir cliente externo
    def create_cliente_externo_fisico(self, **kwargs):
        user = self.model(
            name=kwargs.get('name'),
            last_name=kwargs.get('last_name'),
            phone=kwargs.get('phone'),
            email=kwargs.get('email'),
            fecha_nacimiento=datetime.date.today(),
            rfc=kwargs.get('rfc'),
            homoclave=kwargs.get('homoclave'),
            password="Temporal.123",
            username=str(uuid.uuid4()),
            state=False
        )
        user.is_admin = False
        user.is_active = True
        user.state = True
        user.is_client = True
        user.is_new = True
        user.tipo_persona_id = 2
        user.save(using=self._db)
        return user

    # (AAF 2022-01-03) procedimiendo para añadir cliente externo
    # (AAF 2022-01-06) se añade homoclabe
    def cliente_Externo(self,name, last_name, fecha_nacimiento, phone, email, password: None,rfc, homoclave):
        if password == None:
            password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))
        user = self.model(
            name=name,
            last_name=last_name,
            phone=phone,
            email=email,
            fecha_nacimiento=fecha_nacimiento,
            password=make_password(password),
            rfc=rfc,
            username=str(uuid.uuid4()),
            homoclave=homoclave,
            state=False
        )
        user.is_admin = False
        user.is_active = False
        user.is_client = True
        user.is_new = True
        user.tipo_persona_id = 2
        user.save(using=self._db)
        return user

    # (ChrGil 2022-01-05) Crear personal externo
    def create_personal_externo(
            self,
            name: str,
            last_name: str,
            birth_date: dt.date,
            rfc: str,
            mail: str,
            description_activities: str,
            password: str
    ):

        user = self.model(
            email=self.normalize_email(mail),
            name=name,
            last_name=last_name,
            username=str(uuid.uuid4()),
            fecha_nacimiento=birth_date,
            rfc=rfc,
            motivo=description_activities,
            password=password,
            state=True
        )
        user.is_superuser = False
        user.is_staff = False
        user.is_active = False
        user.is_client = True
        user.is_new = True
        user.tipo_persona_id = 2
        user.set_password(user.password)
        user.save(using=self._db)
        return user.id

    def create_colaborador(self, **kwargs):
        colaborador = self.model(
            email=kwargs.get('email'),
            password=kwargs.get('password', ''),
            username=str(uuid.uuid4()),
            fecha_nacimiento=kwargs.get('fecha_nacimiento'),
            name=kwargs.get('name'),
            phone=kwargs.get('phone'),
            tipo_persona_id=2,
            state=False,
            last_name='*'
        )
        colaborador.save(using=self._db)
        return colaborador

    def update_cost_center(self, **kwargs):
        return (
            super()
            .get_queryset()
            .select_related()
            .filter(
                id=kwargs.get('cost_center_id')
            )
            .update(
                name=kwargs.get('cost_center_name'),
                last_name=kwargs.get('cost_center_razon_social'),
                rfc=kwargs.get('rfc'),
                # banco_clabe=kwargs.get('banco'),
                # clave_traspaso=kwargs.get('clave_traspaso'),
            )
        )

    def update_representante(self, **kwargs):
        last_name = f"{kwargs.get('paterno')} {kwargs.get('materno')}"

        return (
            super()
            .get_queryset()
            .select_related()
            .filter(
                id=kwargs.get('representate_id')
            )
            .update(
                name=kwargs.get('nombre'),
                last_name=last_name,
                rfc=kwargs.get('rfc'),
                fecha_nacimiento=kwargs.get('nacimiento'),
                homoclave=kwargs.get('homoclave'),
                email=kwargs.get('email'),
                phone=kwargs.get('telefono'),
            )
        )


    def filter_admins_polipay(self, name: str, email: str):
        if name == 'null':
            name = ''
        if email == 'null':
            email = ''
        return (
            super()
                .get_queryset()
                # .select_related('tipo_pago', 'status_trans')
                .filter(name__icontains=name,
                        email__icontains=email
                        )
                .filter(Q(is_staff=True) | Q(is_superuser=True))
                .values('id','name', 'last_name', 'email'
                ))


# (ChrGil 2021-11-19) Consultas internas al modelo de usuarios
class QueryPersonaManager(models.Manager):
    # (ChrGil 2021-11-19) Filtra el nombre, apellido y correo atravez de un listado de id de personas
    def list_person(self, list_ids: List[Dict]):
        return (
            super()
            .get_queryset()
            .filter(
                id__in=list_ids,
                state=True
            )
            .values(
                'id',
                'name',
                'last_name',
                'email'
            )
        )

    def get_person_object(self, person_id: int):
        return (
            super()
            .get_queryset()
            .get(
                id=person_id,
            )
            .get_admin()
        )

    # (ChrGil 2022-01-17) Regresa un diccionario de datos necesarios para el inicio de sesión (Polipay Token)
    def get_info_login(self, email: str) -> Dict[str, Any]:
        return (
            super()
            .get_queryset()
            .filter(email=email)
            .values(
                'id',
                'email',
                'password',
                'is_superuser',
                'is_staff',
                'token_device_app_token',
                'is_active',
                'name'
            )
            .first()
        )

    # (ChrGil 2022-01-17) Regresa un diccionario de datos necesarios para el inicio de sesión (Polipay Token)
    def get_info_person(self, user_id: str) -> Dict[str, Any]:
        return (
            super()
            .get_queryset()
            .filter(
                id=user_id,
                state=True
            )
            .values(
                'id',
                'email',
                'password',
                'is_superuser',
                'is_staff',
                'token_device_app_token',
                'is_active',
                'name',
                'last_name',
                'tipo_persona_id',
                'token_device',
                'rfc'
            )
            .first()
        )
