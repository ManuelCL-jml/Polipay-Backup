import datetime
import datetime as dt

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, ClassVar, NoReturn, Union, Dict, List

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, FieldDoesNotExist
from django.db import IntegrityError
from django.db.models import Q, FilteredRelation
from django.db.transaction import atomic
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework import status

from MANAGEMENT.ComissionPay.comission import RegistraOrdenDispersionMasivaIndividual
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from MANAGEMENT.Utils.utils import remove_equal_items, get_values_list, remove_asterisk, get_id_cuenta_eje, \
    calculate_commission, add_iva
from apps.api_dynamic_token.api.web.views.views_dynamic_token import ValidateTokenDynamic
from apps.api_dynamic_token.exc import JwtDynamicTokenException
from apps.api_stp.exc import StpmexException
from apps.commissions.models import Commission, Commission_detail
from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from apps.productos.exc import ProductException
from apps.transaction.api.web.serializers.serializers_dispersiones_masivas import SerializerTransMasivaProg, \
    SerializerDispersionIndividual, SerializerDispersionIndividualMassive, SerializerTransInidivudalProg, \
    SerializerTransactionPolipayComission
from apps.transaction.exc import DispersionesException
from apps.transaction.interface import RegistrationDispersionMassive, CreateDispersionProgramada, \
    CreateDispersionMassive, Dispersion, Disperse, SendMail, ChangeStatusMassive, \
    ChangeStatusIndividual, Comission
from apps.transaction.management import preparingNotification
from apps.transaction.messages import message_email
from apps.transaction.models import transferencia, transmasivaprod, TransMasivaProg, transferenciaProg

from apps.users.models import cuenta, persona, grupoPersona
from polipaynewConfig.settings import COST_CENTER_POLIPAY_COMISSION, COST_CENTER_INNTEC

DATE_FORMAT = '%Y-%m-%d %H:%M'


def strptime(date: Union[int, str]):
    return dt.datetime.strptime(str(date), DATE_FORMAT)


def _add_comission_transaction_id(transaction: transferencia, objs: List[Commission_detail]):
    t = [row.transaction_rel for row in objs]
    Commission_detail.objects.filter(transaction_rel__in=t).update(commission_record=transaction)


def _add_saldo_remanente(transaction: transferencia, current_amount: float, amount_transaction: float):
    saldo_remanente = current_amount
    saldo_remanente += amount_transaction
    transaction.saldo_remanente_beneficiario = saldo_remanente
    transaction.save()


class RequestDataDispersiones:
    total_amount: ClassVar[str]
    person_list: ClassVar[List[Dict[str, Any]]]

    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data
        self.validate_person_list()
        self.total_amount = self.get_total_amount

    def validate_person_list(self):
        self.person_list = remove_equal_items(key="account", list_data=self._request_data.get('PersonList'))

    @property
    def get_razon_social_id(self) -> int:
        return self._request_data.get('RazonSocialID')

    @property
    def get_observations(self) -> str:
        return self._request_data.get('observations')

    @property
    def get_dynamic_token(self) -> str:
        return self._request_data.get('auth').get('token')

    @property
    def is_shedule(self) -> bool:
        return self._request_data.get('IsShedule')

    @property
    def get_scheduled_date(self) -> Union[dt.date, None]:
        date = self._request_data.get('ScheduledDate')
        if date:
            scheduled_date = dt.datetime.strptime(str(date), DATE_FORMAT)
            return scheduled_date
        return None

    @property
    def get_group_name(self) -> str:
        return self._request_data.get('GroupName')

    @property
    def is_a_dispersion_massive(self) -> Union[bool, int]:
        if len(self.person_list) == 1:
            return 0
        if len(self.person_list) > 1:
            return True
        return False

    @property
    def get_all_accounts_beneficiario(self) -> List[str]:
        return get_values_list('account', self.person_list)

    @property
    def get_all_mail_beneficiarios(self) -> List[str]:
        return get_values_list('mail', self.person_list)

    @property
    def get_all_amount_beneficiario(self) -> List[float]:
        return get_values_list('amount', self.person_list)

    @property
    def get_name_beneficiario_is_not_assive(self) -> Union[str, None]:
        if not self.is_a_dispersion_massive:
            return remove_asterisk(get_values_list('name', self.person_list)[0])
        return None

    @property
    def get_total_amount(self) -> float:
        return round(sum(get_values_list('amount', self.person_list)), 2)

    @property
    def get_token_dynamic(self):
        return self._request_data.get('auth').get('token')


# (ChrGil 2022-02-07) Alamacena en variables de clase la información del emisor (razon social y administrador)
class GetInfoEmisor:
    info_account_razon_social: ClassVar[Dict[str, Any]]
    info_razon_social: ClassVar[Dict[str, Any]]
    info_admin: ClassVar[Dict[str, Any]]
    info_account_cuenta_eje: ClassVar[Dict[str, Any]]

    def __init__(self, razon_social_id: int, admin: persona):
        self._razon_social_id = razon_social_id
        self._admin = admin

        self._get_info_account_cuenta_eje()
        is_cuenta_eje = self._validate_is_cuenta_eje

        if is_cuenta_eje:
            if self.info_account_cuenta_eje.get('rel_cuenta_prod_id') != 1:
                raise ValueError('No es posible hacer una dispersión desde la cuenta eje con tu producto actual')

            self._get_info_account_razon_social()
            self._get_info_razon_social()
            self._get_info_admin()

        if not is_cuenta_eje:
            if not self._belongs_parent_account:
                raise ValueError('Cuenta eje y/o centro de costos no valido o no existe')

            self._get_info_account_razon_social()
            self._get_info_razon_social()
            self._get_info_admin()

    @property
    def _validate_is_cuenta_eje(self) -> bool:
        return grupoPersona.objects.annotate(
            company=FilteredRelation(
                'empresa', condition=Q(empresa__is_active=True) & Q(empresa__state=True) & Q(empresa__tipo_persona_id=1)
            ),
        ).filter(company__id=self._razon_social_id, relacion_grupo_id=1).exists()

    # Validamos que el centro de costos exista y pertenezca a la cuenta eje del cliente actual
    @property
    def _belongs_parent_account(self) -> bool:
        return grupoPersona.objects.annotate(
            persona=FilteredRelation(
                'person', condition=Q(person__is_active=True) & Q(person__state=True) & Q(person__tipo_persona_id=1)
            ),
        ).filter(
            persona__id=self._razon_social_id,
            relacion_grupo_id=5,
            empresa_id=self.info_account_cuenta_eje.get('persona_cuenta_id')
        ).exists()

    def _get_info_account_cuenta_eje(self):
        self.info_account_cuenta_eje = cuenta.objects.select_related(
            'persona_cuenta_id',
            'rel_cuenta_prod'
        ).filter(
            persona_cuenta_id=get_id_cuenta_eje(self._admin.get_only_id())
        ).values(
            'id',
            'cuenta',
            'cuentaclave',
            'rel_cuenta_prod_id',
            'persona_cuenta_id',
            'persona_cuenta__name_stp',
        ).first()

    def _get_info_account_razon_social(self):
        self.info_account_razon_social = cuenta.objects.select_related('persona_cuenta', 'rel_cuenta_prod').filter(
            persona_cuenta_id=self._razon_social_id,
            is_active=True
        ).values(
            'id',
            'cuentaclave',
            'monto',
            'rel_cuenta_prod_id',
            'is_active'
        ).first()

    def _get_info_razon_social(self):
        self.info_razon_social = persona.objects.filter(
            id=self._razon_social_id,
            is_active=True,
            state=True,
            tipo_persona_id=1
        ).values(
            'id',
            'name',
            'rfc',
        ).first()

    def _get_info_admin(self):
        self.info_admin = {
            "id": self._admin.get_only_id(),
            "name": f"{self._admin.name} {remove_asterisk(self._admin.last_name)}",
            "email": self._admin.get_email()
        }


