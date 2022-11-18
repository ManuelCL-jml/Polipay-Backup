from typing import ClassVar, Dict, Any, NoReturn, List, Union

from apps.api_stp.client import CosumeAPISTP
from apps.api_stp.exc import StpmexException
from apps.api_stp.management import SetFolioOpetacionSTP
from apps.api_stp.signature import SignatureProductionAPIStpIndividualComissionPay
from apps.logspolipay.manager import RegisterLog
from apps.transaction.models import transferencia, transmasivaprod
from apps.users.models import persona
from MANAGEMENT.mails.messages import EmailWarningAdminsPolipay, EmailWarningAdminsPolipayFondeoSaldosWallet


# (ChrGil 2022-06-29) Regresa un listado de administrativos y super administrativos
class ComponentAllAdmin:
    def __init__(self):
        self.list_admin = self._get_all_admin

    @property
    def _get_all_admin(self) -> List[Dict[str, Any]]:
        return persona.objects.filter(
            # Q(is_superuser=True) | Q(is_staff=True),
            # state=True,
            email="fernandasanchezmerlin@yopmail.com"
        ).values(
            "id",
            "name",
            "email"
        )


class RegistraOrdenSTP:
    _sing: ClassVar[SignatureProductionAPIStpIndividualComissionPay] = SignatureProductionAPIStpIndividualComissionPay
    _api: ClassVar[CosumeAPISTP] = CosumeAPISTP
    _folio_stp: ClassVar[SetFolioOpetacionSTP] = SetFolioOpetacionSTP
    _email: ClassVar[EmailWarningAdminsPolipay] = EmailWarningAdminsPolipay
    _admin_list: ClassVar[ComponentAllAdmin] = ComponentAllAdmin

    def __init__(
            self,
            transaction: transferencia,
            log: RegisterLog,
            demo_bool: bool = False,
            transaction_reference: transferencia = None
    ):
        self.transaction_reference = transaction_reference
        self.transaction = transaction
        self.log = log
        self.data_email = None

        if transaction.monto > 0:
            if transaction_reference:
                self.data_email = self._data_email

            self.transaction = transaction
            self.demo_bool = demo_bool
            self._put()

    @property
    def _data_email(self) -> Dict[str, Any]:
        return {
            "folio": self.transaction_reference.id,
            "clave_rastreo": self.transaction_reference.clave_rastreo,
            "monto": self.transaction_reference.monto,
            "beneficiario": self.transaction_reference.nombre_beneficiario,
            "cuenta_beneficiario": self.transaction_reference.cta_beneficiario,
            "ordenante": self.transaction_reference.nombre_emisor,
            "cuenta_ordenante": self.transaction_reference.cuenta_emisor,
            "comision": self.transaction.monto,
            "beneficiario_comision": self.transaction.nombre_beneficiario,
        }

    def _put(self) -> NoReturn:
        try:
            json_stp_data = self._sing(self.transaction)
            self.log.json_response(json_stp_data.json_data_registra_orden)
            api = self._api(json_stp_data.json_data_registra_orden, demo_bool=self.demo_bool)
            self._folio_stp(api.response, json_stp_data.json_data_registra_orden.get('claveRastreo'))
        except StpmexException as e:
            data = self.data_email
            for row in self._admin_list().list_admin:
                self._email(to=row.get("email"), error_stp=str(e.desc), **row, **data)


class RegistraOrdenSTPDispersion:
    _sing: ClassVar[SignatureProductionAPIStpIndividualComissionPay] = SignatureProductionAPIStpIndividualComissionPay
    _api: ClassVar[CosumeAPISTP] = CosumeAPISTP
    _folio_stp: ClassVar[SetFolioOpetacionSTP] = SetFolioOpetacionSTP
    _email: ClassVar[EmailWarningAdminsPolipayFondeoSaldosWallet] = EmailWarningAdminsPolipayFondeoSaldosWallet
    _admin_list: ClassVar[ComponentAllAdmin] = ComponentAllAdmin

    def __init__(
            self,
            transaction: transferencia,
            log: RegisterLog,
            demo_bool: bool = False,
            transaction_ref: Union[transmasivaprod, transferencia] = None
    ):

        self.transaction_reference = transaction_ref
        self.transaction = transaction
        self.log = log
        self.data_email = None

        if transaction.monto > 0:
            if transaction_ref:
                self.data_email = self._data_email

            self.transaction = transaction
            self.demo_bool = demo_bool
            self._put()

    @property
    def _data_email(self) -> Dict[str, Any]:
        return {
            "folio": self.transaction_reference.id,
            "clave_rastreo": self.transaction_reference.clave_rastreo,
            "monto": self.transaction_reference.monto,
            "beneficiario": self.transaction_reference.nombre_beneficiario,
            "cuenta_beneficiario": self.transaction_reference.cta_beneficiario,
            "ordenante": self.transaction_reference.nombre_emisor,
            "cuenta_ordenante": self.transaction_reference.cuenta_emisor,
            "comision": self.transaction.monto,
            "beneficiario_comision": self.transaction.nombre_beneficiario,
        }

    def _put(self) -> NoReturn:
        try:
            json_stp_data = self._sing(self.transaction)
            self.log.json_response(json_stp_data.json_data_registra_orden)
            api = self._api(json_stp_data.json_data_registra_orden, demo_bool=self.demo_bool)
            self._folio_stp(api.response, json_stp_data.json_data_registra_orden.get('claveRastreo'))
        except StpmexException as e:
            data = self.data_email
            for row in self._admin_list().list_admin:
                self._email(to=row.get("email"), error_stp=str(e.desc), **row, **data)


class RegistraOrdenDispersionMasivaIndividual:
    _sing: ClassVar[SignatureProductionAPIStpIndividualComissionPay] = SignatureProductionAPIStpIndividualComissionPay
    _api: ClassVar[CosumeAPISTP] = CosumeAPISTP
    _folio_stp: ClassVar[SetFolioOpetacionSTP] = SetFolioOpetacionSTP

    def __init__(
            self,
            transaction: transferencia,
            log: RegisterLog,
            demo_bool: bool = False,
    ):
        self.transaction = transaction
        self.log = log
        self.data_email = None

        if transaction.monto > 0:
            self.transaction = transaction
            self.demo_bool = demo_bool
            self._put()

    def _put(self) -> NoReturn:
        json_stp_data = self._sing(self.transaction)
        self.log.json_response(json_stp_data.json_data_registra_orden)
        api = self._api(json_stp_data.json_data_registra_orden, demo_bool=self.demo_bool)
        self._folio_stp(api.response, json_stp_data.json_data_registra_orden.get('claveRastreo'))
