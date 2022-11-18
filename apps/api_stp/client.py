from typing import ClassVar, Dict, Any, Union, List, NoReturn

from requests import Response, Session

from apps.api_stp.exc import _raise_description_error_exc, _raise_description_exc, \
    _raise_description_error_exc_retorna_orden
from polipaynewConfig.settings import HOST_STP, HOST_STP_CONSULTA_SALDO

HOST = HOST_STP


# (ChrGil 2021-12-28) Clase para consumir el endpoint ordenPago/registra
class CosumeAPISTP:
    response: ClassVar[Dict[str, Any]]
    _data: ClassVar[Dict[str, Any]]
    _session: ClassVar[Session] = Session()
    _client_version: ClassVar[str] = '3.8.10'
    _endpoint: ClassVar[str] = f"{HOST}/speiws/rest/ordenPago/registra/"

    def __init__(self, data: Dict[str, Any], demo_bool: bool = True):
        self._data = data

        self._session.headers['User-Agent'] = f'polipay/{self._client_version}'
        if demo_bool:
            self._session.verify = False
            self.put()

        if not demo_bool:
            self.put()
            self._session.verify = True

    def put(self) -> Union[Dict[str, Any], List[Any]]:
        return self.request('PUT', self._endpoint, self._data)

    def request(self, method: str, endpoint: str, data: Dict[str, Any], **kwargs: Any) -> Union[Dict[str, Any], List[Any]]:
        response = self._session.request(method, endpoint, json=data, **kwargs)
        self._check_response(response)

        resultado = response.json()
        self.response = resultado
        if 'estado' in resultado:
            resultado = resultado['resultado']

        return resultado

    @staticmethod
    def _check_response(response: Response) -> NoReturn:
        if not response.ok:
            response.raise_for_status()
        resp = response.json()
        if isinstance(resp, dict):
            try:
                _raise_description_error_exc(resp)
            except KeyError:
                ...
            try:
                assert resp['descripcion']
                _raise_description_exc(resp)
            except (AssertionError, KeyError):
                ...
        response.raise_for_status()


# (ChrGil 2021-12-28) Clase para consumir el endpoint retornaOrden/registra
class CosumeRetornaOrdenAPISTP:
    response: ClassVar[Dict[str, Any]]
    _data: ClassVar[Dict[str, Any]]
    _session: ClassVar[Session] = Session()
    _client_version: ClassVar[str] = '3.8.10'
    _endpoint: ClassVar[str] = f"{HOST}speiws/rest/ordenPago/retornaOrden"

    def __init__(self, data: Dict[str, Any], demo_bool: bool = True):
        self._data = data

        self._session.headers['User-Agent'] = f'polipay/{self._client_version}'
        if demo_bool:
            self._session.verify = False
            self.put()

        if not demo_bool:
            self.put()
            self._session.verify = True

    def put(self) -> Union[Dict[str, Any], List[Any]]:
        return self.request('PUT', self._endpoint, self._data)

    def request(self, method: str, endpoint: str, data: Dict[str, Any], **kwargs: Any) -> Union[Dict[str, Any], List[Any]]:
        response = self._session.request(method, endpoint, json=data, **kwargs)
        self._check_response(response)

        resultado = response.json()
        self.response = resultado
        if 'resultado' in resultado:
            resultado = resultado['resultado']

        return resultado

    @staticmethod
    def _check_response(response: Response) -> NoReturn:
        if not response.ok:
            response.raise_for_status()
        resp = response.json()
        if isinstance(resp, dict):
            try:
                _raise_description_error_exc_retorna_orden(resp)
            except KeyError:
                ...
            try:
                assert resp['descripcion']
                _raise_description_exc(resp)
            except (AssertionError, KeyError):
                ...
        response.raise_for_status()


# (ChrGil 2021-12-28) Clase para consumir el endpoint retornaOrden/registra
class CosumeConsultaSaldoCuentaAPISTP:
    response: ClassVar[Dict[str, Any]]
    _data: ClassVar[Dict[str, Any]]
    _session: ClassVar[Session] = Session()
    _client_version: ClassVar[str] = '3.8.10'
    _endpoint: ClassVar[str] = f"{HOST_STP_CONSULTA_SALDO}/efws/API/consultaSaldoCuenta/"

    def __init__(self, data: Dict[str, Any], demo_bool: bool = True):
        self._data = data

        self._session.headers['User-Agent'] = f'polipay/{self._client_version}'
        if demo_bool:
            self._session.verify = False
            self.post()

        if not demo_bool:
            self.post()
            self._session.verify = True

    def post(self) -> Union[Dict[str, Any], List[Any]]:
        return self.request('POST', self._endpoint, self._data)

    def request(self, method: str, endpoint: str, data: Dict[str, Any], **kwargs: Any) -> Union[Dict[str, Any], List[Any]]:
        response = self._session.request(method, endpoint, json=data, **kwargs)
        self._check_response(response)

        resultado = response.json()
        if 'resultado' in resultado:
            resultado = resultado['resultado']

        self.response = resultado
        return resultado

    @staticmethod
    def _check_response(response: Response) -> NoReturn:
        # if response.status_code == 400:
        #     response.raise_for_status()
        resp = response.json()
        print(resp)
        if isinstance(resp, dict):
            try:
                _raise_description_error_exc_retorna_orden(resp)
            except KeyError:
                ...
            try:
                assert resp['descripcion']
                _raise_description_exc(resp)
            except (AssertionError, KeyError):
                ...
        response.raise_for_status()