# (ChrGil 2022-02-10) Obtiene las comisiones de la cuenta eje, si el producto es empresa
class GetInfoComissionEmisor:
    info: ClassVar[Dict[str, Any]]

    def __init__(self, emisor: GetInfoEmisor):
        self._emisor = emisor
        self.info = self._get_info_comission

        if not self.info:
            raise ValueError('Los serivicios no han sido asignados a tu cuenta eje')

    @property
    def _get_info_comission(self) -> Dict[str, Any]:
        cuenta_eje = self._emisor.info_account_cuenta_eje.get('persona_cuenta_id')

        return Commission.objects.select_related('person_debtor', 'person_payer', 'commission_rel').filter(
            Q(person_payer_id=cuenta_eje) | Q(person_debtor_id=cuenta_eje)
        ).filter(
            commission_rel__servicio__service_id=2
        ).values(
            'id',
            'commission_rel_id',
            'commission_rel__servicio__service__id',
            'commission_rel__servicio__product_id',
            'commission_rel__servicio__product__nombre',
            'commission_rel__percent',
            'commission_rel__type',
            'commission_rel__type_id',
        ).first()


# (ChrGil 2021-11-01) Clase que se encarga de crear el identificador de una transacción masiva
class RegisterMassiveDispersion(RegistrationDispersionMassive):
    _default_status: ClassVar[int] = 5

    def __init__(self, request_data: RequestDataDispersiones, emisor: GetInfoEmisor):
        self._request_data = request_data
        self._emisor = emisor
        self._raise_errros()
        self.massive_id = self._create

    def _raise_errros(self):
        if self._request_data.is_shedule:
            self._default_status = 2

        if not self._request_data.is_shedule:
            self._default_status = 5

    @property
    def _create(self) -> int:
        return transmasivaprod.objects.create_transaction_massive(
            observations=self._request_data.get_observations,
            status=self._default_status,
            user_admin_id=self._emisor.info_admin.get('id'),
        ).get_only_id()


