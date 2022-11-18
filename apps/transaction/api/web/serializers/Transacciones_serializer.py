from typing import NoReturn
import datetime as dt
from typing import NoReturn

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.transaction import atomic
from rest_framework.serializers import *
from django.core.files import File
from rest_framework.serializers import ValidationError

from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.mails.messages import EmailAuthTransactionIndividual
from apps.api_dynamic_token.api.web.serializers.serializers_dynamic_token import SerializerDynamicToken
from apps.contacts.models import HistoricoContactos
from apps.transaction.exc import CouldNotChangeState, InsufficientBalance
from apps.transaction.management import ceateTransactionIndividualMasive, CrearComprobanteTransactionPDF
from apps.transaction.models import transmasivaprod, tipo_transferencia, transferencia, bancos
from apps.users.models import persona, cuenta
from polipaynewConfig.exceptions import add_list_errors
from apps.transaction.api.movil.serializers.createTransaction import *
# from apps.transaction.management import ceateTransactionIndividualMasive
from apps.users.management import (
    get_Object_orList_error,
    filter_all_data_or_return_none,
    filter_data_or_return_none)


#__POSIBLE__OBSOLETO
class serializerTransaccionesOut(serializers.Serializer):
    id = serializers.ReadOnlyField()
    banco_beneficiario = serializers.CharField()
    cta_beneficiario = serializers.CharField()
    banco = serializers.CharField()
    clave_rastreo = serializers.CharField()
    nombre_beneficiario = serializers.CharField()
    rfc_curp_beneficiario = serializers.CharField()
    tipo_pago_id = serializers.IntegerField()
    tipo_cuenta = serializers.CharField()
    monto = serializers.FloatField()
    concepto_pago = serializers.CharField()
    referencia_numerica = serializers.CharField()
    institucion_operante = serializers.CharField()
    empresa = serializers.CharField()
    banco_emisor = serializers.CharField()
    nombre_emisor = serializers.CharField()
    cuenta_emisor = serializers.CharField()
    fecha_creacion = serializers.DateTimeField()
    masivo_trans_id = serializers.IntegerField()
    status_trans_id = serializers.IntegerField()
    cuentatransferencia_id = serializers.IntegerField()


#__POSIBLE__OBSOLETO
class serializerTransMasivaProdIn(serializers.Serializer):
    date_liberation = serializers.DateTimeField()
    observations = serializers.CharField()
    data = serializers.ListField()

    def createMasive(self, IdPersona, IdStatus, Id_account):
        datos = self.validated_data.get("data")
        f = open('file.xlsx', 'rb')
        excel = File(f)
        instanceM = transmasivaprod.objects.create(date_liberation=self.validated_data.get("date_liberation"),
                                                   observations=self.validated_data.get("observations"))
        instanceM.file = excel
        instanceM.date_modified = None
        instanceM.save()
        ceateTransactionIndividualMasive(datos, instanceM, IdPersona, IdStatus, Id_account)
        return instanceM


#__POSIBLE__OBSOLETO
class serializerTransmasivaprodOut(serializers.Serializer):
    id = serializers.ReadOnlyField()
    date_created = serializers.DateTimeField()
    date_modified = serializers.DateTimeField()
    date_liberation = serializers.DateTimeField()
    observations = serializers.CharField()
    file = serializers.FileField()


class serializerListAllBanks(serializers.Serializer):
    id = serializers.ReadOnlyField()
    clabe = serializers.CharField()
    institucion = serializers.CharField()
    participante = serializers.CharField()


#__POSIBLE__OBSOLETO
class serializerListCard(serializers.Serializer):
    id = serializers.ReadOnlyField()
    tarjeta = serializers.CharField()


#__POSIBLE__OBSOLETO
class serializerPerson(serializers.Serializer):
    person = serializers.SerializerMethodField()

    def get_person(self, obj: person):
        person_instance = get_Object_orList_error(persona, id=obj.id)
        account_instance = get_Object_orList_error(cuenta, persona_cuenta=person_instance.id)
        return {
            'id': person_instance.id,
            'name': person_instance.get_full_name(),
            'Saldo-Disponible': account_instance.monto
        }

#__POSIBLE__OBSOLETO
class serializerMoviemientoEgresos(serializers.Serializer):
    id = serializers.ReadOnlyField()
    nombre_beneficiario = serializers.CharField()
    monto = serializers.CharField()
    fecha_creacion = serializers.ReadOnlyField()
    Tipo = serializers.SerializerMethodField()
    Origen = serializers.SerializerMethodField()

    def get_Tipo(self, obj: Tipo):
        t_transferencia_instance = filter_all_data_or_return_none(tipo_transferencia, id=obj.tipo_pago_id)
        for i in t_transferencia_instance:
            return i.nombre_tipo

    def get_Origen(self, obj: Origen):
        if obj.masivo_trans_id is None:
            return 'Individual'
        else:
            return 'Masivo'


