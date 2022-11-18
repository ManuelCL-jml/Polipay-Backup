import base64
import binascii
import datetime
from os import remove
from datetime import timedelta
from typing import List, Dict, ClassVar, Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File

from rest_framework.serializers import *

from MANAGEMENT.Supplier.STP.stp import CatBancos, CatTipoCuenta
from MANAGEMENT.Utils.utils import strptime
from MANAGEMENT.mails.messages import EmailAuthTransactionIndividual
from polipaynewConfig.exceptions import ErrorsList
from MANAGEMENT.Standard.errors_responses import MyHttpError
from apps.users.models import grupoPersona
from apps.transaction.models import (transmasivaprod, transferencia, TransMasivaProg)


# (ChrGil 2021-11-02) Crear archivo de xlsx
def create_xlsx_file(file, cost_center: str):
    decrypted = base64.b64decode(file)
    name = cost_center.split()
    with open(f"TMP/cost_center_{name[0]}.xlsx", "wb") as file:
        file.write(decrypted)
    return file.name


# (ChrGil 2021-11-01) Serializador para crear una transferencia masiva
class SerializerMassTransfer(Serializer):
    observations = CharField()
    status = IntegerField()
    layout_file = CharField()
    user_admin_id = IntegerField()

    def validate(self, attrs):
        try:
            cost_center = grupoPersona.objects.get(
                empresa_id=self.context['cost_center_id'], relacion_grupo_id=4).get_empresa()

            layout_file = create_xlsx_file(attrs['layout_file'], cost_center['name'])
        except binascii.Error as e:
            raise ValidationError('Error al decodificar el archivo')
        else:
            attrs['layout_file'] = layout_file
            return attrs

    def create(self, **kwargs):
        layout_file = self.validated_data.pop('layout_file')
        instance = transmasivaprod.objects.create_transaction_massive(**self.validated_data)

        with open(layout_file, 'rb') as document:
            instance.file = File(document)
            instance.save()

        remove(layout_file)
        return instance.get_only_id()


# (ChrGil 2021-11-03) Serializador para crear una transacción masiva programada
class SerializerTransMasivaProg(Serializer):
    masivaReferida_id = IntegerField()
    fechaProgramada = CharField()
    fechaEjecucion = CharField()

    def validate_fechaProgramada(self, value: str) -> str:
        return strptime(value)

    def validate_fechaEjecucion(self, value: str) -> str:
        return strptime(value)

    def validate(self, attrs):
        return attrs

    def create(self, **kwargs):
        TransMasivaProg.objects.create(**self.validated_data)