# (ChrGil 2021-11-03) Clase que se encarga de crear el registro de una transferencia masiva programada
class RegisterDispersionMasivaProgClass(CreateDispersionProgramada):
    _serializer_class: ClassVar[SerializerTransMasivaProg] = SerializerTransMasivaProg
    _dispersion: ClassVar[CreateDispersionMassive]

    def __init__(self, request_data: RequestDataDispersiones, dispersion: RegisterMassiveDispersion):
        self._dispersion = dispersion
        self._request_data = request_data

        if request_data.is_shedule:
            self.create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "masivaReferida_id": self._dispersion.massive_id,
            "fechaProgramada": self._request_data.get_scheduled_date,
            "fechaEjecucion": self._request_data.get_scheduled_date,
        }

    def create(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        serializer.create()


# (ChrGil 2021-11-02) Crear una transacción individual
class DispersionIndividual(Dispersion):
    _serializer_class: ClassVar[SerializerDispersionIndividual] = SerializerDispersionIndividual
    transaction_id: ClassVar[int]

    def __init__(self, request_data: RequestDataDispersiones, emisor: GetInfoEmisor):
        self._request_data = request_data
        self._emisor = emisor
        self._create()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "nombre_emisor": self._emisor.info_razon_social.get('name'),
            "cuenta_emisor": self._emisor.info_account_razon_social.get('cuentaclave'),
            "cuentatransferencia_id": self._emisor.info_account_razon_social.get('id'),
            "monto_cuenta_emisor": self._emisor.info_account_razon_social.get('monto'),
            "is_active_cuenta_emisor": self._emisor.info_account_razon_social.get('is_active'),
            "emisor_empresa_id": self._emisor.info_admin.get('id'),
            "total_amount": self._request_data.total_amount,
            "massive_trans_id": None,
            "programada": False,
            "empresa": self._emisor.info_account_cuenta_eje.get("persona_cuenta__name_stp"),
            "observations": self._request_data.get_observations
        }

    @property
    def _data(self) -> List[Dict[str, Any]]:
        return self._request_data.person_list[0]

    def _create(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        self.transaction_id = serializer.create()


# (ChrGil 2021-11-03) Clase que se encarga de crear el registro de una transferencia individual programada
class RegisterDispersionProgramadaIndividual(CreateDispersionProgramada):
    _serializer_class: ClassVar[SerializerTransInidivudalProg] = SerializerTransInidivudalProg
    _dispersion: ClassVar[CreateDispersionMassive]

    def __init__(self, request_data: RequestDataDispersiones, dispersion: DispersionIndividual):
        self._dispersion = dispersion
        self._request_data = request_data

        if request_data.is_shedule:
            self.create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "transferReferida_id": self._dispersion.transaction_id,
            "fechaProgramada": self._request_data.get_scheduled_date,
            "fechaEjecucion": self._request_data.get_scheduled_date,
        }

    def create(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        serializer.create()


# (ChrGil 2022-02-10) Cambia estado de una transacción individual
class ChangeStatusDispersionIndividual(ChangeStatusIndividual):
    def __init__(self, dispersion: DispersionIndividual, emisor: GetInfoEmisor, request_data: RequestDataDispersiones):
        self._dispersion = dispersion
        self._emisor = emisor
        self._request_data = request_data
        self._raise_is_shedule(request_data.is_shedule)
        self._update()

    def _raise_is_shedule(self, is_shedule: bool) -> NoReturn:
        self._shedule = is_shedule

        # Pendiente
        if is_shedule:
            self._status_id = 9

        # Liquidada
        if not is_shedule:
            self._status_id = 1

    # (ChrGil 2022-01-14) Metodo que cambia el estado de las dispersiones individuales
    def _update(self) -> NoReturn:
        amount: float = 0.0

        for beneficiario in self._request_data.person_list:
            amount = self._emisor.info_account_razon_social.get('monto')
            amount -= beneficiario.get('amount')

        transferencia.objects.filter(
            id=self._dispersion.transaction_id
        ).update(
            date_modify=dt.datetime.now(),
            status_trans_id=self._status_id,
            saldo_remanente=round(amount, 2),
            programada=self._shedule
        )


# (ChrGil 2022-02-01) Crea una objeto de tipo transferencia
class DispersionIndividualMassiva(Dispersion):
    _serializer_class: ClassVar[SerializerDispersionIndividual] = SerializerDispersionIndividualMassive
    obj: ClassVar[transferencia]

    def __init__(self, dispersion_individual: Dict[str, Any], context_data: Dict[str, Any]):
        self._dispersion_individual = dispersion_individual
        self._context_data = context_data
        self._create()

    @property
    def _context(self) -> Dict[str, Any]:
        return self._context_data

    @property
    def _data(self) -> Dict[str, Any]:
        return self._dispersion_individual

    def _create(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        self.obj = serializer.create()


# (ChrGil 2021-11-02) Clase que se encargara de crear una transacción individual de manera masiva
class DispersionMassive(CreateDispersionMassive):
    def __init__(
            self,
            request_data: RequestDataDispersiones,
            massive_trans: RegisterMassiveDispersion,
            emisor: GetInfoEmisor,
    ):
        self._request_data = request_data
        self.massive_trans = massive_trans
        self._emisor = emisor

        if not isinstance(request_data.is_a_dispersion_massive, bool):
            raise ValueError('Debe agrega como minimo a una persona para realizar esta operación')

        if not isinstance(request_data.person_list, list):
            raise ValueError('Se esperaba un listado')

        if not isinstance(request_data.person_list[0], dict):
            raise ValueError('Se esperaba un objeto JSON')

        self._bulk_create_dispersion(self._create)

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "nombre_emisor": self._emisor.info_razon_social.get('name'),
            "cuenta_emisor": self._emisor.info_account_razon_social.get('cuentaclave'),
            "cuentatransferencia_id": self._emisor.info_account_razon_social.get('id'),
            "monto_cuenta_emisor": self._emisor.info_account_razon_social.get('monto'),
            "is_active_cuenta_emisor": self._emisor.info_account_razon_social.get('is_active'),
            "emisor_empresa_id": self._emisor.info_admin.get('id'),
            "total_amount": self._request_data.total_amount,
            "massive_trans_id": self.massive_trans.massive_id,
            "programada": self.massive_trans.is_shedule,
            "empresa": self._emisor.info_account_cuenta_eje.get("persona_cuenta__name_stp"),
            "observations": self._request_data.get_observations
        }

    @property
    def _data(self) -> List[Dict[str, Any]]:
        return self._request_data.person_list

    @property
    def _create(self) -> List[transferencia]:
        return [
            DispersionIndividualMassiva(dispersion, self._context).obj
            for dispersion in self._data
        ]

    # (ChrGil 2021-11-03) Metodo que crea masivamente las dispersiones
    def _bulk_create_dispersion(self, objs: List[transferencia]):
        transferencia.objects.bulk_create(objs)


# (ChrGil 2022-01-18) Cambia el estado de una dispersión a liquidada, si todo salio bien
class ChangeStatusDispersionMassive(ChangeStatusMassive):
    def __init__(
            self,
            request_data: RequestDataDispersiones,
            massive: RegisterMassiveDispersion,
            emisor: GetInfoEmisor
    ):
        self._massive = massive.massive_id
        self._monto_emisor = emisor.info_account_razon_social.get('monto')
        self._raise_is_shedule(request_data.is_shedule)
        self._bulk_update(self._update)

    def _raise_is_shedule(self, is_shedule: bool):
        self._shedule = is_shedule

        # Pendiente
        if is_shedule:
            self._status_id = 9

        # Liquidada
        if not is_shedule:
            self._status_id = 1

    @property
    def _list_dispersiones_masivas(self) -> List[transferencia]:
        return transferencia.filter_transaction.list_trasnfer_objs_massive(self._massive, type_page_id=4)

    # (ChrGil 2022-01-14) Metodo que cambia el estado de las dispersiones masivas
    @property
    def _update(self) -> List[transferencia]:
        objs = self._list_dispersiones_masivas
        i = 0

        for transfer in objs:
            transfer.date_modify = dt.datetime.now()
            transfer.status_trans_id = self._status_id
            transfer.programada = self._shedule
            self._monto_emisor -= transfer.monto
            i += 1
            transfer.saldo_remanente = round(self._monto_emisor, 2)

        return objs

    def _bulk_update(self, objs: List[transferencia]):
        transferencia.objects.bulk_update(
            objs=objs, fields=['saldo_remanente', 'status_trans_id', 'date_modify', 'programada'])


# (ChrGil 2022-01-03) Retira dinero de la cuenta del emisor
class WithdrawAmount(Disperse):
    def __init__(self, request_data: RequestDataDispersiones, emisor: GetInfoEmisor):
        self._emisor = emisor
        self.total_amount = request_data.total_amount
        self._razon_social_id = emisor.info_razon_social.get('id')
        self.update_amount()

    def update_amount(self) -> NoReturn:
        cuenta.objects.withdraw_amount(self._razon_social_id, self.total_amount)


# (ChrGil 2022-01-04) Envio de notificación al cliente
class SendNotificationDispersaBeneficiarios:
    def __init__(self, request_data: RequestDataDispersiones):
        self._request_data = request_data

        if not request_data.is_shedule:
            self._send_notification()

    def _send_notification(self) -> NoReturn:
        for account in self._request_data.get_all_accounts_beneficiario:
            preparingNotification(cuentaBeneficiario=account, opcion=3)


class SendMailEmisor(SendMail):
    def __init__(self, request_data: RequestDataDispersiones, emisor: GetInfoEmisor):
        self._request_data = request_data
        self._emisor = emisor
        self._send_mail()

    @property
    def _context_data_email(self, context: Union[None, Dict[str, Any]] = None) -> Dict[str, Any]:
        folio = f"PO-{dt.datetime.now().strftime('%Y%m%d%H%M')}"

        return {
            "folio": folio,
            "email": self._emisor.info_admin.get('email'),
            "observation": self._request_data.get_observations,
            "nombre_emisor": self._emisor.info_razon_social.get('name'),
            "fecha_operacion": dt.datetime.now(),
            "monto_total": self._request_data.get_total_amount,
            "nombre_grupo": self._request_data.get_group_name,
            "nombre_beneficiario": self._request_data.get_name_beneficiario_is_not_assive,
            "is_shedule": self._request_data.is_shedule,
            "fecha_programada": self._request_data.get_scheduled_date
        }

    def _send_mail(self) -> NoReturn:
        message_email(
            template_name='MailDispersionesEmisor.html',
            context=self._context_data_email,
            title='Dispersion',
            body=self._context_data_email.get('observation'),
            email=self._context_data_email.get('email')
        )


@dataclass
class SendMailBeneficiario(SendMail):
    def __init__(self, request_data: RequestDataDispersiones, emisor: GetInfoEmisor):
        self._request_data = request_data
        self._emisor = emisor

        if not request_data.is_shedule:
            self._send_mail()

    def _context_data_email(self, context: Union[None, Dict[str, Any]] = None) -> NoReturn:
        folio = f"{dt.datetime.now().strftime('%Y%m%d%H%S')}"

        return {
            "folio": folio,
            "name": context.get('name'),
            "fecha_operacion": dt.datetime.now(),
            "observation": self._request_data.get_observations,
            "nombre_emisor": self._emisor.info_razon_social.get('name'),
            "monto": context.get('amount')
        }

    def _send_mail(self) -> NoReturn:
        for context in self._request_data.person_list:
            message_email(
                template_name='MailDispersionesBeneficiario.html',
                context=self._context_data_email(context=context),
                title='Dispersion',
                body=self._request_data.get_observations,
                email=context.get('mail')
            )


# (ChrGil 2022-01-31) Obtiene la comision que se le va a cobrar al beneficiario
class ValidateProduct:
    _is_massive: ClassVar[bool]
    _productos: ClassVar[List[Dict[str, Any]]]
    comission: ClassVar[Union[None, GetInfoComissionEmisor]]

    def __init__(self, emisor: GetInfoEmisor):
        # (ChrGil 2022-02-10) Producto Empresa
        if emisor.info_account_cuenta_eje.get('rel_cuenta_prod_id') == 3:
            self.comission = GetInfoComissionEmisor(emisor).info

        if emisor.info_account_cuenta_eje.get('rel_cuenta_prod_id') != 3:
            self.comission = None


class TransactionInfo:
    list_transaction: ClassVar[List[Dict[str, Any]]]

    def __init__(self, **kwargs):
        self._massive_id = kwargs.get('massive_id', None)
        self._transaction_id = kwargs.get('transaction_id', None)

        if not self._massive_id:
            self.list_transaction = self._get_transaction_individual_objects

        if not self._transaction_id:
            self.list_transaction = self._get_transaction_massive_objects

    @property
    def _get_transaction_massive_objects(self) -> List[Dict[str, Any]]:
        return transferencia.objects.filter(
            masivo_trans_id=self._massive_id
        ).values(
            'id',
            'monto',
            'cta_beneficiario',
            'nombre_beneficiario',
            'rfc_curp_beneficiario',
            "nombre_emisor",
            "cuenta_emisor",
            "rfc_curp_emisor",
            "clave_rastreo",
            "concepto_pago",
            "fecha_creacion",
            "date_modify",
            "referencia_numerica",
            "empresa",
            "cuentatransferencia_id",
            "programada",
            "masivo_trans_id",
            "status_trans_id",
            "saldo_remanente",
            "transmitter_bank_id",
            "receiving_bank_id",
        )

    @property
    def _get_transaction_individual_objects(self) -> List[transferencia]:
        return transferencia.objects.filter(
            id=self._transaction_id
        ).values(
            'id',
            'monto',
            'cta_beneficiario',
            'nombre_beneficiario',
            'rfc_curp_beneficiario',
            "nombre_emisor",
            "cuenta_emisor",
            "rfc_curp_emisor",
            "clave_rastreo",
            "concepto_pago",
            "fecha_creacion",
            "date_modify",
            "referencia_numerica",
            "empresa",
            "cuentatransferencia_id",
            "programada",
            "masivo_trans_id",
            "status_trans_id",
            "saldo_remanente",
            "transmitter_bank_id",
            "receiving_bank_id",
        )


# (ChrGil 2022-02-16) Realiza el calculo y realiza el movimientos de la comisión negativa
class NegativeComission(Comission):
    total_amount: ClassVar[Decimal]

    def __init__(self, comission: GetInfoComissionEmisor, transaction_info: TransactionInfo):
        self._comission = comission
        self._transaction_info = transaction_info

        if self._comission.info.get('commission_rel__type') == 2:
            objs = self._calculate_comission
            self.objs = self._bulk_create(objs)
            self.total_amount = self._sum_total_amoun(objs)

    @staticmethod
    def _sum_total_amoun(objs: List[Commission_detail]) -> float:
        _total_amount: float = 0.0
        for row in objs:
            _total_amount += float(row.mount)

        return _total_amount

    @staticmethod
    def _bulk_create(objs: List[Commission_detail]) -> List[Commission_detail]:
        return Commission_detail.objects.bulk_create(objs)

    @property
    def _calculate_comission(self) -> List[Commission_detail]:
        return [
            self._create(transaction_id=data.get('id'), amount=self._comissions(**data))
            for data in self._transaction_info.list_transaction
        ]

    def _comissions(self, **kwargs) -> Decimal:
        comission = calculate_commission(
            amount=kwargs.get('monto'),
            comission=self._comission.info.get('commission_rel__percent')
        )
        return add_iva(comission)

    def _create(self, **kwargs) -> Commission_detail:
        return Commission_detail.objects.create_object(
            comission=self._comission.info.get('id'),
            transaction=kwargs.get('transaction_id', None),
            amount=kwargs.get('amount', None),
            status=1,
            payment_date=dt.datetime.now()
        )


# (ChrGil 2022-01-31) Calcula la comisión y la suma al monto de la cuenta del cliente
# (ChrGil 2022-01-31) y dependiendo de su serivico se cobrará a fin de mes
class PositiveCommission:
    def __init__(self, comission: GetInfoComissionEmisor, transaction_info: TransactionInfo):
        self._comission = comission
        self._transaction_info = transaction_info

        if self._comission.info.get('commission_rel__type') == 1:
            objs = self._calculate_comission
            self.objs = self._bulk_create(objs)
            self.total_amount = self._sum_total_amoun(objs)

    @staticmethod
    def _sum_total_amoun(objs: List[Commission_detail]) -> float:
        _total_amount: float = 0.0
        for row in objs:
            _total_amount += float(row.mount)

        return _total_amount

    @staticmethod
    def _bulk_create(objs: List[Commission_detail]) -> List[Commission_detail]:
        return Commission_detail.objects.bulk_create(objs)

    @property
    def _calculate_comission(self) -> List[Commission_detail]:
        return [
            self._create(transaction_id=data.get('id'), amount=self._comissions(**data))
            for data in self._transaction_info.list_transaction
        ]

    def _comissions(self, **kwargs) -> Decimal:
        comission = calculate_commission(
            amount=kwargs.get('monto'),
            comission=self._comission.info.get('commission_rel__percent')
        )
        return add_iva(comission)

    def _create(self, **kwargs) -> Commission_detail:
        return Commission_detail.objects.create_object(
            comission=self._comission.info.get('id'),
            transaction=kwargs.get('transaction_id', None),
            amount=kwargs.get('amount', None),
            status=2,
            payment_date=dt.datetime.now()
        )


# (ChrGil 2022-01-24) Polipay Comission id: 7422 host de pruebas
# (ChrGil 2022-01-24) variable global RS_POLIPAY_COMISSION
class TransferComissionToPolipayComission:
    _rs_polipay_comission: ClassVar[int] = COST_CENTER_POLIPAY_COMISSION
    _info_polipay_comission: ClassVar[Dict[str, Union[int, str]]]
    _serializer_class: ClassVar[SerializerTransactionPolipayComission] = SerializerTransactionPolipayComission

    def __init__(
            self,
            comission_info: GetInfoComissionEmisor,
            emisor: GetInfoEmisor,
            total_amount: float,
            request_data: RequestDataDispersiones
    ):
        self._emisor = emisor
        self._comission_info = comission_info
        self._request_data = request_data
        self._total_comission = round(total_amount, 2)

        self._get_info_polipay_comission()
        self.instance_transaction = self._create()
        self._deposit_amount()

    def _get_info_polipay_comission(self) -> NoReturn:
        self._info_polipay_comission = cuenta.objects.get_info_polipay_comission(self._rs_polipay_comission)

    @staticmethod
    def saldo_remanente(transaction: transferencia):
        transaction.saldo_remanente -= transaction.monto
        transaction.save()

    @property
    def _get_amount_emisor(self) -> Dict[str, Any]:
        return cuenta.objects.filter(persona_cuenta_id=self._emisor.info_razon_social.get('id')).values(
            'monto'
        ).first()

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "comission_type": self._comission_info.info.get('commission_rel__type_id'),
            "monto_actual": self._get_amount_emisor.get('monto'),
            "is_shedule": self._request_data.is_shedule
        }

    @property
    def _data(self) -> Dict[str, Union[str, int, float]]:
        return {
            "empresa": self._emisor.info_account_cuenta_eje.get("persona_cuenta__name_stp"),
            "monto": self._total_comission,
            "nombre_emisor": self._emisor.info_razon_social.get('name'),
            "cuenta_emisor": self._emisor.info_account_razon_social.get('cuentaclave'),
            "rfc_curp_emisor": self._emisor.info_razon_social.get('rfc'),
            "nombre_beneficiario": self._info_polipay_comission.get('persona_cuenta__name'),
            "cta_beneficiario": self._info_polipay_comission.get('cuentaclave'),
            "rfc_curp_beneficiario": self._info_polipay_comission.get('persona_cuenta__rfc'),
            "cuentatransferencia_id": self._emisor.info_account_razon_social.get('id')
        }

    def _create(self) -> transferencia:
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        instance = serializer.create()
        self.saldo_remanente(instance)
        return instance

    # (ChrGil 2022-02-01) Deposita el monto de la comisón a la cuenta de POLIPAY COMISSION si es negativa
    def _deposit_amount(self) -> NoReturn:
        _type_comission = self._comission_info.info.get('commission_rel__type_id')

        # (Negativa)
        if _type_comission == 2:
            cuenta.objects.deposit_amount(self._rs_polipay_comission, self._total_comission)