#__POSIBLE__OBSOLETO (Esta repetido, el funcional se encuentra en recibida_manual)
class CreateTransactionReceivedIn(serializers.Serializer):
    empresa = serializers.CharField(read_only=True, allow_null=False, allow_blank=False)
    nombre_emisor = serializers.CharField()
    transmitter_bank_id = serializers.IntegerField()
    cuenta_emisor = serializers.CharField()
    monto = serializers.FloatField()
    concepto_pago = serializers.CharField()
    referencia_numerica = serializers.CharField()
    clave_rastreo = serializers.CharField()
    date_modify = serializers.CharField()
    hora = serializers.CharField(write_only=True)
    nombre_beneficiario = serializers.CharField(read_only=True)
    cta_beneficiario = serializers.CharField(read_only=True)
    receiving_bank_id = serializers.IntegerField(read_only=True)
    rfc_curp_beneficiario = serializers.CharField(read_only=True)

    def validate_clave_rastreo(self, value: str) -> str:
        if len(value) > 30:
            raise ValidationError({'code':400,
                                   'status': 'Error',
                                   'detail': 'Asegúrese que la longitud no sea mayor a 30 caracteres'})
        return value

    def validate_cuenta_emisor(self, value: str) -> str:
        if len(value) > 18:
            raise ValidationError({'code':400,
                                   'status': 'Error',
                                   'detail': 'Asegúrese que la longitud no sea mayor a 18 digitos'})
        return value

    def validate_referencia_numerica(self, value: str) -> str:
        if len(value) > 7:
            raise ValidationError({'code':400,
                                   'status': 'Error',
                                   'detail': 'Asegúrese que la longitud no sea mayor a 7 digitos'})
        return value

    def validate(self, attrs):
        date_modify = (attrs['date_modify'])
        hora = (attrs['hora'])

        get_cuenta_beneficiario = self.context['cuenta_beneficiaria'].get_all_cuentas()

        if not get_cuenta_beneficiario['is_active']:
            raise ValidationError({'code': 400,
                                   'status': 'Error',
                                   'detail': 'Cuenta de beneficiario inactiva'})

        attrs['empresa'] = self.context['cuenta_eje']
        attrs['nombre_beneficiario'] = self.context['nombre_beneficiario']
        attrs['cta_beneficiario'] = get_cuenta_beneficiario['cuenta']
        attrs['date_modify'] = datetime.datetime.strptime(f'{date_modify}{hora}', "%d/%m/%Y%H:%M")
        attrs['cuentatransferencia_id'] = get_cuenta_beneficiario['id']

        return attrs

    def create(self, **kwargs):
        try:
            with atomic():

                self.validated_data.pop('hora')
                instance_cuenta_beneficiaria = self.context['cuenta_beneficiaria']
                instance_transR = transferencia.objects.create_trans_rec(**self.validated_data)

                instance_cuenta_beneficiaria.monto += instance_transR.monto
                instance_cuenta_beneficiaria.save()

                return True
        except Exception as e:
            raise ValidationError({'code': 400, 'status': 'Error',
                                   'message': 'Ocurrio un error inesperado al momento de crear la transaccion',
                                   'detail': str(e)})


class SerializerCreateTransactionReceivedFisicPerson(Serializer):
    empresa = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    nombre_emisor = serializers.CharField()
    transmitter_bank_id = serializers.IntegerField()
    cuenta_emisor = serializers.CharField()
    monto = serializers.FloatField()
    concepto_pago = serializers.CharField()
    referencia_numerica = serializers.IntegerField()
    clave_rastreo = serializers.CharField()
    date_modify = serializers.CharField()
    hora = serializers.CharField(write_only=True)
    nombre_beneficiario = serializers.CharField(read_only=True)
    cta_beneficiario = serializers.CharField(read_only=True)
    receiving_bank_id = serializers.IntegerField(read_only=True)
    rfc_curp_beneficiario = serializers.CharField(read_only=True)

    def validate(self, attrs):
        date_modify = (attrs['date_modify'])
        hora = (attrs['hora'])

        get_cuenta_beneficiario = self.context['cuenta_beneficiaria'].get_all_cuentas()

        if get_cuenta_beneficiario['is_active'] == 0:
            raise ValidationError({'code': 400,
                                   'status': 'Error',
                                   'detail': 'Cuenta de beneficiario inactiva'})

        attrs['empresa'] = 'N/A'
        attrs['nombre_beneficiario'] = self.context['nombre_beneficiario']
        attrs['cta_beneficiario'] = get_cuenta_beneficiario['cuenta']
        attrs['date_modify'] = datetime.datetime.strptime(f'{date_modify}{hora}', "%d/%m/%Y%H:%M")
        attrs['cuentatransferencia_id'] = get_cuenta_beneficiario['id']

        return attrs

    def create(self, **kwargs):
        self.validated_data.pop('hora')

        instance_cuenta_beneficiaria = self.context['cuenta_beneficiaria']

        instance_transR = transferencia.objects.create_trans_rec(**self.validated_data)

        instance_cuenta_beneficiaria.monto += instance_transR.monto
        instance_cuenta_beneficiaria.save()

        return True


