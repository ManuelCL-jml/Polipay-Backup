from typing import Any, Dict, ClassVar

from rest_framework.serializers import *

from apps.commissions.models import Cat_commission
from apps.users.exc import YouNotSuperUser


class SerializerUpdateProductsServices(Serializer):
    _paycash_service: ClassVar[int] = 3

    id = FloatField()
    percent = FloatField(allow_null=True)
    amount = FloatField(allow_null=True)
    type_id = BooleanField()
    application_id = IntegerField(read_only=True)
    service_id = IntegerField()

    def validate_id(self, value: int) -> int:
        if not Cat_commission.objects.filter(id=value).exists():
            raise ValueError("Comisión no valida o no existe")
        return value

    def validate_percent(self, value: int) -> float:
        if value >= 100 or value < 0:
            raise TypeError('El porcentaje no debe de ser mayor a 100 o menor a 0')
        if value:
            return value / 100
        return 0.0

    def validate_amount(self, value: float) -> float:
        return value

    def validate_type_id(self, value: bool) -> int:
        # Positiva
        if value:
            return 1

        # Negativa
        if not value:
            return 2

    def validate(self, attrs):
        if not self.context.get('is_superuser'):
            raise YouNotSuperUser("No tienes los permisos suficientes para hacer esta operación")

        # Cobro comisión, mensual
        if attrs['type_id'] == 1:
            attrs['application_id'] = 2

        # Cobro comisión, inmediato
        if attrs['type_id'] == 2:
            attrs['application_id'] = 1

        if attrs["service_id"] == 3:
            if not attrs["amount"]:
                attrs["amount"] = 12.50

        return attrs

    def update(self, **kwargs) -> int:
        self.validated_data.pop("service_id")
        comission_id: int = self.validated_data.pop("id")
        return Cat_commission.objects.update_cat_comission(
            comission_id=comission_id,
            **self.validated_data
        )