# (ChrGil 2022-01-03) Retira dinero de la comisión a la cuenta del emisor
class WithdrawAmountComission(Disperse):
    def __init__(self, emisor: GetInfoEmisor, total_amount_comission: float):
        self._emisor = emisor
        self._total_amount = total_amount_comission
        self._razon_social_id = emisor.info_razon_social.get('id')
        self.update_amount()

    def update_amount(self) -> NoReturn:
        cuenta.objects.withdraw_amount(self._razon_social_id, self._total_amount)


class TypeCommission:
    total: ClassVar[Decimal]
    _comission: ClassVar[TransferComissionToPolipayComission] = TransferComissionToPolipayComission
    _api_registra_orden: ClassVar[RegistraOrdenDispersionMasivaIndividual] = RegistraOrdenDispersionMasivaIndividual

    def __init__(
            self,
            comission: GetInfoComissionEmisor,
            emisor: GetInfoEmisor,
            transaction_info: TransactionInfo,
            request_data: RequestDataDispersiones,
            log: RegisterLog
    ):
        self.comission = comission

        # (ChrGil 2022-01-31) Comisión positiva
        if comission.info.get('commission_rel__type_id') == 1:
            _positive_commission = PositiveCommission(comission, transaction_info)

        # (ChrGil 2022-01-31) Comisión negativa
        if comission.info.get('commission_rel__type_id') == 2:
            _negative_comission = NegativeComission(comission, transaction_info)
            comission = self._comission(comission, emisor, _negative_comission.total_amount, request_data)
            self._api_registra_orden(comission.instance_transaction, log)
            _add_comission_transaction_id(comission.instance_transaction, _negative_comission.objs)
            WithdrawAmountComission(emisor, _negative_comission.total_amount)