class serializerDetailTransactionReceived(Serializer):
    id = serializers.CharField()
    clave_rastreo = serializers.CharField()
    nombre_beneficiario = serializers.ReadOnlyField()
    cta_beneficiario = serializers.CharField()
    receiving_bank_id = serializers.SerializerMethodField()
    nombre_emisor = serializers.CharField()
    cuenta_emisor = serializers.CharField()
    transmitter_bank_id = serializers.SerializerMethodField()
    monto = serializers.CharField()
    concepto_pago = serializers.CharField()
    referencia_numerica = serializers.CharField()
    date_modify = serializers.CharField()
    tipo_operacion = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    def get_tipo_operacion(self, obj: tipo_operacion):
        t_transferencia_instance = filter_all_data_or_return_none(tipo_transferencia, id=obj.tipo_pago_id)
        for i in t_transferencia_instance:
            return i.nombre_tipo

    def get_email(self, obj: email):
        cuenta_ins = cuenta.objects.filter(cuentaclave=obj.cta_beneficiario).values('persona_cuenta__email').first()
        if cuenta_ins:
            return cuenta_ins.get('persona_cuenta__email')
        return None

    def get_receiving_bank_id(self, obj: receiving_bank_id):
        banks = bancos.objects.filter(id=obj.receiving_bank_id).values('institucion').first()
        if banks:
            return banks.get('institucion')
        return None


    def get_transmitter_bank_id(self, obj: transmitter_bank_id):
        banks = bancos.objects.filter(id=obj.transmitter_bank_id).values('institucion').first()
        if banks:
            return banks.get('institucion')
        return None


