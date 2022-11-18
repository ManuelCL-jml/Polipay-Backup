from rest_framework.serializers import *

from apps.paycash.models import PayCashRegistraNotificacionPago


class SerializerPayCashNotifica(Serializer):
    folio = IntegerField()
    resultado = IntegerField()
    tipo = IntegerField()
    emisor = IntegerField()
    secuencia = IntegerField()
    monto = FloatField()
    fecha = CharField()
    hora = CharField()
    autorizacion = CharField()
    referencia = CharField()
    value = CharField()
    fecha_creacion = DateTimeField()
    fecha_confirmacion = DateTimeField()
    fecha_vencimiento = DateTimeField()
    reference_id = IntegerField()

    def validate(self, attrs):
        atrr = dict(attrs)

        if self.context.get("status_reference_id") != 3:
            if self.context.get("type_reference_id") == 1:
                raise ValueError("La referencia es de tipo única, no se puede liquidar mas de una vez")

        if self.context.get("status_reference_id") == 5:
            raise ValueError("La referencia expiro o fue cancelada")

        return attrs

    def create(self, **kwargs):
        PayCashRegistraNotificacionPago.objects.create(**self.validated_data)
