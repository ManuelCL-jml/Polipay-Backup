import json
from abc import ABC, abstractmethod
from typing import NoReturn, ClassVar, Dict, Any

from jwcrypto import jwt
from jwcrypto.jwk import JWK

import datetime as dt


class GenerateBodyJWT(ABC):
    @abstractmethod
    def _payload(self) -> NoReturn:
        ...

    @abstractmethod
    def _header(self) -> NoReturn:
        ...


class EncryptedJWTPubKey(GenerateBodyJWT):
    @abstractmethod
    def _create_encryp_jwt(self) -> NoReturn:
        ...

    @abstractmethod
    def serialize_token(self) -> NoReturn:
        ...


class DecryptJWTPriKey(ABC):
    @abstractmethod
    def dencryp_jwt(self) -> NoReturn:
        ...

    @abstractmethod
    def payload(self) -> NoReturn:
        ...


class EncodeJWT(EncryptedJWTPubKey):
    _alg: ClassVar[str] = 'RSA-OAEP-256'
    _enc: ClassVar[str] = 'A256CBC-HS512'

    def __init__(self, encr_aes_code: str, pub_key: JWK, expiration_minutes: dt.timedelta):
        self._expiration_minutes = expiration_minutes
        self._code = encr_aes_code
        self._key = pub_key

    @property
    def _header(self) -> Dict[str, Any]:
        return {
            "alg": self._alg,
            "enc": self._enc
        }

    @staticmethod
    def _unix_time(date_time: dt.datetime):
        return dt.datetime.timestamp(date_time)

    @property
    def _payload(self) -> Dict[str, Any]:
        return {
            "data": self._code,
            "exp": self._unix_time(dt.datetime.now() + self._expiration_minutes),
            "iat": self._unix_time(dt.datetime.now())
        }

    @property
    def _create_encryp_jwt(self) -> jwt.JWT:
        token = jwt.JWT(header=self._header, claims=self._payload)
        token.make_encrypted_token(self._key)
        return token

    @property
    def serialize_token(self) -> str:
        return self._create_encryp_jwt.serialize(compact=True)


class DecodeJWT(DecryptJWTPriKey):
    _jwt: ClassVar[str]
    _private_key: ClassVar[JWK]

    def __init__(self, jwt_token: str, private_key: JWK):
        self._jwt = jwt_token
        self._private_key = private_key

    def dencryp_jwt(self) -> jwt.JWT:
        return jwt.JWT(key=self._private_key, jwt=self._jwt)

    def payload(self) -> Dict[str, Any]:
        return json.loads(self.dencryp_jwt().claims)

