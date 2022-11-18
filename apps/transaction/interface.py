import datetime as dt
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import ClassVar, Union, NoReturn, List, Dict, Any

from apps.commissions.models import Commission_detail
from apps.transaction.models import transferencia


class ListData(ABC):
    _defaul_start_date: ClassVar[dt.date] = dt.date.today() - dt.timedelta(days=91)
    _defaul_end_date: ClassVar[dt.date] = dt.date.today()
    defaul_size: ClassVar[int] = 5
    data: ClassVar[Union[List[Dict[str, Any]], Dict[str, Any]]]

    @abstractmethod
    def _list(self) -> NoReturn:
        ...

    @abstractmethod
    def _detail(self) -> NoReturn:
        ...

    @abstractmethod
    def _raise_params(self) -> NoReturn:
        ...


# (ChrGil 202-02-07) clases ABC Dispersiones
class Dispersion(ABC):
    @abstractmethod
    def _data(self) -> NoReturn:
        ...

    @abstractmethod
    def _context(self) -> NoReturn:
        ...

    @abstractmethod
    def _create(self) -> NoReturn:
        ...


class RegistrationDispersionMassive(ABC):
    massive_id: ClassVar[int] = 0
    is_shedule: ClassVar[bool] = False

    @abstractmethod
    def _create(self) -> NoReturn:
        ...


class CreateDispersionProgramada(ABC):
    @abstractmethod
    def _data(self) -> NoReturn:
        ...

    @abstractmethod
    def create(self) -> NoReturn:
        ...


class CreateDispersionMassive(Dispersion):
    @abstractmethod
    def _bulk_create_dispersion(self, objs: List[transferencia]) -> NoReturn:
        ...


# (ChrGil 2022-01-04) Envia correo a beneficiario o a Emisor
class SendMail(ABC):
    @abstractmethod
    def _send_mail(self) -> NoReturn:
        ...

    @abstractmethod
    def _context_data_email(self, context: Union[None, Dict[str, Any]] = None) -> NoReturn:
        ...


# (ChrGil 2022-01-04) Actualiza el monto de una cuenta
class Disperse(ABC):
    @abstractmethod
    def update_amount(self) -> NoReturn:
        ...


class ChangeStatus(ABC):
    _status_id: ClassVar[int]
    _shedule: ClassVar[bool]

    @abstractmethod
    def _update(self) -> NoReturn:
        ...

    @abstractmethod
    def _raise_is_shedule(self, is_shedule: bool) -> NoReturn:
        ...


class ChangeStatusMassive(ChangeStatus):
    @abstractmethod
    def _list_dispersiones_masivas(self) -> NoReturn:
        ...

    @abstractmethod
    def _bulk_update(self, objs: List[transferencia]) -> NoReturn:
        ...


class ChangeStatusIndividual(ChangeStatus):
    ...


class Comission(ABC):
    list_objs_comission_detail: ClassVar[List[Commission_detail]]
    total_amount: ClassVar[Decimal]