class SerializerTransactionToThirdPerson(Serializer):
    nombre_beneficiario = CharField()
    email = CharField(allow_null=True)
    rfc_curp_beneficiario = CharField(allow_null=True)
    cuenta_beneficiario = CharField()
    monto = FloatField()
    banco_beneficiario_id = IntegerField()
    referencia_numerica = CharField()
    concepto_pago = CharField()
    empresa = CharField(read_only=True)
    cuenta_emisor = CharField(read_only=True)
    nombre_emisor = CharField(read_only=True)
    cuenta_id = IntegerField(read_only=True)
    emisor_empresa_id = IntegerField(read_only=True)
    tipo_cuenta_beneficiario = IntegerField(read_only=True)

    def validate_nombre_beneficiario(self, value: str) -> str:
        return value.title()

    def validate_email(self, value: str) -> str:
        if value:
            return value.lower()
        return "ND"

    def validate_rfc_curp_beneficiario(self, value: str) -> str:
        if value:
            return value.upper()
        return "ND"

    def validate_cuenta_beneficiario(self, value: str) -> str:
        if len(value) > 18:
            raise ValueError('Error validando la cuenta clabe')

        if len(value) < 16:
            raise ValueError('Error validando el numero de tarjeta')

        if len(value) == 17:
            raise ValueError('Error validando la cuenta clabe')

        return value

    def validate_monto(self, value: float) -> float:
        if value < 1:
            raise ValidationError('Asegúrese de que el monto no sea menor a 1')
        return round(value, 2)

    def validate_banco_beneficiario_id(self, value: int) -> int:
        return value

    def validate_referencia_numerica(self, value: str) -> str:
        if len(value) > 7:
            raise ValueError('Numero de referencia no debe ser mayor a 7')

        if len(value) == 0:
            raise ValueError('Numero de referencia no debe ser menor a 0')

        if not value.isnumeric():
            raise ValueError('Se esperaba un valor numerico')

        if value.split()[0] == "0":
            raise ValueError('La referencia numerica no puede iniciar en 0')

        return value

    def _update_attrs(self, attrs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if len(attrs.get('cuenta_beneficiario')) == 18:
            attrs.update({'tipo_cuenta_beneficiario': 40})

        if len(attrs.get('cuenta_beneficiario')) == 16:
            attrs.update({'tipo_cuenta_beneficiario': 3})

        attrs.update({'empresa': context.get('empresa')})
        attrs.update({'nombre_emisor': context.get('nombre_emisor')})
        attrs.update({'cuenta_emisor': context.get('cuenta_emisor')})
        attrs.update({'cuenta_id': context.get('cuenta_id')})
        attrs.update({'emisor_empresa_id': context.get('emisor_empresa_id')})
        return attrs

    def validate(self, attrs):
        attrs = self._update_attrs(dict(attrs), self.context)
        if self.context.get('monto_emisor') < attrs.get('monto'):
            raise ValueError("Saldo insuficiente")

        return attrs

    def create(self, **kwargs) -> NoReturn:
        transferencia.objects.create_transaction_individual(**self.validated_data)


# (ChrGil 28-11-2021) Autorizar transacción a terceros individual
class SerializerAuthorizeTransaction(Serializer):
    status_trans_id = IntegerField()

    def validate(self, attrs):
        amount_transaction = self.context.get('transaction_info').get('monto')
        amount_cost_center = self.context.get('transaction_info').get('cuentatransferencia__monto')

        if self.context.get('transaction_info').get('user_autorizada_id'):
            raise CouldNotChangeState('Esta transacción ya ha sido autorizada')

        if attrs['status_trans_id'] != 3:
            raise CouldNotChangeState('Ya no es posible cambiar el estado de esta transacción')

        if amount_cost_center < amount_transaction:
            raise InsufficientBalance('Saldo insuficiente')

        return attrs

    def update(self, **kwargs):
        transferencia.objects.filter(
            id=self.context.get('transaction_info').get('id')
        ).update(
            status_trans_id=3,
            date_modify=dt.datetime.now(),
            user_autorizada=self.context.get('admin').get('id'),
            saldo_remanente=self.context.get('saldo_remanente')
        )

        self._send_email_emisor()

    # (ChrGil 2021-11-25) Enviar Correo a la persona que emitio la transacción masiva
    def _send_email_emisor(self):
        EmailAuthTransactionIndividual(
            to=self.context.get('transaction_info').get('emisor_empresa__email'),
            name=self.context.get('transaction_info').get('emisor_empresa__name'),
            observations=self.context.get('transaction_info').get('concepto_pago'),
            status="AUTORIZADA"
        )


class SerializerCancelTransaction(Serializer):

    def validate(self, attrs):
        status_trans_id = self.context['status_trans']

        if status_trans_id == 5:
            error = {'code': 400, 'status': 'error','message': 'Esta transaccion ya ha sido cancelada anteriormente'}
            raise ValidationError(error)
        if status_trans_id == 1:
            error = {'code': 400, 'status': 'error', 'message': 'Esta Transaccion ya ha sido liquidada'}
            raise ValidationError(error)
        return attrs

    def update(self, instance, validated_data):

        instance_cuenta_emisor = self.context['cuenta_emisor']
        persona_emisor_email = self.context['person_emisor_email']
        user_cancela = self.context['user_cancelar']

        instance.status_trans_id = 5
        instance.saldo_remanente = instance_cuenta_emisor.monto
        instance.save()
        send_email_cancel_transaction_emisor(instance, persona_emisor_email, user_cancela)
        send_email_cancel_transaction_user_autorize(instance, persona_emisor_email, user_cancela)


class SerializerCreateTransactionPolipayToPolipay(Serializer):
    empresa = serializers.CharField(read_only=True, allow_null=False, allow_blank=False)
    cta_beneficiario = serializers.CharField(allow_blank=False, allow_null=False)
    monto = serializers.FloatField(allow_null=False)
    nombre_beneficiario = serializers.CharField(allow_null=False, allow_blank=False)
    referencia_numerica = serializers.CharField(allow_null=False, allow_blank=False)
    concepto_pago = serializers.CharField(allow_null=False, allow_blank=False)
    rfc_curp_beneficiario = serializers.CharField(allow_blank=True, allow_null=True)
    email = serializers.CharField(allow_blank=True, allow_null=True)
    nombre_emisor = serializers.CharField(read_only=True)
    cuenta_emisor = serializers.CharField(read_only=True)
    is_frecuent = serializers.BooleanField()
    alias = serializers.CharField(allow_null=True, allow_blank=True)

    def validate(self, attrs):
        get_cuenta_emisor = self.context['cuenta_emisor'].get_all_cuentas()
        cost_center = self.context['cost_center']
        cuenta_beneficiario = attrs['cta_beneficiario']
        contacto = contactos.objects.filter(person_id=self.context['empresa_id'], cuenta=attrs['cta_beneficiario'], tipo_contacto_id=1)

        try:
            get_cuenta_beneficiario: Dict = cuenta.objects.get(Q(cuentaclave=cuenta_beneficiario)|Q(cuenta=cuenta_beneficiario)).get_all_cuentas()
        except ObjectDoesNotExist as e:
            error = {'code': 404, 'status': 'Error', 'detail': 'La cuenta beneficiario no existe'}
            raise ValidationError(error)
        else:
            is_cuenta_eje = grupoPersona.objects.filter(
                empresa_id=get_cuenta_beneficiario.get('persona_cuenta_id'),
                relacion_grupo_id=1
            ).exists()

            cost_center_beneficiario = grupoPersona.objects.filter(
                person_id=get_cuenta_beneficiario.get('persona_cuenta_id'),
                relacion_grupo_id__in=[5,9]).values('empresa_id').first()

            cost_center_emisor = grupoPersona.objects.filter(person_id=get_cuenta_emisor['persona_cuenta_id'],
                                                             relacion_grupo_id__in=[5,9]).values('empresa_id').first()

            if cost_center_emisor['empresa_id'] == cost_center_beneficiario['empresa_id']:
                error = {'code': 400, 'status': 'Error', 'detail': 'Estimado cliente, la operacion que intenta realizar no es posible'}
                self.context.get('log').json_response(error)
                raise ValidationError(error)

            if attrs['monto'] < 1:
                error = {'code':400, 'status':'Error', 'detail': 'No es posible transferir montos en 0 o negativos'}
                raise ValidationError(error)

            if is_cuenta_eje:
                error = {'code': 400, 'status': 'Error', 'detail': 'Estimado cliente, la operación que intenta realizar no es posible.'}
                self.context.get('log').json_response(error)
                raise ValidationError(error)

            if not get_cuenta_beneficiario['is_active']:
                error = {'code': 400, 'status': 'Error', 'detail': 'Cuenta beneficiario inactiva'}
                self.context.get('log').json_response(error)
                raise ValidationError(error)

            if not cost_center['is_active']:
                error = {'code': 400, 'status': 'error', 'detail': 'centro de costo inactivo'}
                self.context.get('log').json_response(error)
                raise ValidationError(error)

            if not get_cuenta_emisor['is_active']:
                error = {'code': 400, 'status': 'Error', 'detail': 'Cuenta emisor inactiva'}
                self.context.get('log').json_response(error)
                raise ValidationError(error)

            if get_cuenta_emisor['monto'] < attrs['monto']:
                error = {'code': 400, 'status': 'Error', 'detail': 'Saldo insuficiente'}
                self.context.get('log').json_response(error)
                raise ValidationError(error)

            if get_cuenta_emisor['cuenta'] == attrs['cta_beneficiario']:
                error = {'code': 400, 'status': 'Error', 'detail': 'No es posible transferir a su misma cuenta'}
                self.context.get('log').json_response(error)
                raise ValidationError(error)

            if get_cuenta_emisor['cuentaclabe'] == attrs['cta_beneficiario']:
                error = {'code': 400, 'status': 'Error', 'detail': 'No es posible transferir a su misma cuenta'}
                self.context.get('log').json_response(error)
                raise ValidationError(error)

            if attrs['is_frecuent'] is True and attrs['alias'] is None:
                error = {'code': 400, 'status': 'Error', 'Detail': 'Ingrese un alias'}
                self.context.get('log').json_response(error)
                raise ValidationError(error)

            if attrs ['is_frecuent'] is True and contacto:
                error = {'code': 400, 'status': 'Error', 'detail': 'Ya existe un contacto frecuente regitrado con esta cuenta'}
                self.context.get('log').json_response(error)
                raise ValidationError(error)

            attrs['empresa'] = self.context['empresa']
            attrs['nombre_emisor'] = self.context['nombre_emisor']
            attrs['cuenta_emisor'] = get_cuenta_emisor['cuenta']

            return attrs

    def create(self, **kwargs):
        try:
            with atomic():
                if self.validated_data['is_frecuent'] is True:
                    self.save_frecuent_contact()

                self.validated_data.pop('is_frecuent')
                self.validated_data.pop('alias')
                email_emisor = self.context['email_emisor']

                instance_transferecia = transferencia.objects.create_transaction_polipay_to_polipay(
                    **self.validated_data)
                instance_cuenta_emisor = self.context['cuenta_emisor']

                get_cuenta_beneficiario = cuenta.objects.get(Q(cuentaclave=instance_transferecia.cta_beneficiario)|Q(cuenta=instance_transferecia.cta_beneficiario))

                instance_transferecia.saldo_remanente = instance_cuenta_emisor.monto - instance_transferecia.monto
                instance_transferecia.save()

                instance_transferecia.saldo_remanente_beneficiario = get_cuenta_beneficiario.monto + instance_transferecia.monto
                instance_transferecia.save()

                instance_cuenta_emisor.monto -= instance_transferecia.monto
                instance_cuenta_emisor.save()

                get_cuenta_beneficiario.monto += instance_transferecia.monto
                get_cuenta_beneficiario.save()
                send_email_emisor_polipay_to_polipay(instance_transferecia, email_emisor)
                return True
        except IntegrityError as e:
            error = {'code': 400,
                     'status': 'error',
                     'message': 'Ocurrio un error inesperado al momento de crear la transaccion',
                     'detail': str(e)}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

    def save_frecuent_contact(self, **kwargs):
        nombre = self.validated_data['nombre_beneficiario']
        cuenta = self.validated_data['cta_beneficiario']
        instance = contactos.objects.create(
            nombre=nombre,
            cuenta=cuenta,
            banco=86,
            is_favorite=True,
            person_id=self.context['empresa_id'],
            alias=self.validated_data['alias'],
            tipo_contacto_id=1
        )

        instance_historico_contactos = HistoricoContactos.objects.create(
            fechaRegistro=datetime.datetime.now(),
            contactoRel_id=instance.id,
            operacion_id=1,
            usuario_id=self.context['empresa_id']
        )
        return True


class serializerDetailTransactionPolipayToPolipaySend(Serializer):
    id = serializers.CharField()
    clave_rastreo = serializers.CharField()
    nombre_beneficiario = serializers.ReadOnlyField()
    cta_beneficiario = serializers.CharField()
    receiving_bank_id = serializers.SerializerMethodField()
    nombre_emisor = serializers.CharField()
    cuenta_emisor = serializers.CharField()
    transmitter_bank_id = serializers.SerializerMethodField()
    monto = serializers.FloatField()
    concepto_pago = serializers.CharField()
    referencia_numerica = serializers.CharField()
    date_modify = serializers.CharField()
    tipo_operacion = serializers.SerializerMethodField()

    def get_tipo_operacion(self, obj: tipo_operacion):
        t_transferencia_instance = filter_all_data_or_return_none(tipo_transferencia, id=obj.tipo_pago_id)
        for i in t_transferencia_instance:
            return i.nombre_tipo

    def get_receiving_bank_id(self, obj: receiving_bank_id):
        bank_instance = get_Object_orList_error(bancos, id=obj.receiving_bank_id)
        return bank_instance.institucion

    def get_transmitter_bank_id(self, obj: transmitter_bank_id):
        bank_instance = get_Object_orList_error(bancos, id=obj.transmitter_bank_id)
        return bank_instance.institucion


class SerializerCreateTransactionBetweenOwnAccounts(Serializer):
    empresa = serializers.CharField()
    nombre_beneficiario = serializers.CharField()
    nombre_emisor = serializers.CharField(read_only=True)
    concepto_pago = serializers.CharField(allow_null=False, allow_blank=False)
    monto = serializers.FloatField(allow_null=False)
    cuenta_emisor = serializers.IntegerField(allow_null=True)
    cta_beneficiario = serializers.IntegerField(allow_null=False)
    cuentatransferencia_id = serializers.IntegerField(read_only=True)

    def validate(self, attrs):
        get_cuenta_emisor = cuenta.objects.get(cuenta=attrs['cuenta_emisor'])
        get_cuenta_beneficiario = cuenta.objects.get(cuenta=attrs['cta_beneficiario'])

        if attrs['monto'] < 1:
            error = {'code': 400, 'status': 'Error', 'detail': 'No es posible transferir montos en 0 o negativos'}
            self.context.get('log').json_response(error)    
            raise ValidationError(error)

        if get_cuenta_emisor.monto < attrs['monto']:
            error = {'code': 400, 'status': 'Error', 'detail': 'Saldo insuficiente'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if get_cuenta_emisor.cuenta == attrs['cta_beneficiario']:
            error = {'code': 400, 'status': 'Error', 'detail': 'No es posible transferir a su misma cuenta'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if get_cuenta_emisor.cuentaclave == attrs['cta_beneficiario']:
            error = {'code': 400, 'status': 'Error', 'detail': 'No es posible transferir a su misma cuenta'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if not get_cuenta_emisor.is_active:
            error = {'code': 400, 'status': 'Error', 'detail': 'Cuenta emisor inactiva'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if not get_cuenta_beneficiario.is_active:
            error = {'code': 400, 'status': 'Error', 'detail': 'Cuenta beneficiario inactiva'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        attrs['nombre_emisor'] = self.context['nombre_emisor']
        attrs['cuentatransferencia_id'] = get_cuenta_emisor.id
        attrs['emisor_empresa_id'] = self.context['request_user']
        return attrs

    def create(self, **kwargs):
        try:
            with atomic():

                instance_transferencia = transferencia.objects.create_trans_own_accounts(**self.validated_data)
                get_cuenta_beneficiario = cuenta.objects.get(cuenta=instance_transferencia.cta_beneficiario)
                get_cuenta_emisor = cuenta.objects.get(cuenta=instance_transferencia.cuenta_emisor)

                instance_transferencia.saldo_remanente = get_cuenta_emisor.monto - instance_transferencia.monto
                instance_transferencia.save()

                instance_transferencia.saldo_remanente_beneficiario = get_cuenta_beneficiario.monto + instance_transferencia.monto
                instance_transferencia.save()

                get_cuenta_emisor.monto -= instance_transferencia.monto
                get_cuenta_emisor.save()

                get_cuenta_beneficiario.monto += instance_transferencia.monto
                get_cuenta_beneficiario.save()
                return True
        except Exception as e:
            error = {'code': 400,
                     'status': 'Error',
                     'message': 'Ocurrio un error inesperado al momento de crear la transaccion',
                     'detail': str(e)}
            self.context.get('log').json_response(error)
            raise ValidationError(error)


class SerializerDashboardAdmin(serializers.Serializer):
    centro_costo = serializers.IntegerField()

    def validate_centro_costo(self, value):
        # Confirmo que exista el id de persoan moral como Cuenta eje o centro de costos
        queryExisteCentroCosto = persona.objects.filter(id=value, tipo_persona_id=1).exists()
        if not queryExisteCentroCosto:
            r = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "field": "centro_costo",
                        "data": value,
                        "message": "El cento de costos no existe en el sistema."
                    }
                ]
            }
            raise serializers.ValidationError(r)

        return value

    def validate(self, data):
        tmp_message = "centro de costos"
        # Confirmo que el centro de costos sea un cento de costo (Polipay Empresa y Liberate requiere cento de costos)
        queryEsCentroCosto = grupoPersona.objects.filter(person_id=data["centro_costo"], relacion_grupo_id=5).exists()
        if not queryEsCentroCosto:

            queryEsCuentaEje = grupoPersona.objects.filter(empresa_id=data["centro_costo"],
                                                           relacion_grupo_id=1).exists()
            if not queryEsCuentaEje:
                # Confirmo que sea cuenta eje al no ser centro de costo (Producto Dispera se requiere cuenta eje)
                r = {
                    "code": [400],
                    "status": "ERROR",
                    "detail": [
                        {
                            "field": "centro_costo",
                            "data": data["centro_costo"],
                            "message": "No está registrado como una cuenta eje ni centro de costos."
                        }
                    ]
                }
                raise serializers.ValidationError(r)

        return data

    def getTransactionSummary(self, data):
        objJson = {"empresas": []}
        arrayTmp_movimientos = []

        banderaIdentidadCentroCosto = True  # True: es un centro de costos, False: es una cuenta eje
        # Determino si es centro de costos o cuenta eje
        queryEsCentroCosto = grupoPersona.objects.filter(person_id=data["centro_costo"], relacion_grupo_id=5).exists()
        if not queryEsCentroCosto:
            banderaIdentidadCentroCosto = False

        # Recupero el id e la cuenta eje a la que pertenece el administrativo, siempre y cuando sea un centro de costos
        if banderaIdentidadCentroCosto:
            queryIdCuentaEje = grupoPersona.objects.filter(person_id=data["centro_costo"], relacion_grupo_id=5).values(
                "id", "empresa_id")
            idCuentaEje = queryIdCuentaEje[0]["empresa_id"]  # Centro de costo
        else:
            idCuentaEje = data["centro_costo"]  # Cuenta eje

        queryCentroDeCostos = persona.objects.filter(id=data["centro_costo"]).values("id", "name", "last_name")
        print(queryCentroDeCostos)

        for centroDeCosto in queryCentroDeCostos:
            centroDeCosto["empresa_id"] = centroDeCosto.pop("id")
            centroDeCosto["empresa_name"] = centroDeCosto.pop("name")
            centroDeCosto["empresa_lastname"] = centroDeCosto.pop("last_name")

        # ::: Recorro los centros de costos para recuperar sus movimientos :::
        for centroDeCosto in queryCentroDeCostos:
            queryCuenta = cuenta.objects.filter(persona_cuenta_id=centroDeCosto["empresa_id"]).values("id", "cuenta", "cuentaclave", "monto")
            centroDeCosto["empresa_cuenta"] = queryCuenta[0]["cuenta"]
            centroDeCosto["empresa_clabe"] = queryCuenta[0]["cuentaclave"]

            queryMovimientos = transferencia.objects.filter(
                Q(cuenta_emisor=centroDeCosto["empresa_cuenta"]) | Q(cuenta_emisor=centroDeCosto["empresa_clabe"]) |
                Q(cta_beneficiario=centroDeCosto["empresa_cuenta"]) | Q(
                    cta_beneficiario=centroDeCosto["empresa_clabe"])).values(
                "id", "monto", "cuenta_emisor", "cta_beneficiario", "tipo_pago_id", "status_trans_id",
                "masivo_trans_id",
                "masivo_trans__statusRel_id")

            for movimiento in queryMovimientos:
                movimiento["masiva_status_trans_id"] = movimiento.pop("masivo_trans__statusRel_id")
                arrayTmp_movimientos.append(movimiento)

        if banderaIdentidadCentroCosto:
            # ::: Recorro todos los movimientos de todos los centros de costos:::
            arrayTmp_categorias = {
                "cuentas_propias": ""
            }

            for centroDeCosto in queryCentroDeCostos:
                #   Caso 4: Cuentas propias
                tmp_monto_emisor = 0.0
                tmp_numero_emisor = 0.0
                tmp_monto_receptor = 0.0
                tmp_numero_receptor = 0.0
                arrayTmp_caso_4 = []

                queryCentroDeCostosHnos = grupoPersona.objects.filter(empresa_id=idCuentaEje,
                                                                      relacion_grupo_id=5).exclude(
                    person_id=data["centro_costo"]).values(
                    "id", "person_id", "person_id__email", "person_id__name", "person_id__last_name")
                for centroDeCosto2 in queryCentroDeCostosHnos:
                    centroDeCosto2["relacion_id"] = centroDeCosto2.pop("id")
                    centroDeCosto2["empresa_id"] = centroDeCosto2.pop("person_id")
                    centroDeCosto2["empresa_email"] = centroDeCosto2.pop("person_id__email")
                    centroDeCosto2["empresa_name"] = centroDeCosto2.pop("person_id__name")
                    centroDeCosto2["empresa_lastname"] = centroDeCosto2.pop("person_id__last_name")

                # Recupero la cuenta y CLABE de cada centro de costos.
                for centroDeCosto2 in queryCentroDeCostosHnos:
                    queryCuenta = cuenta.objects.filter(persona_cuenta_id=centroDeCosto2["empresa_id"]).values(
                        "id", "cuenta", "cuentaclave", "monto")
                    centroDeCosto2["empresa_cuenta_id"] = queryCuenta[0]["id"]
                    centroDeCosto2["empresa_cuenta"] = queryCuenta[0]["cuenta"]
                    centroDeCosto2["empresa_clabe"] = queryCuenta[0]["cuentaclave"]

                for centroDeCostoHno in queryCentroDeCostosHnos:

                    # Caso 1: Centro de costos es el emisor
                    for m in arrayTmp_movimientos:

                        if str(m["cuenta_emisor"]) == str(centroDeCosto["empresa_cuenta"]) and str(
                                m["cta_beneficiario"]) == str(centroDeCostoHno["empresa_cuenta"]) and m[
                                "tipo_pago_id"] == 7 and m["status_trans_id"] == 1:
                            tmp_monto_emisor += round(float(m["monto"]), 2)
                            tmp_numero_emisor += 1

                        elif str(m["cuenta_emisor"]) == str(centroDeCosto["empresa_clabe"]) and str(
                                m["cta_beneficiario"]) == str(centroDeCostoHno["empresa_clabe"]) and m[
                                "tipo_pago_id"] == 7 and m["status_trans_id"] == 1:
                            tmp_monto_emisor += round(float(m["monto"]), 2)
                            tmp_numero_emisor += 1

                        if str(m["cta_beneficiario"]) == str(centroDeCosto["empresa_cuenta"]) and str(
                                m["cuenta_emisor"]) == str(centroDeCostoHno["empresa_cuenta"]) and m[
                                "tipo_pago_id"] == 7 and m["status_trans_id"] == 1:
                            tmp_monto_receptor += round(float(m["monto"]), 2)
                            tmp_numero_receptor += 1

                        elif str(m["cta_beneficiario"]) == str(centroDeCosto["empresa_clabe"]) and str(
                                m["cuenta_emisor"]) == str(centroDeCostoHno["empresa_clabe"]) and m[
                                "tipo_pago_id"] == 7 and m["status_trans_id"] == 1:
                            tmp_monto_receptor += round(float(m["monto"]), 2)
                            tmp_numero_receptor += 1

                    if round(float(tmp_monto_emisor), 2) > 0.0:
                        arrayTmp_caso_4.append(
                            {
                                "origen": centroDeCosto["empresa_name"],
                                "destino": centroDeCostoHno["empresa_name"],
                                "monto": tmp_monto_emisor,
                                "movimientos": tmp_numero_emisor
                            }
                        )

                    if round(float(tmp_monto_receptor), 2) > 0.0:
                        arrayTmp_caso_4.append(
                            {
                                "origen": centroDeCostoHno["empresa_name"],
                                "destino": centroDeCosto["empresa_name"],
                                "monto": tmp_monto_receptor,
                                "movimientos": tmp_numero_receptor
                            }
                        )

                    tmp_monto_emisor = 0.0
                    tmp_numero_emisor = 0.0
                    tmp_monto_receptor = 0.0
                    tmp_numero_receptor = 0.0
                arrayTmp_categorias["cuentas_propias"] = arrayTmp_caso_4

                # Se agregan movimientos de cada categoria en cada centro de costos
                centroDeCosto["detalle"] = arrayTmp_categorias
                arrayTmp_categorias = {
                    "cuentas_propias": ""
                }
        else:
            queryCuentaEje = persona.objects.filter(id=data["centro_costo"]).values("id", "email", "name", "last_name")
            # ::: Recorro todos los movimientos de la cuenta eje :::
            arrayTmp_categorias = {
                "cuentas_propias": []
            }

            # Se agregan movimientos de cada categoria en cada centro de costos
            centroDeCosto["detalle"] = arrayTmp_categorias
        objJson = queryCentroDeCostos
        for data in objJson:
            data.pop('empresa_id')
            data.pop('empresa_name')
            data.pop('empresa_lastname')
            data.pop('empresa_cuenta')
            data.pop('empresa_clabe')
            return data


class SerializerDocInd(Serializer):
    documento = FileField()

    def validate(self, attrs):
        return attrs


class SerializerDocIndIn(Serializer):
    id = IntegerField()

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        instance_disper = transferencia.objects.get(id=validated_data.get("id"))
        beneficiario = instance_disper.nombre_beneficiario
        userId = self.context["admin_id"]
        documentoId = CrearComprobanteTransactionPDF(instance_disper, beneficiario, userId)
        instance = documentos.objects.get(id=documentoId)
        return SerializerDocInd(instance)