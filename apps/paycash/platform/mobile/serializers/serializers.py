import datetime as dt
from rest_framework.serializers import *

from apps.paycash.models import PayCashReference


class SerializerCreateReference(Serializer):
    amount = FloatField()
    expiration_date = DateField()
    payment_concept = CharField()
    value = CharField()
    persona_cuenta_id = IntegerField()
    supplier_id = IntegerField()
    type_reference_id = IntegerField()
    reference_number = CharField()
    comission_pay = FloatField()
    date_modify = DateTimeField(default=dt.datetime.now())

    def get_amount(self, value: float) -> float:
        return value

    def get_payment_concept(self, value: str) -> str:
        return value

    def validate(self, attrs):
        return attrs

    def create(self, **kwargs) -> int:
        return PayCashReference.objects.create(**self.validated_data).id
