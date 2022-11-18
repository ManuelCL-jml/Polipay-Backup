from typing import ClassVar, Dict, Any, Union

from rest_framework.serializers import *

from apps.api_dynamic_token.models import Token_detail


class CatTimeConfiguration:
    _cat_time: ClassVar[Dict[str, Any]] = {
        3: "Tres minutos de duración",
        5: "Cinco minutos de duración",
        7: "Siete minutos de duración"
    }

    def get_value(self, key: int) -> Union[str, None]:
        return self._cat_time.get(key)


# (ChrGil 2022-01-18) Se crea la configuración del cliente para los tiempos de expiración
class SerializerCreateConfiguration(Serializer):
    _cat_time: ClassVar[CatTimeConfiguration] = CatTimeConfiguration()

    time_config = IntegerField()
    person_id_id = IntegerField()

    def validate_time_config(self, value: int):
        if not self._cat_time.get_value(value):
            raise ValidationError('Rango de tiempo no catalogado')
        return value

    def validate(self, attrs):
        return attrs

    def create(self, **kwargs):
        Token_detail.objects.create(**self.validated_data)

    def update(self, token_detail_id: int, **kwargs):
        Token_detail.objects.filter(id=token_detail_id).update(time_config=self.validated_data.get('time_config'))
