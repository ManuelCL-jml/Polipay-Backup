import datetime
from decimal import Decimal
from typing import List, Dict, Union, Any, ClassVar

from django.db import models, OperationalError

from django.db.models import Q


# (ChrGil) Manager del modelo Domicilio
class ManagerDomicilio(models.Manager):
    def create_address(self, **kwargs):
        self.model(
            codigopostal=kwargs.get('codigopostal'),
            colonia=kwargs.get('colonia'),
            alcaldia_mpio=kwargs.get('alcaldia_mpio'),
            estado=kwargs.get('estado'),
            calle=kwargs.get('calle'),
            no_exterior=kwargs.get('no_exterior'),
            no_interior=kwargs.get('no_interior'),
            pais=kwargs.get('pais'),
            domicilioPersona_id=kwargs.get('person_id')
        ).save(using=self._db)

    def add_address_rs(self, codigopostal, colonia, alcaldia_mpio, estado, calle, no_exterior, no_interior, pais,
                       person_id):
        address = self.model(
            codigopostal=codigopostal,
            colonia=colonia,
            alcaldia_mpio=alcaldia_mpio,
            estado=estado,
            calle=calle,
            no_exterior=no_exterior,
            no_interior=no_interior,
            pais=pais,
            domicilioPersona_id=person_id
        )
        address.historial = False
        address.save(using=self._db)
        return address


# (ChrGil 2021-11-10) Manager para el modelo Tarjeta
class ManagerTarjeta(models.Manager):

    # (ChrGil 2021-11-10) Busqueda de tarjeta de un personal externo (regresa una listado de cuentas)
    def card_search(self, client_id: int):
        list_card_data: List[Dict] = (
            super()
                .get_queryset()
                .select_related('cuenta')
                .filter(
                clientePrincipal_id=client_id,
                status='00',
                is_active=True
            )
                .values(
                'id',
                'cuenta__persona_cuenta__name',
                'cuenta__persona_cuenta__last_name',
                'cuenta__persona_cuenta__email',
                'cuenta__cuenta',
                'is_active',
                'tarjeta',
                'status'
            )
        )

        return list_card_data

    # (ChrGil 2022-01-14) Regresa el ultimo id de la clave empleado
    def get_last_clave_empleado(self) -> str:
        return (
            super()
                .get_queryset()
                .filter(
                ClaveEmpleado__isnull=False
            )
                .order_by('id')
                .values_list('ClaveEmpleado', flat=True).last()
        )

    def list_cards_company(self, company_id: int,  num_tarjeta: int, email:str):
        if num_tarjeta == 'null':
            num_tarjeta = ''

        if email == 'null':
            email = ''
        return (
            super()
                .get_queryset()
                .filter(
                    clientePrincipal_id=company_id,
                    tarjeta__icontains=num_tarjeta,
                    cuenta__persona_cuenta__email__icontains=email
            ).values(
                'TarjetaId',
                'tarjeta',
                'fecha_register',
                'cuenta__persona_cuenta__email',
                'statusInterno__nombreStatus'
            )
        )

    def list_cards_all_company(self, company_id: List[int], num_tarjeta: int, name_company: str):
        if num_tarjeta == 'null':
            num_tarjeta = ''
        if name_company == 'null':
            name_company = ''
        return (
            super()
                .get_queryset()
                .filter(
                clientePrincipal_id__in=company_id,
                tarjeta__icontains=num_tarjeta,
                clientePrincipal__name__icontains=name_company
            ).values(
                'TarjetaId',
                'tarjeta',
                'fecha_register',
                'clientePrincipal__name',
                'statusInterno__nombreStatus'
            )
        )


