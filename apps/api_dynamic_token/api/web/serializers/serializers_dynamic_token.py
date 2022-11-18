from django.core.cache import cache
from rest_framework import serializers

from MANAGEMENT.Standard.errors_responses import MyHttpError
from apps.api_dynamic_token.SymetricKey import DecryptWithAES
from apps.api_dynamic_token.exc import TokenNotProvided

from polipaynewConfig.settings import PASS_FRONTEND, IV_FRONTEND


# (ChrGil 2021-12-22) Validación del token dinamico (Versión 1)
class SerializerDynamicToken(serializers.Serializer):
    token = serializers.CharField(write_only=True, allow_null=True)
    email = serializers.CharField(write_only=True)

    def validate_token(self, value: str):
        if value is None:
            raise TokenNotProvided('Para realizar esta operación, es obligatorio digitar el token')
        return value

    def validate(self, attrs):
        try:
            attrs_data = dict(attrs)
            code = DecryptWithAES(attrs_data.get('token'), secret_key=PASS_FRONTEND, iv=IV_FRONTEND)
            print(code.decrypt)

            if code.decrypt != cache.get(attrs_data.get('email'), None):
                err = MyHttpError(message="Error validando el token", real_error=None)
                raise serializers.ValidationError(err.standard_error_responses())

        except Exception as e:
            err = MyHttpError(message="Error validando el token", real_error=None)
            raise serializers.ValidationError(err.standard_error_responses())
        else:
            return attrs