class DepositAmount:
    def __init__(self, request_data: RequestDataDispersiones):
        self._request_data = request_data

        if not request_data.is_shedule:
            self._deposit_amount()

    def _deposit_amount(self):
        for row in self._request_data.person_list:
            account: float = row.get('account')
            account_instance: cuenta = cuenta.objects.get(cuenta=account)
            account_instance.monto += row.get('amount')
            account_instance.save()


# class RegisterMovimentMassiveInntecCostCenter:
#
#     def __init__(self, request_data: RequestDataDispersiones, transaction_info: TransactionInfo):
#         self._request_data = request_data
#         self._dispersion_info = transaction_info
#         self.create_movement_inntec_cost_center()
#
#     def create_movement_inntec_cost_center(self):
#         dispersion = self._dispersion_info.list_transaction
#
#         account_cost_center_inntec: cuenta = cuenta.objects.get(persona_cuenta_id=COST_CENTER_INNTEC)
#         for data in dispersion:
#             create_dispesion = transferencia.objects.create(
#                 nombre_emisor=data['nombre_emisor'],
#                 cuenta_emisor=data['cuenta_emisor'],
#                 cta_beneficiario=account_cost_center_inntec.cuentaclave,
#                 nombre_beneficiario=account_cost_center_inntec.persona_cuenta.name,
#                 clave_rastreo=data['clave_rastreo'],
#                 monto=data['monto'],
#                 rfc_curp_emisor=data['rfc_curp_emisor'],
#                 concepto_pago=f"{data['concepto_pago']} INFORMATIVO",
#                 fecha_creacion=data['fecha_creacion'],
#                 date_modify=data['date_modify'],
#                 referencia_numerica=data['referencia_numerica'],
#                 empresa=data['empresa'],
#                 tipo_pago_id=1,
#                 cuentatransferencia_id=1833,
#                 programada=data['programada'],
#                 masivo_trans_id=data['masivo_trans_id'],
#                 status_trans_id=data['status_trans_id'],
#                 saldo_remanente=data['saldo_remanente'],
#             )
#
#             if not create_dispesion.programada:
#                 create_dispesion.saldo_remanente_beneficiario = account_cost_center_inntec.monto + create_dispesion.monto
#                 create_dispesion.save()
#
#                 account_cost_center_inntec.monto += create_dispesion.monto
#                 account_cost_center_inntec.save()