# (ChrGil 2021-11-10) Manager para el modelo Cuenta
class CuentaManager(models.Manager):
    _NUMBER_DECIMALS: ClassVar[int] = 4

    def create_account(self, **kwargs):
        self.model(
            cuenta=kwargs.get('cuenta'),
            persona_cuenta_id=kwargs.get('person_id'),
            cuentaclave=kwargs.get('clabe'),
            rel_cuenta_prod_id=kwargs.get('product_id'),
            is_active=True
        ).save(using=self.db)

    def get_info_with_user_id(self, owner: int) -> Union[None, Dict[str, Any]]:
        return (
            super()
            .get_queryset()
            .filter(
                persona_cuenta_id=owner,
                is_active=True
            )
            .values(
                'id',
                'monto',
                'cuenta',
                'cuentaclave',
                'persona_cuenta_id',
                'persona_cuenta__name',
                "persona_cuenta__rfc",
                'persona_cuenta__tipo_persona_id',
                "persona_cuenta__last_name",
            )
            .first()
        )

    # (ChrGil 2022-02-07) Obtener info de la cuenta de usuario filtrando por numero de cuenta
    def get_info_with_account_number(self, numero_cuenta: str) -> Union[None, Dict[str, Any]]:
        return (
            super()
            .get_queryset()
            .filter(
                Q(cuenta=numero_cuenta) |
                Q(cuentaclave=numero_cuenta)
            )
            .values(
                'id',
                'monto',
                'cuentaclave',
                'persona_cuenta_id',
            )
            .first()
        )

    # (ChrGil 2022-02-07) Obtener producto id asociado a la cuenta
    def get_product(self, person_id: int) -> Union[None, Dict[str, Any]]:
        return (
            super()
                .get_queryset()
                .select_related('rel_cuenta_prod', 'persona_cuenta')
                .filter(persona_cuenta_id=person_id)
                .values('rel_cuenta_prod_id')
                .first()
        )

    # (ChrGil 2021-11-24) Regresa un objeto de tipo cuenta para acceder a atributos y/o metodos
    def get_object_cuenta(self, cost_center_id: int):
        return (
            super()
                .get_queryset()
                .select_related('persona_cuenta')
                .get(persona_cuenta_id=cost_center_id)
        )

    # (ManuelCl 2021-11-29 ) Se crea metodo para obtener  datos de las cuentas de centros de costo atraves de un listado
    def filter_account_cost_center(self, list_cost_center_id: List[int]):
        return (
            super()
                .get_queryset()
                .select_related('persona_cuenta')
                .filter(
                persona_cuenta_id__in=list_cost_center_id,
                is_active=True
            )
                .values('persona_cuenta_id', 'persona_cuenta__name', 'cuenta', 'cuentaclave', 'monto')
        )

    # ManuelCL 2021-12-28 (Se creo metodo para obtener unicamente el numero de cuenta de los centros de costos)
    def filter_only_account_cost_centers(self, list_cost_center_id: List[int]):
        return (
            super()
                .get_queryset()
                .select_related('persona_cuenta')
                .filter(
                persona_cuenta_id__in=list_cost_center_id,
                is_active=True
            )
                .values('cuenta')
        )

    def filter_account_transaction_cost_centers(self, list_cost_center_id: List[int], account_number):
        if account_number == 'null':
            account_number = ''
        return (
            super()
                .get_queryset()
                .select_related('persona_cuenta')
                .filter(
                persona_cuenta_id__in=list_cost_center_id,
                cuenta__icontains=account_number,
                is_active=True
            )
                .values('persona_cuenta__name', 'cuenta', 'cuentaclave')
        )

    def filter_account_clientes_externos(self, list_clientes_externos_id: List[int]):
        return (
            super()
            .get_queryset()
            .select_related('persona_cuenta')
            .filter(
                persona_cuenta_id__in=list_clientes_externos_id,
                is_active=True
            )
            .values(
                'persona_cuenta_id',
                'persona_cuenta__name',
                'persona_cuenta__last_name',
                'persona_cuenta__email',
                'cuenta',
                'cuentaclave'
            )
            .order_by('-persona_cuenta_id')
        )

    # (ChrGil 2022-01-24) Obtener información de la razon social POLIPAY COMISSION
    def get_info_polipay_comission(self, cuenta_eje_id: int):
        return (
            super()
            .get_queryset()
            .filter(
                persona_cuenta_id=cuenta_eje_id
            )
            .values(
                'cuenta',
                'cuentaclave',
                'persona_cuenta_id',
                'persona_cuenta__name',
                'persona_cuenta__name_stp',
                'persona_cuenta__rfc',
                'monto'
            )
            .first()
        )

    # (ChrGil 2022-01-24) Actualiza cuenta
    def update_account(self, person_id: int, **kwargs):
        return (
            super()
                .get_queryset()
                .select_related('persona_cuenta')
                .filter(
                persona_cuenta_id=person_id
            )
                .update(**kwargs)
        )

    def deposit_amount(self, owner: int, amount: float):
        try:
            instance = (
                super()
                .get_queryset()
                .select_for_update()
                .get(persona_cuenta_id=owner)
            )
            _amount: float = instance.monto
            _amount += float(amount)
            instance.monto = _amount
            instance.save()
        except OperationalError as e:
            self.deposit_amount(owner, amount)

    def withdraw_amount(self, owner: int, amount: Union[int, float, Decimal]) -> bool:
        try:
            instance = (
                super()
                .get_queryset()
                .select_for_update()
                .get(persona_cuenta_id=owner)
            )

            _amount = instance.monto
            _amount -= float(amount)
            instance.monto = _amount
            instance.save()
            return _amount

        except OperationalError as e:
            self.withdraw_amount(owner, amount)


