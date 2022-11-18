from typing import ClassVar, Union, Dict, Any, NoReturn

from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from apps.users.models import persona


class RegisterLog:
    _type: ClassVar[int] = 1
    _json_request: ClassVar[Union[Dict[str, Any], None]]
    _json_response: ClassVar[Union[Dict[str, Any], None]]

    def __init__(self, owner: Union[persona, int], request: Dict[str, Any]):
        if isinstance(owner, int):
            self._owner = owner

        if isinstance(owner, persona):
            self._owner = owner.get_only_id()

        self._request = request
        self._json_response = None
        self._json_request = None

    @property
    def _generate_url(self) -> str:
        return get_info(self._request)

    def json_request(self, json_request: Dict[str, Any]) -> NoReturn:
        self._json_request = json_request

    def json_response(self, json_response: Dict[str, Any]) -> NoReturn:
        self._json_response = json_response
        self._register_log()

    def _register_log(self) -> NoReturn:
        RegisterSystemLog(
            idPersona=self._owner,
            type=self._type,
            endpoint=self._generate_url,
            objJsonRequest=self._json_request,
            objJsonResponse=self._json_response
        )

