from abc import abstractmethod, ABC
from typing import NoReturn, ClassVar, Dict, Any, List, Union

from MANAGEMENT.AlgSTP.GenerarFirmaSTP import RegistraOrdenDataSTP, GetPriKey, GeneraFirma, SignatureCertSTP
from apps.transaction.models import transferencia


class CobranzaAbonoABC(ABC):
    transaction_id: ClassVar[int]

    @abstractmethod
    def context(self) -> NoReturn:
        ...

    @abstractmethod
    def create(self) -> NoReturn:
        ...


# (ChrGil 2022-01-04) Envia correo a beneficiario o a Emisor
class SendMail(ABC):
    @abstractmethod
    def send_mail_emisor(self) -> NoReturn:
        ...

    @abstractmethod
    def send_mail_beneficiario(self) -> NoReturn:
        ...

    @abstractmethod
    def context_data_email(self, **kwargs) -> NoReturn:
        ...


class CatError(ABC):
    @abstractmethod
    def get_error(self, error_id: int) -> NoReturn:
        ...


# (ChrGil 2022-01-24) Se crea clase abstracta para la data de request.data
class ResquestData(ABC):
    @abstractmethod
    def get_folio_operacion(self) -> int:
        ...

    @abstractmethod
    def get_cuenta_beneficiario(self) -> str:
        ...


class BuildObjectJSONStp(ABC):
    _default_data_stp: ClassVar[RegistraOrdenDataSTP] = RegistraOrdenDataSTP()
    _private_key: ClassVar[GetPriKey] = GetPriKey()
    _generate_sing: ClassVar[GeneraFirma] = GeneraFirma
    _sing_firma_stp: ClassVar[SignatureCertSTP] = SignatureCertSTP

    @abstractmethod
    def _add_stp_signature(self) -> NoReturn:
        ...


class EmisorTransaction(ABC):
    info_transaction: ClassVar[Dict[str, Any]]
    info_admin: ClassVar[Dict[str, Any]]
    info_transaction_stp: ClassVar[Union[Dict[str, Any], List[Dict[str, Any]]]]

    @abstractmethod
    def _get_info_transaction(self) -> NoReturn:
        ...

    @abstractmethod
    def _get_info_admin(self) -> NoReturn:
        ...

    @abstractmethod
    def _get_info_transaction_stp(self) -> NoReturn:
        ...


class ChangeStatusTransactionMassive(ABC):
    status_transaction: ClassVar[str]

    @abstractmethod
    def _context(self) -> NoReturn:
        ...

    @abstractmethod
    def _data(self) -> NoReturn:
        ...

    @abstractmethod
    def _change_status(self) -> NoReturn:
        ...


class Transaction(ABC):
    @abstractmethod
    def _data(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def _context(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def _create(self) -> NoReturn:
        ...


class CreateTransactionMassive(Transaction):
    massive_id: ClassVar[int] = 0
    is_shedule: ClassVar[bool] = False


class CreateTransactionIndividualMassive(Transaction):
    @abstractmethod
    def _bulk_create_transaction(self, objs: List[transferencia]) -> NoReturn:
        ...


class DepositAmountRecived(ABC):
    @abstractmethod
    def _deposit_amount(self) -> NoReturn:
        ...