# (ChrGil 2021-11-10) Manager para el modelo GrupoPersona
class GrupoPersonaManager(models.Manager):

    # (ChrGil 2022-03-18) Regresa un booleano si el centro de costos existe
    def exist(self, **kwargs) -> bool:
        return (
            super()
                .get_queryset()
                .filter(
                empresa_id=kwargs.pop('empresa_id'),
                person_id=kwargs.pop('person_id'),
                relacion_grupo_id=kwargs.pop('group_id'),
                **kwargs
            )
                .exists()
        )

    def count_cost_center(self, owner: int):
        return (
            super()
                .get_queryset()
                .select_related(
                'person',
                'relacion_grupo'
            )
                .filter(
                person_id=owner,
                relacion_grupo_id=8
            ).count()
        )

    # (ChrGil 2022-03-07) Crea objeto de tipo grupo persona
    def create_grupo_persona(self, **kwargs):
        return self.model(
            empresa_id=kwargs.get('empresa_id'),
            person_id=kwargs.get('person_id'),
            relacion_grupo_id=kwargs.get('type_group'),
            nombre_grupo=kwargs.get('group_name')
        )

    # (ChrGil 2021-11-19) Listar id de los administrativos de una cuenta eje
    def get_list_ids_admin(self, company_id: int):
        return (
            super()
                .get_queryset()
                .select_related(
                'empresa',
                'relacion_grupo'
            )
                .filter(
                empresa_id=company_id,
                is_admin=True
            )
                .filter(
                Q(relacion_grupo_id=1) | Q(relacion_grupo_id=3)
            )
                .values_list('person_id', flat=True)
        )

    # (ManuelCalixtro 29-11-2021) Se creo metodo para listar los id de centros de costos de una cuenta eje
    def get_list_cost_center_id(self, nombre: str, empresa_id: int):
        if nombre == 'null':
            nombre = ''
        return (
            super()
                .get_queryset()
                .filter(
                empresa_id=empresa_id,
                nombre_grupo__icontains=nombre,
                relacion_grupo_id=5
            )
                .values_list('person_id', flat=True)
        )

    # (ManuelCalixtro 24-03-2022) Metodo para obtener centros de costos activos de una cuenta eje
    def get_list_actives_cost_centers_id(self, empresa_id: int):
        return (
            super()
            .get_queryset()
            .filter(
                empresa_id=empresa_id,
                person__state=True,
                relacion_grupo_id=5,
                empresa__is_active=True,
                person__is_active=True
            )
            .values_list('person_id', flat=True)
        )

    # (ManuelCalixtro 24-03-2022) Se creo metodo para obtener el id del centro de costos
    def get_centro_costos_id(self, empresa_id: int):
        return (
            super()
            .get_queryset()
            .filter(
                person_id=empresa_id,
                person__state=True,
                relacion_grupo_id=5,
                empresa__is_active=True,
                person__is_active=True
            )
            .values_list('person_id', flat=True)
        )

    # (ManuelCalixtro 24-03-2022) Metodo para obtener los clientes externos fisicos activos
    def get_list_actives_clientes_externo(self, empresa_id: List[int]):
        return (
            super()
            .get_queryset()
            .filter(
                empresa_id__in=empresa_id,
                person__state=True,
                relacion_grupo_id=9
            )
            .values_list('person_id', flat=True)
        )

    # (ChrGil 2021-11-26) Regresa un objeto del modelo grupoPersona de un centro de costos
    def get_object_cost_center(self, cost_center_id: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'empresa',
                'relacion_grupo'
            )
            .get(
                empresa_id=cost_center_id,
                relacion_grupo_id=4
            )
        )

    # (ChrGil 2021-11-26) Regresa un objeto del modelo grupoPersona de una cuenta eje
    def get_object_cuenta_eje(self, cuenta_eje_id: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'empresa',
                'relacion_grupo'
            )
            .get(
                empresa_id=cuenta_eje_id,
                relacion_grupo_id=1
            )
        )

    # (ChrGil 2021-11-26) Regresa un objeto del modelo GrupoPersona que hace referencia a un administrativo de empresa
    def get_object_admin_company(self, person_id: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'relacion_grupo',
                'person',
            )
            .filter(
                relacion_grupo_id__in=[1, 3, 14]
            )
            .get(
                person_id=person_id
            )
        )

    # (ChrGil 2022-01-06) Regresa un objeto de grupoPersona (Para Adelante Zapopan) (Temporal)
    def get_object_admin_company_adelante_zapopan(self, person_id: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'relacion_grupo',
                'person',
            )
            .filter(
                relacion_grupo_id=13
            )
            .get(
                person_id=person_id
            )
        )

    # ( AAF 2021-11-29) regresa datos de la empresa dada una persona
    def get_values_admin(self, company_id: int):
        return (
            super()
            .get_queryset()
            .filter(
                person_id=company_id,
            )
            .filter(
                relacion_grupo_id=5
            )
            .values('empresa_id')
        )

    # ( AAF 2021-11-29) devuelve los datos de la persona inferior dado un sup
    def get_persona(self, empresa_id: int, relacion: int):
        return (
            super()
            .get_queryset()
            .filter(
                empresa_id__in=empresa_id,
                relacion_grupo_id=relacion
            )
            .values(
                'person_id',
                'person__email',
                'person__name',
                'person__last_name',
                'empresa__name'
            )
        )

    # ( AAF 2021-11-29) regresa datos de la empresa dada una persona
    def get_values_empresa(self, persona_id: int, rel: int):
        return (
            super()
            .get_queryset()
            .filter(
                person_id=persona_id
            )
            .filter(
                relacion_grupo_id=rel
            )
            .values(
                'empresa_id',
                'empresa__name'
            )
        )

    # (ChrGil 2022-01-17) Regresa un booleado si es admin o colaborador
    def is_admin_or_collaborator(self, person_id: int) -> bool:
        return (
            super()
                .get_queryset()
                .select_related(
                'person_id',
                'relacion_grupo_id'
            )
                .filter(
                person_id=person_id,
                relacion_grupo_id__in=[1, 3, 14]
            )
                .exists()
        )

    # (ChrGil 2022-01-25) Regresa un booleano
    def belonging_to_cuenta_eje(self, cuenta_eje_id: int, razon_social_id: int) -> bool:
        return (
            super()
                .get_queryset()
                .select_related(
                'relacion_grupo',
                'person',
                'empresa'
            )
                .filter(
                empresa_id=cuenta_eje_id,
                person_id=razon_social_id,
                relacion_grupo_id=5
            )
                .exists()
        )

    def get_name_cuenta_eje(self, person_id: int) -> Dict:
        person: dict = (
            super()
            .get_queryset()
            .filter(
                Q(person_id=person_id) | Q(empresa_id=person_id)
            ).values(
                "empresa_id",
                "empresa__name_stp",
                "empresa__name",
            ).first()
        )

        empresa: dict = (
            super()
            .get_queryset()
            .filter(
                person_id=person.get("empresa_id")
            )
            .values(
                "empresa_id",
                "empresa__name_stp",
                "empresa__name",
            ).first()
        )

        if empresa:
            return empresa
        return person

    def search_person_in_grupo_persona(self, person_id: int, relacion_grupo_list: List[int]) -> Dict:
        return (
            super()
            .get_queryset()
            .filter(
                Q(person_id=person_id) | Q(empresa_id=person_id),
                relacion_grupo_id__in=relacion_grupo_list
            )
            .values(
                'id',
                'empresa_id',
                'relacion_grupo_id',
                'person_id',
                'nombre_grupo',
            )
            .first()
        )

    def all_admin_cuenta_eje(self, company_id: int) -> List[int]:
        return (
            super()
            .get_queryset()
            .filter(
                Q(relacion_grupo_id=1) | Q(relacion_grupo_id=3) | Q(relacion_grupo_id=8),
                empresa_id=company_id,
            )
            .values_list(
                "person_id",
                flat=True
            )
        )


