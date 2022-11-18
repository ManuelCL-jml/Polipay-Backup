from dataclasses import dataclass, field
from typing import List, Dict, Any, ClassVar, Union

from rest_framework.status import HTTP_400_BAD_REQUEST


@dataclass
class MyHttpError:
    message: str
    real_error: Union[str, None]
    error_desc: Union[str, None] = None
    code: int = HTTP_400_BAD_REQUEST

    def detail(self) -> List[Dict]:
        return [
            {
                "field": None,
                "data": self.real_error,
                "message": self.message,
                "desc": self.error_desc
            }
        ]

    def standard_error_responses(self) -> Dict[str, Any]:
        return {
            "code": [self.code],
            "status": ["ERROR"],
            "detail": self.detail()
        }

    def object_does_not_exist(self) -> Dict[str, Any]:
        return self.standard_error_responses()

    def multi_value_dict_key_error(self) -> Dict[str, Any]:
        return self.standard_error_responses()


@dataclass
class ErrorsValidations:
    message: str
    field: str = None
    value: str = None

    @property
    def render_error(self) -> Dict:
        return {
            "field": self.field,
            "data": self.value,
            "message": self.message
        }


@dataclass
class AddErrorStack:
    list_errors: List[ErrorsValidations] = field(default_factory=list)

    def add_error(self, err: ErrorsValidations) -> None:
        self.list_errors.append(err)

    @property
    def get_list_errors(self) -> List[ErrorsValidations]:
        return self.list_errors


@dataclass
class ErrorsStandard:
    errors: List[ErrorsValidations]
    code: int = HTTP_400_BAD_REQUEST

    def standard_error_responses(self) -> Dict[str, Any]:
        return {
            "code": [self.code],
            "status": ["ERROR"],
            "detail": [err.render_error for err in self.errors]
        }


@dataclass
class ErrorResponseSTP:
    message: str
    code: int = 400
    real_error: Union[str, None] = None
    _status: ClassVar[str] = "ERROR"

    @property
    def error(self):
        return {
            "code": self.code,
            "status": self._status,
            "message": self.message,
            "error": self.real_error
        }
