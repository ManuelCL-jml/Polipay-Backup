import base64
import random
import string
from decouple import config
from Crypto.Cipher import AES
from dataclasses import dataclass
from django.core.cache import cache
from abc import abstractmethod, ABC
from typing import ClassVar, Dict, List, NoReturn

from apps.users.models import persona


class RandomNumber(ABC):
    _defaul_length: ClassVar[int] = 4

    @abstractmethod
    def random_number(self) -> None:
        ...


class CodeCache(ABC):
    @abstractmethod
    def _set_cache_person(self) -> None:
        ...


class GenerateCodeCache(RandomNumber):
    code: ClassVar[str]

    def __init__(self):
        self.random_number()

    def random_number(self) -> NoReturn:
        self.code = "".join(random.choices(string.digits, k=self._defaul_length))


class GenerateCodeAES16Bytes(RandomNumber):
    aes_16bytes: ClassVar[str]
    _defaul_length: ClassVar[int] = 11

    def __init__(self):
        self.random_number()

    def random_number(self) -> NoReturn:
        self.aes_16bytes = "".join(random.choices(string.digits, k=self._defaul_length))


class CreateCodeCache(CodeCache):
    _person: ClassVar[persona]
    _code_cache: ClassVar[GenerateCodeCache]

    def __init__(self, code: GenerateCodeCache, person: persona, time_expire: float):
        self._code_cache = code
        self._person = person
        self._time_expire = int((time_expire + 0.1) * 60)
        self._set_cache_person()

    def _set_cache_person(self) -> bytes:
        cache.set(self._person.get_username, self._code_cache.code, self._time_expire)
        return cache.get(self._person.get_username).encode('utf-8')


class EncryptWithAES:
    _code: ClassVar[bytes]
    encrypt_mode_cbc: ClassVar[str]

    def __init__(self, code: GenerateCodeCache, code_aes16: GenerateCodeAES16Bytes, secret_key: bytes, iv: bytes):
        self._join_code(code.code, code_aes16.aes_16bytes)
        self._SECRET_KEY = secret_key
        self._IV = iv

        self._encrypt_mode_cbc()

    def _join_code(self, code: str, code_aes16: str) -> NoReturn:
        self._code = f"{code}_{code_aes16}".encode('utf-8')

    def _encrypt_mode_cbc(self) -> NoReturn:
        aes = AES.new(self._SECRET_KEY, AES.MODE_CBC, self._IV)
        encrypt_data = base64.b64encode(aes.encrypt(self._code))
        self.encrypt_mode_cbc = encrypt_data.decode('utf-8')


class EncryptWithAESTest:
    _code: ClassVar[bytes]
    encrypt_mode_cbc: ClassVar[str]

    def __init__(self, code: str, secret_key: bytes, iv: bytes):
        self._join_code(code, "12345678901")
        self._SECRET_KEY = secret_key
        self._IV = iv

        self._encrypt_mode_cbc()

    def _join_code(self, code: str, code_aes16: str) -> NoReturn:
        self._code = f"{code}_{code_aes16}".encode('utf-8')

    def _encrypt_mode_cbc(self) -> NoReturn:
        aes = AES.new(self._SECRET_KEY, AES.MODE_CBC, self._IV)
        encrypt_data = base64.b64encode(aes.encrypt(self._code))
        self.encrypt_mode_cbc = encrypt_data.decode('utf-8')


class DecryptWithAES:
    _text: ClassVar[str]
    _SECRET_KEY: ClassVar[bytes]
    _IV: ClassVar[bytes]

    def __init__(self, text: str, secret_key: bytes, iv: bytes):
        self._text = text
        self._SECRET_KEY = secret_key
        self._IV = iv

    def render_code(self, code: str) -> str:
        result = code.split("_")
        return result[0]

    @property
    def decrypt(self) -> str:
        aes = AES.new(self._SECRET_KEY, AES.MODE_CBC, self._IV)
        ciphertext = base64.b64decode(self._text.encode('utf-8'))
        code = aes.decrypt(ciphertext).decode('utf-8')
        return self.render_code(code)