# (ChrGil 2021-11-10) Manager para el modelo Documentos
class DocumentsManager(models.Manager):

    # (ChrGil 2022-03-08) Actualizar documentos
    def update_document(self, **kwargs):
        return (
            super()
                .get_queryset()
                .select_related(
                'relacion_grupo',
                'person',
                'empresa'
            )
                .filter(
                id=kwargs.pop('document_id')
            )
                .update(
                userauth=kwargs.pop('user_auth'),
                comentario=kwargs.pop('comment'),
                status=kwargs.pop('status'),
                authorization=True,
                dateauth=datetime.datetime.now(),
                dateupdate=datetime.datetime.now(),
                **kwargs
            )
        )

    # (ChrGil 2021-12-07) Metodo para crear un documento
    def create_document(self, tipo: int, owner: int, comment: Union[str, None]):
        document = self.model(tdocumento_id=tipo, person_id=owner, comentario=comment)
        document.save(using=self._db)
        return document

    # (ChrGil 2021-11-22) Regresa un listado de objetos, donde puedes acceder a sus atributos y metodos
    def get_url_aws_document_by_type(self, person_id: int, type_document: int):
        list_objs = (
            super()
                .get_queryset()
                .select_related('person')
                .filter(person_id=person_id, tdocumento_id=type_document)
        )

        if len(list_objs) > 2:
            return list_objs

        return list_objs[0].get_url_aws_document()

    # (Aboyts 2021-11-29) actualiza el documento enviado
    def get_documento_instance(self, documento_id: int):
        instance = (
            super()
                .get_queryset()
                .get(id=documento_id)
        )
        return instance


# (ChrGil 2022-01-26) Crear un registro de credenciales de acceso
class ManagerAccessCredentials(models.Manager):
    def create(self, owner: int, key: str, platform: str = 'M'):
        credentials = self.model(
            person_id=owner,
            credential_access=key,
            credential_app=platform
        )

        credentials.save(using=self._db)

    def all_keys(self, owner: int) -> List:
        return (
            super()
                .get_queryset()
                .select_related(
                'person'
            )
                .filter(person_id=owner)
        )

    def update_access_key(self, owner: int):
        return (
            super()
                .get_queryset()
                .select_related(
                'person'
            )
                .filter(person_id=owner)
                .update(credential_access='Public Key Expires')
        )

    def exists_key(self, owner: int, key: str) -> bool:
        return (
            super()
                .get_queryset()
                .select_related(
                'person'
            )
                .filter(person_id=owner, credential_access=key)
                .exists()
        )