class SerializerIndividualTransaction(Serializer):
    _institucion_cat: ClassVar[CatBancos] = CatBancos()
    _tipo_cuenta_stp_cat: ClassVar[CatTipoCuenta] = CatTipoCuenta()

    # (ChrGil 2021-12-27) Información que se envia en el layout
    institucionContraparte = CharField()
    empresa = CharField()
    monto = DecimalField(decimal_places=2, max_digits=14, max_value=999999999999.99)
    tipoPago = IntegerField()
    nombreOrdenante = CharField(read_only=True)
    cuentaOrdenante = CharField(read_only=True)
    tipoCuentaBeneficiario = IntegerField()
    nombreBeneficiario = CharField()
    cuentaBeneficiario = CharField()
    rfcCurpBeneficiario = CharField()
    conceptoPago = CharField()
    referenciaNumerica = IntegerField()

    programada = BooleanField(read_only=True)
    emisor_empresa_id = IntegerField(read_only=True)
    masivo_trans_id = IntegerField(read_only=True)
    cuentatransferencia_id = IntegerField(read_only=True)
    rfc_curp_emisor = IntegerField(read_only=True)
    list_errors = ErrorsList()

    def errors_list_clear(self):
        self.list_errors.clear_list()

    def validate_institucionContraparte(self, value: str) -> int:
        self.errors_list_clear()
        result = self.context.get('banks').get(int(value))

        if len(value) > 5:
            ErrorsList('institucionContraparte', value, 'Asegúrese de que este campo no tenga más de 5 caracteres.')

        if result is None:
            ErrorsList('institucionContraparte', value, 'Banco No Catalogado')
        return result

    def validate_empresa(self, value: str) -> str:
        if len(value) > 15:
            ErrorsList('empresa', value, 'Asegúrese de que este campo no tenga más de 15 caracteres.')
        return value.upper()

    def validate_monto(self, value: float) -> float:
        if value <= 0:
            ErrorsList('monto', str(value), 'Asegúrese de que el monto no sea menor a 0')
        return round(value, 2)

    def validate_tipoPago(self, value: int) -> int:
        # (ChrGil 2021-12-18) Normalmente en el catálogo de STP el tipo de pago será (1)
        # (ChrGil 2021-12-18) Que hace referencia a un tipo de pago de tercero a tercero
        # (ChrGil 2021-12-18) Pero en nuestra base, siempre será (2)
        value = 2
        return value

    def validate_nombreOrdenante(self, value: str) -> str:
        if len(value) > 40:
            ErrorsList('nombreOrdenante', value, 'Asegúrese de que este campo no tenga más de 40 caracteres.')
        return value

    def validate_cuentaOrdenante(self, value: str) -> str:
        if len(value) > 20:
            ErrorsList('cuentaOrdenante', value, 'Asegúrese de que este campo no tenga más de 20 caracteres.')
        return value

    def validate_tipoCuentaBeneficiario(self, value: int) -> int:
        if value > 99 or value < 0:
            ErrorsList('nombreBeneficiario', str(value), 'Asegúrese de que este campo no tenga más de 2 digitos.')

        if not self._tipo_cuenta_stp_cat.get_value(key=str(value)):
            ErrorsList('tipoCuentaBeneficiario', str(value), 'Tipo de cuenta No Catalogado')
        return value

    def validate_nombreBeneficiario(self, value: str) -> str:
        if len(value) > 40:
            ErrorsList('nombreBeneficiario', value, 'Asegúrese de que este campo no tenga más de 40 caracteres.')
        return value

    def validate_cuentaBeneficiario(self, value: str) -> str:
        if len(value) > 18:
            ErrorsList('cuentaBeneficiario', value, 'Error validando la cuenta clabe')

        if len(value) < 16:
            ErrorsList('cuentaBeneficiario', value, 'Error validando el numero de tarjeta de debito')
        return value

    def validate_rfcCurpBeneficiario(self, value: str) -> str:
        if value is None:
            value = 'ND'
            return value

        if len(value) > 13:
            ErrorsList('rfcCurpBeneficiario', value, 'Asegúrese de que este campo no tenga más de 13 caracteres.')
        return value

    def validate_conceptoPago(self, value: str) -> str:
        if len(value) > 40:
            ErrorsList('conceptoPago', value, 'Asegúrese de que este campo no tenga más de 40 caracteres.')
        return value

    def validate_referenciaNumerica(self, value: int) -> int:
        if value > 9_999_999 or value < 0:
            ErrorsList('referenciaNumerica', str(value), 'Asegúrese de que este campo no tenga más de 7 digitos.')
        return value

    # (ChrGil 2021-12-27) Actualiza valores de los atributos del serializador
    def update_attrs(self, attrs: Dict[str, Any], context: Dict[str, Any]):
        attrs.update({"cuentatransferencia_id": context.get('cuentatransferencia_id')})
        attrs.update({"emisor_empresa_id": context.get('emisor_empresa_id')})
        attrs.update({"masivo_trans_id": context.get('massive_trans_id')})
        attrs.update({"nombreOrdenante": context.get('nombre_emisor')})
        attrs.update({"cuentaOrdenante": context.get('cuenta_emisor')})
        attrs.update({"cuentaOrdenante": context.get('cuenta_emisor')})
        attrs.update({"rfc_curp_emisor": context.get('rfc_emisor')})
        attrs.update({"programada": context.get('programada')})
        return attrs

    def validate(self, attrs):
        if self.context.get('monto_cuenta_emisor') < float(self.context.get('monto_total')):
            ErrorsList('El centro de costos no cuenta con el monto suficiente para realizar esta transacción')

        if len(self.list_errors.show_errors_list()) > 0:
            raise ValidationError(self.list_errors.standard_error_responses())

        attrs = self.update_attrs(dict(attrs), self.context)
        self.list_errors.clear_list()
        return attrs

    def create(self, **kwargs) -> transferencia:
        return transferencia.objects.create_object_transfer(**self.validated_data)


# (ChrGil 2021-11-26) Se crea serializador para cancelar una transacción masiva
class SerializerCancelTransaction(Serializer):
    massive_id = IntegerField()

    def validate(self, attrs):
        massive_id: int = attrs['massive_id']

        if self.context.get("current_status") != 2:
            err = MyHttpError("Ya no es posible cambiar el estado de esta transacción", real_error='null', code=400)
            raise ValidationError(err.standard_error_responses())

        try:
            trans_massive_pro = TransMasivaProg.objects.get_object_trans_masiva_prog(massive_id)

            # (ChrGil 2021-11-29) Si la transacción es programada y es mayor a 24 horas de la fecha liminte
            if datetime.datetime.now() > (trans_massive_pro.fechaProgramada - timedelta(days=1)):
                err = MyHttpError("Ya no se puede cancelar esta transacción masiva", real_error='null', code=400)
                raise ValidationError(err.standard_error_responses())

            return attrs

        except ObjectDoesNotExist as e:
            return attrs

    def update(self, **kwargs) -> str:
        massive_id: int = self.validated_data.get('massive_id')
        self.update_status_massive(massive_id, status_id=3)
        self.update_status_individual(massive_id, status_id=5, user_auth=self.context['admin_id'])
        self.send_email_emisor()

        return "CANCELADA"

    # (ChrGil 2021-11-11) Actualiza el estado de la transacció  masiva
    def update_status_massive(self, massive_id: int, status_id: int):
        transmasivaprod.objects.change_status_massive(massive_id, status_id)

    # (ChrGil 2021-11-11) Actualiza el estado de cada transacción individual
    def update_status_individual(self, massive_id: int, user_auth: int, status_id: int):
        transferencia.filter_transaction.update_massive_transaction(massive_id, status_id, user_auth)

    # (ChrGil 2021-11-26) Enviar Correo a la persona que emitio la transacción masiva
    def send_email_emisor(self):
        context = self.context.get('administrative')
        context['status'] = 'CANCELADO'
        context['observations'] = self.context.get('observations'),
        EmailAuthTransactionIndividual(to=context.get('email'), **context)