# class RegisterMovimentMassiveInntecCostCenter:
#
#     def __init__(self, request_data: RequestDataDispersiones, transaction_info: TransactionInfo):
#         self._request_data = request_data
#         self._dispersion_info = transaction_info
#         self.create_movement_inntec_cost_center()
#
#     def create_movement_inntec_cost_center(self):
#         dispersion = self._dispersion_info.list_transaction
#
#         account_cost_center_inntec: cuenta = cuenta.objects.get(persona_cuenta_id=COST_CENTER_INNTEC)
#         for data in dispersion:
#             create_dispesion = transferencia.objects.create(
#                 nombre_emisor=data['nombre_emisor'],
#                 cuenta_emisor=data['cuenta_emisor'],
#                 cta_beneficiario=account_cost_center_inntec.cuentaclave,
#                 nombre_beneficiario=account_cost_center_inntec.persona_cuenta.name,
#                 clave_rastreo=data['clave_rastreo'],
#                 monto=data['monto'],
#                 rfc_curp_emisor=data['rfc_curp_emisor'],
#                 concepto_pago=f"{data['concepto_pago']} INFORMATIVO",
#                 fecha_creacion=data['fecha_creacion'],
#                 date_modify=data['date_modify'],
#                 referencia_numerica=data['referencia_numerica'],
#                 empresa=data['empresa'],
#                 tipo_pago_id=1,
#                 cuentatransferencia_id=1833,
#                 programada=data['programada'],
#                 masivo_trans_id=data['masivo_trans_id'],
#                 status_trans_id=data['status_trans_id'],
#                 saldo_remanente=data['saldo_remanente'],
#             )
#
#             if not create_dispesion.programada:
#                 create_dispesion.saldo_remanente_beneficiario = account_cost_center_inntec.monto + create_dispesion.monto
#                 create_dispesion.save()
#
#                 account_cost_center_inntec.monto += create_dispesion.monto
#                 account_cost_center_inntec.save()


class RegisterMovimentInntecCostCenter:

    def __init__(self, request_data: RequestDataDispersiones, transaction_info: TransactionInfo, emisor: GetInfoEmisor):
        self._request_data = request_data
        self._dispersion_info = transaction_info
        self._emisor = emisor
        self.list_obj_transaction = self.create_movement_inntec_cost_center

    @property
    def create_movement_inntec_cost_center(self) -> List[transferencia]:
        account_cost_center_inntec: cuenta = cuenta.objects.get(persona_cuenta_id=COST_CENTER_INNTEC)
        dispersion = self._dispersion_info.list_transaction
        total_amount: float = 0.0
        amount_saldos_wallet: float = account_cost_center_inntec.monto
        list_obj_transaction: List[transferencia] = []

        for data in dispersion:
            amount_saldos_wallet += data.get("monto")
            total_amount += data.get("monto")

            create_dispesion = transferencia.objects.create(
                nombre_emisor=data.get("nombre_emisor"),
                cuenta_emisor=data.get("cuenta_emisor"),
                cta_beneficiario=account_cost_center_inntec.cuentaclave,
                nombre_beneficiario=account_cost_center_inntec.persona_cuenta.name,
                rfc_curp_beneficiario=account_cost_center_inntec.persona_cuenta.rfc,
                clave_rastreo=data.get("clave_rastreo"),
                monto=data.get("monto"),
                rfc_curp_emisor="ND",
                concepto_pago=f"{data.get('concepto_pago')} INFORMATIVO",
                referencia_numerica=dt.datetime.strftime(dt.datetime.now(), "%y%m%d"),
                empresa=self._emisor.info_account_cuenta_eje.get("persona_cuenta__name_stp"),
                tipo_pago_id=10,
                cuentatransferencia_id=data["cuentatransferencia_id"],
                programada=data['programada'],
                masivo_trans_id=data['masivo_trans_id'],
                saldo_remanente_beneficiario=amount_saldos_wallet,
                transmitter_bank_id=86,
                t_ctaEmisor=40,
                fecha_creacion=dt.datetime.now(),
                t_ctaBeneficiario=40,
                date_modify=dt.datetime.now(),
                receiving_bank_id=86,
                status_trans_id=3,
            )

            list_obj_transaction.append(create_dispesion)

        # account_cost_center_inntec.monto += total_amount
        # account_cost_center_inntec.save()
        return list_obj_transaction


class PayCecoInntec:
    """ Pago por SPEI del monto de una dispersión al CECO de Inntec """

    _registra_orden: ClassVar[RegistraOrdenDispersionMasivaIndividual] = RegistraOrdenDispersionMasivaIndividual

    def __init__(
            self,
            request_data: RequestDataDispersiones,
            emisor: GetInfoEmisor,
            log: RegisterLog,
            saldos_wallet: RegisterMovimentInntecCostCenter
    ):
        self.request_data = request_data
        self.emisor = emisor
        self.log = log

        for instance in saldos_wallet.list_obj_transaction:
            self._registra_orden(instance, log)


