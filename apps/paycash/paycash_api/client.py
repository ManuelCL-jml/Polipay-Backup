import json

from typing import ClassVar, Dict, Any, Union, List, NoReturn
from requests import Response, Session
import datetime as dt

from apps.paycash.paycash_api.exceptions import *
from apps.paycash.paycash_api.exceptions import _check_response
from polipaynewConfig.settings import KEY_PAYCASH, HOST_PAYCASH
from apps.suppliers.models import cat_products_params

HOST = HOST_PAYCASH


class ComponenGetTokenPayCash:
    def __init__(self):
        token = self.get_token_autorization_paycash

        if token:
            json_content: Dict = json.loads(token.get("json_content"))
            self.autorization = json_content.get("Authorization", None)

    @property
    def get_token_autorization_paycash(self) -> Union[Dict[str, Any], None]:
        return cat_products_params.objects.filter(supplier_id=1).values("id", "json_content").last()


# (ChrGil 2021-12-28) Clase para consumir el endpoint ordenPago/registra
class APIGetTokenPayCash:
    response: ClassVar[Dict[str, Any]]
    _session: ClassVar[Session] = Session()
    _client_version: ClassVar[str] = '3.8.10'
    _endpoint: ClassVar[str] = f"{HOST}/v1/authre/"
    _key: ClassVar[str] = KEY_PAYCASH

    def __init__(self):
        self._session.headers['User-Agent'] = f'polipay/{self._client_version}'
        self._session.verify = True
        self.response = self.get

    @property
    def _params(self) -> Dict[str, Any]:
        return {
            "key": self._key,
            "expirationdate": dt.datetime.now() + dt.timedelta(days=1)
        }

    @property
    def get(self) -> Dict[str, Any]:
        return self.request('GET', self._endpoint, params=self._params)

    def request(self, method: str, endpoint: str, **kwargs: Any) -> Union[Dict[str, Any], List[Any]]:
        response = self._session.request(method, endpoint, **kwargs)
        _check_response(response)
        resultado = response.json()
        return resultado


# (ChrGil 2021-12-28) Clase para consumir el endpoint ordenPago/registra
class APICreateReferencePayCash:
    response: ClassVar[Dict[str, Any]]
    _session: ClassVar[Session] = Session()
    _client_version: ClassVar[str] = '3.8.10'
    _endpoint: ClassVar[str] = f"{HOST}/v1/reference"
    _key: ClassVar[str] = KEY_PAYCASH
    _authorization: ClassVar[ComponenGetTokenPayCash] = ComponenGetTokenPayCash

    def __init__(self, **kwargs):
        self.authorization = self._authorization().autorization
        self.expire_date = kwargs.get("expire_date")
        self.amount = kwargs.get("amount")
        self.value = kwargs.get("value")
        self.type = kwargs.get("type")

        self._session.headers['User-Agent'] = f'polipay/{self._client_version}'
        self._session.verify = True
        self.response = self.post

    @property
    def _headers(self):
        return {
            "Authorization": self.authorization,
            "Content-Type": "application/json",
            "accept": "application/json"
        }

    @property
    def _body(self) -> Dict[str, Any]:
        return {
            "Amount": self.amount,
            "ExpirationDate": self.expire_date,
            "Value": self.value,
            "Type": self.type
        }

    @property
    def post(self) -> Dict[str, Any]:
        return self.request('POST', self._endpoint, headers=self._headers, json=self._body)

    def request(self, method: str, endpoint: str, **kwargs: Any) -> Union[Dict[str, Any], List[Any]]:
        response = self._session.request(method, endpoint, **kwargs)
        _check_response(response)
        resultado = response.json()
        return resultado


# (ChrGil 2022-06-20) Cancelar una referencia
class APICancelReferencePayCash:
    response: ClassVar[Dict[str, Any]]
    _session: ClassVar[Session] = Session()
    _client_version: ClassVar[str] = '3.8.10'
    _endpoint: ClassVar[str] = f"{HOST}/v1/cancel"
    _key: ClassVar[str] = KEY_PAYCASH
    _authorization: ClassVar[ComponenGetTokenPayCash] = ComponenGetTokenPayCash

    def __init__(self, **kwargs):
        self.authorization = self._authorization().autorization
        self.reference = kwargs.get("reference_number")

        self._session.headers['User-Agent'] = f'polipay/{self._client_version}'
        self._session.verify = True
        self.response = self.post

    @property
    def _headers(self):
        return {
            "Authorization": self.authorization,
            "Content-Type": "application/json",
            "accept": "application/json"
        }

    @property
    def _body(self) -> Dict[str, Any]:
        return {
            "Reference": self.reference,
        }

    @property
    def post(self) -> Dict[str, Any]:
        return self.request('POST', self._endpoint, headers=self._headers, json=self._body)

    def request(self, method: str, endpoint: str, **kwargs: Any) -> Union[Dict[str, Any], List[Any]]:
        response = self._session.request(method, endpoint, **kwargs)
        _check_response(response)
        resultado = response.json()
        return resultado
