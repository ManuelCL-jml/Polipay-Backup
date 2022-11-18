from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import NoReturn, ClassVar, Union

from decouple import config

from jwcrypto.jwk import JWK


class ImportKeys(ABC):
    @abstractmethod
    def get_key(self, password: str = None) -> NoReturn:
        ...


class ImportKeysJWE(ImportKeys):
    _file_name: ClassVar[str]

    def __init__(self, file_name: str):
        self._file_name = file_name

    def get_key(self, password: Union[bytes, None] = None) -> JWK:
        with open(self._file_name, mode='rb') as f:
            return JWK.from_pem(f.read(), password=password)
