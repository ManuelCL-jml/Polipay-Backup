from typing import List, Dict, Any, ClassVar

from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from dataclasses import dataclass


@dataclass
class MyHtppSuccess:
    message: str
    extra_data: Any = None
    code: str = HTTP_200_OK
    status: str = "OK"

    def detail(self) -> List[Dict]:
        return [
            {
                "field": None,
                "data": self.extra_data,
                "message": self.message
            }
        ]

    def standard_success_responses(self) -> Dict[str, Any]:
        return {
            "code": [self.code],
            "status": [self.status],
            "detail": self.detail()
        }

    def created(self) -> Dict[str, Any]:
        self.code = HTTP_201_CREATED
        self.status = 'CREATED'
        return self.standard_success_responses()

    def ok(self) -> Dict[str, Any]:
        return self.standard_success_responses()


@dataclass
class SuccessResponseSTP:
    message: str
    code: int = 200
    extra_data: Dict[str, Any] = None
    status: str = "OK"

    @property
    def success(self):
        return {
            "code": self.code,
            "status": self.status,
            "message": self.message,
            "extra_data": self.extra_data
        }