class Controller:
    _type_transaction: ClassVar[Union[RegisterMassiveDispersion, DispersionIndividual]]
    transaction_info: ClassVar[TransactionInfo]

    def __init__(
            self,
            request_data: RequestDataDispersiones,
            emisor: GetInfoEmisor,
            product: ValidateProduct,
            comission: GetInfoComissionEmisor,
            log: RegisterLog,
    ):

        if request_data.is_a_dispersion_massive:
            self._type_transaction = RegisterMassiveDispersion(request_data, emisor)
            self.transaction_info = TransactionInfo(massive_id=self._type_transaction.massive_id)
            RegisterDispersionMasivaProgClass(request_data, self._type_transaction)
            DispersionMassive(request_data, self._type_transaction, emisor)
            ChangeStatusDispersionMassive(request_data, self._type_transaction, emisor)
            DepositAmount(request_data)
            WithdrawAmount(request_data, emisor)

        if not request_data.is_a_dispersion_massive:
            self._type_transaction = DispersionIndividual(request_data, emisor)
            self.transaction_info = TransactionInfo(transaction_id=self._type_transaction.transaction_id)
            RegisterDispersionProgramadaIndividual(request_data, self._type_transaction)
            ChangeStatusDispersionIndividual(self._type_transaction, emisor, request_data)
            DepositAmount(request_data)
            WithdrawAmount(request_data, emisor)

        if product.comission:
            TypeCommission(comission, emisor, self.transaction_info, request_data, log)


# Endpoint: http://127.0.0.1:8000/users/web/v3/CreDisIndMas/create
class DispersionesMasivasIndividuales(GenericViewSet):
    _pay_ceco_inntec: ClassVar[PayCecoInntec] = PayCecoInntec
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear dispersión individual", "Crear dispersión masiva"]

    def create(self, request):
        log = RegisterLog(request.user, request)
        try:
            admin: persona = request.user
            razon_social_id: int = self.request.query_params.get('razon_social_id')
            log.json_request(request.data)

            with atomic():
                request_data = RequestDataDispersiones(request.data)
                ValidateTokenDynamic(request_data.get_dynamic_token, admin)

                emisor = GetInfoEmisor(razon_social_id, admin)
                comission = GetInfoComissionEmisor(emisor)
                product = ValidateProduct(emisor)

                controller = Controller(request_data, emisor, product, comission, log)
                saldos_wallet = RegisterMovimentInntecCostCenter(request_data, controller.transaction_info, emisor)
                self._pay_ceco_inntec(request_data, emisor, log, saldos_wallet)
                SendNotificationDispersaBeneficiarios(request_data)
                SendMailBeneficiario(request_data, emisor)
                SendMailEmisor(request_data, emisor)

        except ObjectDoesNotExist as e:
            message = "Ocurrio un error durante el proceso de dispersión"
            err = MyHttpError(message=message, real_error=str(e), code=404)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except (IntegrityError, FieldDoesNotExist, MultipleObjectsReturned, ValueError, TypeError) as e:
            message = "Ocurrio un error durante el proceso de dispersión"
            err = MyHttpError(message=message, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except (DispersionesException, ProductException, JwtDynamicTokenException) as e:
            message = "Ocurrio un error durante el proceso de dispersión"
            err = MyHttpError(message=message, real_error=e.message)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except StpmexException as e:
            message = "Ocurrio un error al realizar el pago"
            err = MyHttpError(message=message, real_error=e.desc)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        else:
            succ = MyHtppSuccess('La dispersión se realizo de manera satisfactoria')
            log.json_response(succ.standard_success_responses())
            return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


class ComponentInfoCostCenter:
    def __init__(self, cost_center_id: int):
        self._cost_center_id = cost_center_id
        emisor = self._info_emisor
        cuenta_eje_name = self._cuenta_eje_name

        if emisor:
            self.emisor = emisor

        if cuenta_eje_name:
            self.cuenta_eje_name = cuenta_eje_name

        if not emisor:
            raise ValueError("Centro de costos no encontrado o no existe")

    @property
    def _info_emisor(self) -> Dict[str, Any]:
        return cuenta.objects.get_info_with_user_id(owner=self._cost_center_id)

    @property
    def _cuenta_eje_name(self) -> Dict[str, Any]:
        return grupoPersona.objects.get_name_cuenta_eje(person_id=self._cost_center_id)


class DevolverComissionToPolipayComission:
    """ Pago por SPEI de una comisión devuelta """

    _registra_orden: ClassVar[RegistraOrdenDispersionMasivaIndividual] = RegistraOrdenDispersionMasivaIndividual
    _rs_polipay_comission: ClassVar[int] = COST_CENTER_POLIPAY_COMISSION

    def __init__(self, emisor: ComponentInfoCostCenter, total_amount: float, log: RegisterLog):
        self._emisor = emisor
        self._total_comission = total_amount
        self._comission_info = self._get_info_polipay_comission
        instance = self.create(**self._data)
        self._registra_orden(instance, log)
        cuenta.objects.withdraw_amount(self._comission_info.get("persona_cuenta_id"), amount=total_amount)
        _add_saldo_remanente(instance, total_amount, emisor.emisor.get("monto"))

    @property
    def _get_info_polipay_comission(self) -> Dict[str, Any]:
        return cuenta.objects.get_info_polipay_comission(self._rs_polipay_comission)

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "empresa": self._emisor.cuenta_eje_name.get("empresa__name_stp"),
            "rfc_curp_emisor": self._comission_info.get("persona_cuenta__rfc"),
            "nombre_emisor": self._comission_info.get("persona_cuenta__name"),
            "cuenta_emisor": self._comission_info.get("cuentaclave"),
            "cuentatransferencia_id": self._comission_info.get("id"),
            "monto": self._total_comission,
            "nombre_beneficiario": self._emisor.emisor.get("persona_cuenta__name"),
            "cta_beneficiario": self._emisor.emisor.get("cuentaclave"),
            "rfc_curp_beneficiario": self._emisor.emisor.get("persona_cuenta__rfc"),
            "concepto_pago": "Comisión devuelta",
            "referencia_numerica": "1234567"
        }

    @staticmethod
    def create(**kwargs) -> transferencia:
        return transferencia.objects.create_transaction_polipay_to_polipay_v2(**kwargs, tipo_pago_id=11)