class SerializerAuthorizateTransaction(Serializer):
    status: ClassVar[str]
    massive_id = IntegerField()

    def validate(self, attrs):
        if self.context.get('current_status') != 2:
            err = MyHttpError("Ya no es posible cambiar el estado de esta transacción", real_error='null', code=400)
            raise ValidationError(err.standard_error_responses())

        if self.context.get('amount_emisor') < self.context.get('total_amount'):
            message = "No cuentas con el saldo suficiente para realizar esta transacción"
            err = MyHttpError(message=message, real_error='null', code=400)
            raise ValidationError(err.standard_error_responses())

        try:
            trans_massive_pro = TransMasivaProg.objects.get_object_trans_masiva_prog(attrs['massive_id'])

            # (ChrGil 2021-11-29) Si la transacción es programada y es mayor a 24 horas de la fecha liminte
            if (trans_massive_pro.fechaProgramada + timedelta(days=1)) < datetime.datetime.now():
                err = MyHttpError("Ya no se puede autorizar esta transacción masiva", real_error='null', code=400)
                raise ValidationError(err.standard_error_responses())

            return attrs

        except ObjectDoesNotExist as e:
            return attrs

    # (ChrGil 2021-12-03) Trae todas las transferencias individuales de una masiva.
    def get_all_transaction_individual(self, massive_trans_id: int) -> List[transferencia]:
        return transferencia.objects.select_related('masivo_trans').filter(masivo_trans_id=massive_trans_id)

    # (2021-12-03) Recorre el listado de objetivo y cambia su estado, agrega la persona quien la autorizo, cacha la
    # (2021-12-03) hora actual de modificación y calcula el saldo remanente de esa transacción
    def change_fields_data(self, objs_transfer: List[transferencia]) -> List[transferencia]:
        monto_emisor: float = self.context.get('amount_emisor')

        for transfer in objs_transfer:
            transfer.date_modify = datetime.datetime.now()
            transfer.user_autorizada_id = self.context.get('admin_id')
            transfer.status_trans_id = 3
            monto_emisor -= transfer.monto
            transfer.saldo_remanente = round(monto_emisor, 2)

        return objs_transfer

    # (ChrGil 2021-12-01) Actualiza el estado de una transacción masiva
    def update_status_massive(self, massive_trans_id: int, status):
        transmasivaprod.objects.change_status_massive(massive_trans_id, status_id=status)

    # (ChrGil 2021-11-11) Actualiza el estado de la transacció masiva
    def update(self, **kwargs):
        massive_id = self.validated_data.get('massive_id')
        print(massive_id)
        self.status: str = "PENDIENTE"

        # (ChrGil 2021-11-26) Cambiar estado a EN PROCESO Si la transacción no esta programada
        if not self.context.get('is_shedule'):
            self.status = "EN PROCESO"
            self.update_transaction(massive_id, status=4)

        if self.context.get('is_shedule'):
            self.update_transaction(massive_id)

    # (ChrGil 2021-11-29) realiza el movimiento siempre y cuando la transacción no este programada
    def update_transaction(self, massive_trans_id: int, status: int = 2):
        objs = self.change_fields_data(self.get_all_transaction_individual(massive_trans_id))
        self.update_status_massive(massive_trans_id, status)
        self.update_individual_transfer(objs)
        self.send_email_emisor()

    # (ChrGil 2021-11-25) Actualiza el campo user_autorizada_id masivamente las transacciones individuales de una masiva
    def update_individual_transfer(self, objs: List[transferencia]):
        transferencia.objects.bulk_update(objs, fields=[
            'user_autorizada_id',
            'saldo_remanente',
            'status_trans_id',
            'date_modify'
        ])

    # (ChrGil 2021-11-25) Enviar Correo a la persona que emitio la transacción masiva
    def send_email_emisor(self):
        context = {
            "name": self.context.get('name'),
            "email": self.context.get('email'),
            "observations": self.context.get('observations'),
            "status": "AUTORIZADO"
        }

        EmailAuthTransactionIndividual(to=context.get('email'), **context)