class DevuelveDineroSaldosWallet:
    """ El ceco Saldos Wallet regresa por SPEI el monto de la dispersión si es cancelada """

    _registra_orden: ClassVar[RegistraOrdenDispersionMasivaIndividual] = RegistraOrdenDispersionMasivaIndividual
    _rs_saldos_wallet: ClassVar[int] = COST_CENTER_INNTEC

    def __init__(self, emisor: ComponentInfoCostCenter, total_amount: float, log: RegisterLog):
        self._emisor = emisor
        self._total_amount = total_amount
        self._saldos_wallet_info = self._get_info_saldos_wallet
        instance = self.create(**self._data)
        self._registra_orden(instance, log)
        cuenta.objects.withdraw_amount(self._saldos_wallet_info.get("persona_cuenta_id"), amount=total_amount)
        _add_saldo_remanente(instance, total_amount, emisor.emisor.get("monto"))

    @property
    def _get_info_saldos_wallet(self) -> Dict[str, Any]:
        return cuenta.objects.get_info_with_user_id(self._rs_saldos_wallet)

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "empresa": self._saldos_wallet_info.get("persona_cuenta__name_stp"),
            "rfc_curp_emisor": self._saldos_wallet_info.get("persona_cuenta__rfc"),
            "nombre_emisor": self._saldos_wallet_info.get("persona_cuenta__name"),
            "cuenta_emisor": self._saldos_wallet_info.get("cuentaclave"),
            "cuentatransferencia_id": self._saldos_wallet_info.get("id"),
            "monto": self._total_amount,
            "nombre_beneficiario": self._emisor.emisor.get("persona_cuenta__name"),
            "cta_beneficiario": self._emisor.emisor.get("cuentaclave"),
            "rfc_curp_beneficiario": self._emisor.emisor.get("persona_cuenta__rfc"),
            "concepto_pago": "Monto Devuelto",
            "referencia_numerica": "1234567",
        }

    @staticmethod
    def create(**kwargs) -> transferencia:
        return transferencia.objects.create_transaction_polipay_to_polipay_v2(**kwargs, tipo_pago_id=1)


# (ManuelCalixtro 06/06/2022) Endpoint para cancelar una dispersion masiva programada
class CancelMassiveDispersionSheduled(GenericViewSet):
    _info_cost_center: ClassVar[ComponentInfoCostCenter] = ComponentInfoCostCenter
    _cancel_comission: ClassVar[DevolverComissionToPolipayComission] = DevolverComissionToPolipayComission
    _devolver_monto_saldo: ClassVar[DevuelveDineroSaldosWallet] = DevuelveDineroSaldosWallet

    def create(self):
        pass

    def put(self, request):
        log = RegisterLog(request.user, request)
        try:
            with atomic():
                massive_dispersion_id = self.request.query_params['massive_dispersion_id']
                cost_center_id = self.request.query_params['cost_center_id']
                log.json_request(self.request.query_params)
                emisor = self._info_cost_center(cost_center_id)

                # CANCELA DISPERSIONES MASIVAS
                transferencia.objects.filter(masivo_trans_id=massive_dispersion_id, programada=True,
                                             tipo_pago_id=4).update(status_trans_id=5,
                                                                    date_modify=datetime.datetime.now())
                transmasivaprod.objects.filter(id=massive_dispersion_id).update(statusRel_id=3,
                                                                                date_modified=datetime.datetime.now())
                delete_sheduled_register = TransMasivaProg.objects.get(masivaReferida_id=massive_dispersion_id)
                delete_sheduled_register.delete()

                # DEVOLVER MONTO DE DISPERSION
                account_cost_center = cuenta.objects.get(persona_cuenta_id=cost_center_id)
                trans = transferencia.objects.filter(
                    masivo_trans_id=massive_dispersion_id,
                    status_trans_id=5,
                    cuentatransferencia_id=account_cost_center.id
                ).values_list('monto', flat=True)

                total_amount = sum(list(trans))
                # account_cost_center.monto += total_amount
                # account_cost_center.save()

                info_dispersion = transferencia.objects.filter(
                    masivo_trans_id=massive_dispersion_id
                ).values(
                    'cuenta_emisor',
                    'cta_beneficiario',
                    'monto',
                    'nombre_emisor',
                    'nombre_beneficiario',
                    'rfc_curp_emisor',
                    'saldo_remanente'
                )

                # for z in info_dispersion:
                #     print(z['saldo_remanente'])
                # return_dispersion = transferencia.objects.create_movement_to_return_massive_dispersion(info_dispersion)

                # for i in trans:
                #     account_cost_center.monto += i
                #     account_cost_center.save()

                # DEVOLVER COMISION
                transfer_id = transferencia.objects.filter(
                    masivo_trans_id=massive_dispersion_id,
                    status_trans_id=5,
                    cuentatransferencia_id=account_cost_center.id
                ).values_list('id', flat=True)

                list_commision_amount = Commission_detail.objects.filter(
                    transaction_rel_id__in=transfer_id
                ).values_list('mount', flat=True)

                Commission_detail.objects.filter(transaction_rel_id__in=transfer_id).values_list('mount', flat=True)
                # instance_polipay_comission = cuenta.objects.get(persona_cuenta_id=COST_CENTER_POLIPAY_COMISSION)

                # Se recorren el monto de las comisiones
                total_amoun = sum(list(list_commision_amount))
                # for j in instance_comission:
                #     total_amoun += float(j)

                # total_amoun = total_amoun
                # return_comission = transferencia.objects.create_transaction_to_return_massive_comission(total_amoun,
                #                                                                                         account_cost_center)
                # return_comission.saldo_remanente_beneficiario = total_amoun + round(account_cost_center.monto, 2)
                # return_comission.save()

                # account_cost_center.monto += total_amoun
                # account_cost_center.save()
                #
                # instance_polipay_comission.monto -= total_amoun
                # instance_polipay_comission.save()

                # CAMBIAR STATUS COMISION
                all_dispersiones = transferencia.objects.filter(masivo_trans_id=massive_dispersion_id).values_list(
                    'id', flat=True)

                Commission_detail.objects.filter(transaction_rel_id__in=all_dispersiones).update(status_id=5)

                # Regresa monto por SPEI de la comisión al centro de costos que cancela la operación
                self._devolver_monto_saldo(emisor, total_amount, log)
                self._cancel_comission(emisor, total_amoun, log)

            succ = MyHtppSuccess(message='Tu operación se realizo de manera satisfactoria', code='200')
            return Response(succ.standard_success_responses(), status=status.HTTP_201_CREATED)

        except (ObjectDoesNotExist, IntegrityError, ValueError, TypeError) as e:
            err = MyHttpError(message="Ocurrió un error al momento de cancelar la dispersion", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except StpmexException as e:
            message = "Ocurrio un error al cancelar la operación"
            err = MyHttpError(message=message, real_error=e.desc)
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
